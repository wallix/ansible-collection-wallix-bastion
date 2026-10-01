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
from ansible_collections.wallix.bastion.plugins.modules import device_localdomain_account_credential, device_localdomain_account_credential_info
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


CRED = dict(device_name="srv", domain_name="local", account_name="root")
API_PW = {"type": "password", "password": "********"}
API_KEY = {"type": "ssh_key", "private_key": "********", "public_key": "ssh-ed25519 AAA", "key_id": "k1"}


@pytest.fixture
def path(fake):
    device_id = fake.add("devices", {"device_name": "srv", "host": "10.0.0.1"})["id"]
    domain_id = fake.add("devices/%s/localdomains" % device_id, {"domain_name": "local"})["id"]
    account_id = fake.add("devices/%s/localdomains/%s/accounts" % (device_id, domain_id),
                          {"account_name": "root", "account_login": "root"})["id"]
    return "devices/%s/localdomains/%s/accounts/%s/credentials" % (device_id, domain_id, account_id)


def test_create_password(monkeypatch, fake, path):
    res = run(monkeypatch, device_localdomain_account_credential, type="password", password="s3cret", **CRED)
    assert not res.failed and res.result["changed"]
    method, url, body = fake.writes()[0]
    assert (method, url, body) == ("POST", "/api/v3.12/" + path, {"type": "password", "password": "s3cret"})
    assert "password" not in res.result["credential"] and res.result["credential"]["type"] == "password"
    assert "password" not in res.result["diff"]["after"]


def test_create_ssh_key(monkeypatch, fake, path):
    res = run(monkeypatch, device_localdomain_account_credential, type="ssh_key", private_key="generate:ED25519",
              passphrase="p", **CRED)
    assert res.result["changed"]
    assert fake.writes()[0][2] == {"type": "ssh_key", "private_key": "generate:ED25519", "passphrase": "p"}
    assert "private_key" not in res.result["credential"] and "passphrase" not in res.result["credential"]


def test_create_requires_secret(monkeypatch, fake, path):
    res = run(monkeypatch, device_localdomain_account_credential, type="password", **CRED)
    assert res.failed and "password required" in res.result["msg"]
    res = run(monkeypatch, device_localdomain_account_credential, type="ssh_key", **CRED)
    assert res.failed and "private_key required" in res.result["msg"]
    assert fake.writes() == []


def test_secret_of_wrong_type_fails(monkeypatch, fake, path):
    res = run(monkeypatch, device_localdomain_account_credential, type="password", password="x", private_key="k",
              **CRED)
    assert res.failed and "private_key cannot be set for a credential of type password" in res.result["msg"]
    res = run(monkeypatch, device_localdomain_account_credential, type="ssh_key", password="x", **CRED)
    assert res.failed and "password cannot be set" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake, path):
    res = run(monkeypatch, device_localdomain_account_credential, check_mode=True, type="password", password="x",
              **CRED)
    assert res.result["changed"] and fake.writes() == []
    assert "password" not in res.result["credential"]


def test_lookup_by_type(monkeypatch, fake, path):
    fake.add(path, API_KEY)
    res = run(monkeypatch, device_localdomain_account_credential, type="password", password="x", **CRED)
    assert res.result["changed"] and fake.writes()[0][0] == "POST"
    assert sorted(c["type"] for c in fake.objects(path)) == ["password", "ssh_key"]


def test_existing_secret_not_resent(monkeypatch, fake, path):
    fake.add(path, API_PW)
    res = run(monkeypatch, device_localdomain_account_credential, type="password", password="other", **CRED)
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []


def test_update_password_always(monkeypatch, fake, path):
    obj = fake.add(path, API_PW)
    res = run(monkeypatch, device_localdomain_account_credential, type="password", password="new",
              update_password="always", **CRED)
    assert res.result["changed"] and res.result["changed_fields"] == ["password"]
    method, url, body = fake.writes()[0]
    assert method == "PUT" and url.endswith("/credentials/%s" % obj["id"])
    assert body == {"type": "password", "password": "new"}


def test_update_password_always_check_mode(monkeypatch, fake, path):
    fake.add(path, API_PW)
    res = run(monkeypatch, device_localdomain_account_credential, check_mode=True, type="password", password="new",
              update_password="always", **CRED)
    assert res.result["changed"] and fake.writes() == []
    assert "password" not in res.result["credential"]


def test_missing_parents(monkeypatch, fake, path):
    for missing, label in ((dict(account_name="nope"), "account"), (dict(domain_name="nope"), "localdomain"),
                           (dict(device_name="nope"), "device")):
        params = dict(CRED, **missing)
        res = run(monkeypatch, device_localdomain_account_credential, type="password", password="x", **params)
        assert res.failed and res.result["msg"] == "%s nope does not exist" % label
        res = run(monkeypatch, device_localdomain_account_credential, type="password", state="absent", **params)
        assert not res.failed and not res.result["changed"]


def test_delete_and_delete_again(monkeypatch, fake, path):
    fake.add(path, API_PW)
    fake.add(path, API_KEY)
    assert run(monkeypatch, device_localdomain_account_credential, type="ssh_key", state="absent",
               **CRED).result["changed"]
    assert [c["type"] for c in fake.objects(path)] == ["password"]
    assert not run(monkeypatch, device_localdomain_account_credential, type="ssh_key", state="absent",
                   **CRED).result["changed"]


def test_delete_check_mode(monkeypatch, fake, path):
    fake.add(path, API_PW)
    assert run(monkeypatch, device_localdomain_account_credential, check_mode=True, type="password", state="absent",
               **CRED).result["changed"]
    assert len(fake.objects(path)) == 1


def test_info(monkeypatch, fake, path):
    fake.add(path, API_PW)
    fake.add(path, API_KEY)
    one = run(monkeypatch, device_localdomain_account_credential_info, type="ssh_key", **CRED).result
    assert not one["changed"] and len(one["credentials"]) == 1
    assert one["credentials"][0]["public_key"] == "ssh-ed25519 AAA" and "private_key" not in one["credentials"][0]
    every = run(monkeypatch, device_localdomain_account_credential_info, **CRED).result["credentials"]
    assert sorted(c["type"] for c in every) == ["password", "ssh_key"]
    assert all("password" not in c for c in every)
    unknown_account = dict(CRED)
    unknown_account["account_name"] = "x"
    assert run(monkeypatch, device_localdomain_account_credential_info, **unknown_account).failed
