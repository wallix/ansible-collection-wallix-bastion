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
from ansible_collections.wallix.bastion.plugins.modules import domain_account, domain_account_info
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


ACCOUNTS = "domains/%s/accounts"


@pytest.fixture
def domain_id(fake):
    return fake.add("domains", {"domain_name": "corp"})["id"]


def account_obj(**kwargs):
    obj = {"account_name": "admin", "account_login": "Administrator", "description": "", "credentials": [],
           "auto_change_password": True, "auto_change_ssh_key": True, "checkout_policy": "default",
           "resources": [], "certificate_validity": None}
    obj.update(kwargs)
    return obj


def test_create_defaults_checkout_policy(monkeypatch, fake, domain_id):
    res = run(monkeypatch, domain_account, domain_name="corp", account_name="admin", account_login="Administrator",
              resources=["srv:SSH"])
    assert not res.failed and res.result["changed"]
    method, path, body = fake.writes()[0]
    assert method == "POST" and path.endswith("/domains/%s/accounts" % domain_id)
    assert body == {"account_name": "admin", "account_login": "Administrator", "resources": ["srv:SSH"],
                    "checkout_policy": "default"}
    assert res.result["domain_account"]["account_login"] == "Administrator"


def test_create_keeps_given_checkout_policy(monkeypatch, fake, domain_id):
    run(monkeypatch, domain_account, domain_name="corp", account_name="admin", account_login="a",
        checkout_policy="strict")
    assert fake.writes()[0][2]["checkout_policy"] == "strict"


def test_create_requires_account_login(monkeypatch, fake, domain_id):
    res = run(monkeypatch, domain_account, domain_name="corp", account_name="admin")
    assert res.failed and "account_login required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake, domain_id):
    res = run(monkeypatch, domain_account, check_mode=True, domain_name="corp", account_name="admin",
              account_login="a")
    assert res.result["changed"] and res.result["diff"]["after"]["account_login"] == "a"
    assert fake.writes() == []


def test_missing_domain_fails(monkeypatch, fake):
    res = run(monkeypatch, domain_account, domain_name="nope", account_name="admin", account_login="a")
    assert res.failed and res.result["msg"] == "domain nope does not exist"


def test_missing_domain_absent_is_noop(monkeypatch, fake):
    res = run(monkeypatch, domain_account, domain_name="nope", account_name="admin", state="absent")
    assert not res.failed and not res.result["changed"] and res.result["domain_account"] is None


def test_bad_resource_format(monkeypatch, fake, domain_id):
    res = run(monkeypatch, domain_account, domain_name="corp", account_name="admin", account_login="a",
              resources=["srv"])
    assert res.failed and "resources must be" in res.result["msg"]


def test_no_change_is_idempotent(monkeypatch, fake, domain_id):
    fake.add(ACCOUNTS % domain_id, account_obj(resources=["a:SSH", "b:RDP"]))
    res = run(monkeypatch, domain_account, domain_name="corp", account_name="admin", account_login="Administrator",
              resources=["b:RDP", "a:SSH"], auto_change_password=True)
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []


def test_update_keeps_unset_options(monkeypatch, fake, domain_id):
    fake.add(ACCOUNTS % domain_id, account_obj(description="keep me", resources=["a:SSH"]))
    res = run(monkeypatch, domain_account, domain_name="corp", account_name="admin", resources=["b:RDP"])
    assert res.result["changed"] and res.result["changed_fields"] == ["resources"]
    method, _path, body = fake.writes()[0]
    assert method == "PUT"
    assert body == {"account_name": "admin", "resources": ["b:RDP"]}
    obj = fake.objects(ACCOUNTS % domain_id)[0]
    assert obj["description"] == "keep me" and obj["resources"] == ["b:RDP"]


def test_update_uses_force(monkeypatch, fake, domain_id):
    # Without force=true the real API appends to resources instead of replacing them.
    seen = []
    handle = fake.handle

    def spy(client, method, url, *args):
        seen.append((method, url))
        return handle(client, method, url, *args)

    fake.handle = spy
    fake.add(ACCOUNTS % domain_id, account_obj())
    run(monkeypatch, domain_account, domain_name="corp", account_name="admin", description="x")
    assert [u for m, u in seen if m == "PUT"][0].endswith("?force=true")


def test_update_check_mode(monkeypatch, fake, domain_id):
    fake.add(ACCOUNTS % domain_id, account_obj(description="old"))
    res = run(monkeypatch, domain_account, check_mode=True, domain_name="corp", account_name="admin",
              description="new")
    assert res.result["changed"] and res.result["diff"]["after"]["description"] == "new"
    assert fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake, domain_id):
    fake.add(ACCOUNTS % domain_id, account_obj())
    assert run(monkeypatch, domain_account, domain_name="corp", account_name="admin", state="absent").result["changed"]
    assert fake.objects(ACCOUNTS % domain_id) == []
    res = run(monkeypatch, domain_account, domain_name="corp", account_name="admin", state="absent")
    assert not res.result["changed"]


def test_delete_check_mode(monkeypatch, fake, domain_id):
    fake.add(ACCOUNTS % domain_id, account_obj())
    res = run(monkeypatch, domain_account, check_mode=True, domain_name="corp", account_name="admin", state="absent")
    assert res.result["changed"] and len(fake.objects(ACCOUNTS % domain_id)) == 1


def test_info(monkeypatch, fake, domain_id):
    fake.add(ACCOUNTS % domain_id, account_obj(account_name="admin"))
    fake.add(ACCOUNTS % domain_id, account_obj(account_name="admin2"))
    one = run(monkeypatch, domain_account_info, domain_name="corp", account_name="admin").result
    assert [a["account_name"] for a in one["domain_accounts"]] == ["admin"] and not one["changed"]
    assert len(run(monkeypatch, domain_account_info, domain_name="corp").result["domain_accounts"]) == 2
    assert run(monkeypatch, domain_account_info, domain_name="corp", account_name="x").result["domain_accounts"] == []
    res = run(monkeypatch, domain_account_info, domain_name="nope")
    assert res.failed and res.result["msg"] == "domain nope does not exist"
