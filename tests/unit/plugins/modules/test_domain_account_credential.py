# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

import pytest

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

try:
    from ansible.module_utils.testing import patch_module_args  # ansible-core >= 2.19
except ImportError:
    patch_module_args = None

from ansible_collections.wallix.bastion.plugins.module_utils import client as client_utils
from ansible_collections.wallix.bastion.plugins.modules import domain_account_credential, domain_account_credential_info
from ansible_collections.wallix.bastion.tests.unit.plugins.module_utils.fake_bastion import FakeBastion

CONN = dict(bastion_host="bastion.test", bastion_user="admin", bastion_token="token")


class ModuleExit(Exception):
    def __init__(self, result, failed=False):
        super(ModuleExit, self).__init__(result)
        self.result = result
        self.failed = failed


@pytest.fixture
def fake(monkeypatch):
    fake = FakeBastion()
    original_init = client_utils.BastionClient.__init__

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        fake.bind(self)

    monkeypatch.setattr(client_utils.BastionClient, "__init__", init)

    def exit_json(self, **kwargs):
        raise ModuleExit(kwargs)

    def fail_json(self, **kwargs):
        raise ModuleExit(kwargs, failed=True)

    monkeypatch.setattr(basic.AnsibleModule, "exit_json", exit_json)
    monkeypatch.setattr(basic.AnsibleModule, "fail_json", fail_json)
    return fake


def run(monkeypatch, module, check_mode=False, **params):
    args = dict(CONN, **params)
    if check_mode:
        args["_ansible_check_mode"] = True
    if patch_module_args is None:
        monkeypatch.setattr(basic, "_ANSIBLE_ARGS", to_bytes(json.dumps({"ANSIBLE_MODULE_ARGS": args})))
        with pytest.raises(ModuleExit) as exc:
            module.main()
    else:
        with patch_module_args(args), pytest.raises(ModuleExit) as exc:
            module.main()
    return exc.value


from ansible_collections.wallix.bastion.plugins.module_utils.client import Response

PW = "Secr3t!"


@pytest.fixture
def ids(fake):
    domain_id = fake.add("domains", {"domain_name": "corp"})["id"]
    account_id = fake.add("domains/%s/accounts" % domain_id, {"account_name": "admin"})["id"]
    return domain_id, account_id


def creds(ids):
    return "domains/%s/accounts/%s/credentials" % ids


@pytest.fixture
def propagated(fake):
    """Record PUT accountchangepassword/<account>/password, which FakeBastion does not implement."""
    seen = []
    handle = fake.handle

    def spy(client, method, url, data, headers, auth):
        if "/accountchangepassword/" in url:
            seen.append((url.split("/api/v3.12/")[1], json.loads(data)))
            return Response(204, "", {})
        return handle(client, method, url, data, headers, auth)

    fake.handle = spy
    return seen


def test_create_password(monkeypatch, fake, ids):
    res = run(monkeypatch, domain_account_credential, domain_name="corp", account_name="admin", type="password",
              password=PW)
    assert not res.failed and res.result["changed"]
    assert fake.writes()[0][2] == {"type": "password", "password": PW}
    assert "password" not in res.result["domain_account_credential"]
    assert res.result["domain_account_credential"]["type"] == "password"


def test_create_ssh_key(monkeypatch, fake, ids):
    res = run(monkeypatch, domain_account_credential, domain_name="corp", account_name="admin", type="ssh_key",
              private_key="generate:ED25519", passphrase="pp")
    assert res.result["changed"]
    assert fake.writes()[0][2] == {"type": "ssh_key", "private_key": "generate:ED25519", "passphrase": "pp"}
    assert "private_key" not in res.result["domain_account_credential"]


def test_create_requires_secret(monkeypatch, fake, ids):
    res = run(monkeypatch, domain_account_credential, domain_name="corp", account_name="admin", type="password")
    assert res.failed and "password required" in res.result["msg"]
    res = run(monkeypatch, domain_account_credential, domain_name="corp", account_name="admin", type="ssh_key")
    assert res.failed and "private_key required" in res.result["msg"]
    assert fake.writes() == []


def test_options_must_match_type(monkeypatch, fake, ids):
    res = run(monkeypatch, domain_account_credential, domain_name="corp", account_name="admin", type="password",
              password=PW, private_key="k")
    assert res.failed and "private_key cannot be used with type=password" in res.result["msg"]
    res = run(monkeypatch, domain_account_credential, domain_name="corp", account_name="admin", type="ssh_key",
              private_key="k", password=PW)
    assert res.failed and "password cannot be used with type=ssh_key" in res.result["msg"]


def test_create_check_mode_writes_nothing(monkeypatch, fake, ids):
    res = run(monkeypatch, domain_account_credential, check_mode=True, domain_name="corp", account_name="admin",
              type="password", password=PW)
    assert res.result["changed"] and fake.writes() == []
    assert res.result["diff"]["after"] == {"type": "password"}


def test_existing_is_found_by_type(monkeypatch, fake, ids):
    fake.add(creds(ids), {"type": "ssh_key", "private_key": "********", "public_key": "ssh-ed25519 AAA"})
    fake.add(creds(ids), {"type": "password", "password": "********"})
    res = run(monkeypatch, domain_account_credential, domain_name="corp", account_name="admin", type="password",
              password=PW)
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert res.result["domain_account_credential"]["type"] == "password"
    assert fake.writes() == []


def test_update_password_always(monkeypatch, fake, ids):
    cred = fake.add(creds(ids), {"type": "password", "password": "********"})
    res = run(monkeypatch, domain_account_credential, domain_name="corp", account_name="admin", type="password",
              password=PW, update_password="always")
    assert res.result["changed"] and res.result["changed_fields"] == ["password"]
    method, path, body = fake.writes()[0]
    assert method == "PUT" and path.endswith(cred["id"]) and body == {"type": "password", "password": PW}


def test_update_password_always_check_mode(monkeypatch, fake, ids):
    fake.add(creds(ids), {"type": "password", "password": "********"})
    res = run(monkeypatch, domain_account_credential, check_mode=True, domain_name="corp", account_name="admin",
              type="password", password=PW, update_password="always")
    assert res.result["changed"] and fake.writes() == []


def test_ssh_key_replaced_in_place_with_always(monkeypatch, fake, ids):
    cred = fake.add(creds(ids), {"type": "ssh_key", "private_key": "********"})
    res = run(monkeypatch, domain_account_credential, domain_name="corp", account_name="admin", type="ssh_key",
              private_key="generate:RSA_4096")
    assert not res.failed and not res.result["changed"] and fake.writes() == []
    res = run(monkeypatch, domain_account_credential, domain_name="corp", account_name="admin", type="ssh_key",
              private_key="generate:RSA_4096", update_password="always")
    assert res.result["changed"]
    method, path, body = fake.writes()[0]
    assert method == "PUT" and path.endswith(cred["id"])
    assert body == {"type": "ssh_key", "private_key": "generate:RSA_4096"}


def test_passphrase_alone_fails(monkeypatch, fake, ids):
    fake.add(creds(ids), {"type": "ssh_key", "private_key": "********"})
    res = run(monkeypatch, domain_account_credential, domain_name="corp", account_name="admin", type="ssh_key",
              passphrase="p", update_password="always")
    assert res.failed and "required by 'passphrase': private_key" in res.result["msg"]
    assert fake.writes() == []


def test_propagate_on_create_and_update(monkeypatch, fake, ids, propagated):
    run(monkeypatch, domain_account_credential, domain_name="corp", account_name="admin", type="password",
        password=PW, propagate_credential_change=True)
    assert propagated == [("accountchangepassword/%s/password" % ids[1], {"password": PW})]
    assert len(fake.objects(creds(ids))) == 1
    del propagated[:]
    res = run(monkeypatch, domain_account_credential, domain_name="corp", account_name="admin", type="password",
              password="N3w!", propagate_credential_change=True, update_password="always")
    assert res.result["changed"]
    assert propagated == [("accountchangepassword/%s/password" % ids[1], {"password": "N3w!"})]
    assert [w for w in fake.writes() if w[0] == "PUT"] == []


def test_missing_parents(monkeypatch, fake, ids):
    res = run(monkeypatch, domain_account_credential, domain_name="corp", account_name="nope", type="password",
              password=PW)
    assert res.failed and res.result["msg"] == "account nope does not exist"
    res = run(monkeypatch, domain_account_credential, domain_name="nope", account_name="admin", type="password",
              password=PW)
    assert res.failed and res.result["msg"] == "domain nope does not exist"
    for domain_name, account_name in (("corp", "nope"), ("nope", "admin")):
        res = run(monkeypatch, domain_account_credential, domain_name=domain_name, account_name=account_name,
                  type="password", state="absent")
        assert not res.failed and not res.result["changed"]
    assert fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake, ids):
    fake.add(creds(ids), {"type": "ssh_key", "private_key": "********"})
    fake.add(creds(ids), {"type": "password", "password": "********"})
    args = dict(domain_name="corp", account_name="admin", type="password", state="absent")
    assert run(monkeypatch, domain_account_credential, **args).result["changed"]
    assert [c["type"] for c in fake.objects(creds(ids))] == ["ssh_key"]
    assert not run(monkeypatch, domain_account_credential, **args).result["changed"]


def test_delete_check_mode(monkeypatch, fake, ids):
    fake.add(creds(ids), {"type": "password", "password": "********"})
    res = run(monkeypatch, domain_account_credential, check_mode=True, domain_name="corp", account_name="admin",
              type="password", state="absent")
    assert res.result["changed"] and len(fake.objects(creds(ids))) == 1


def test_info(monkeypatch, fake, ids):
    fake.add(creds(ids), {"type": "ssh_key", "private_key": "********", "public_key": "ssh-ed25519 AAA"})
    fake.add(creds(ids), {"type": "password", "password": "********"})
    one = run(monkeypatch, domain_account_credential_info, domain_name="corp", account_name="admin",
              type="ssh_key").result
    assert [c["public_key"] for c in one["domain_account_credentials"]] == ["ssh-ed25519 AAA"]
    assert not one["changed"]
    res = run(monkeypatch, domain_account_credential_info, domain_name="corp", account_name="admin")
    assert len(res.result["domain_account_credentials"]) == 2
    res = run(monkeypatch, domain_account_credential_info, domain_name="corp", account_name="nope")
    assert res.failed and res.result["msg"] == "account nope does not exist"
