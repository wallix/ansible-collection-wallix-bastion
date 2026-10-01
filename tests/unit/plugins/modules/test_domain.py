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
from ansible_collections.wallix.bastion.plugins.modules import domain, domain_info
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


def domain_obj(**kwargs):
    obj = {"domain_name": "corp", "domain_real_name": "", "description": "", "admin_account": None,
           "enable_password_change": False, "password_change_policy": None, "password_change_plugin": None,
           "password_change_plugin_parameters": None, "ca_private_key": "", "ca_public_key": "",
           "vault_plugin": None, "vault_plugin_parameters": None}
    obj.update(kwargs)
    return obj


def test_create(monkeypatch, fake):
    res = run(monkeypatch, domain, domain_name="corp", domain_real_name="corp.example.com",
              ca_private_key="generate:RSA_4096", passphrase="s3cret")
    assert not res.failed and res.result["changed"]
    assert res.result["domain"]["domain_real_name"] == "corp.example.com"
    assert "ca_private_key" not in res.result["domain"] and "passphrase" not in res.result["domain"]
    method, path, body = fake.writes()[0]
    assert method == "POST" and path.endswith("/domains")
    assert body == {"domain_name": "corp", "domain_real_name": "corp.example.com",
                    "ca_private_key": "generate:RSA_4096", "passphrase": "s3cret"}


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, domain, check_mode=True, domain_name="corp", description="d")
    assert res.result["changed"] and res.result["diff"]["after"]["description"] == "d"
    assert fake.writes() == []


def test_create_with_admin_account_fails(monkeypatch, fake):
    res = run(monkeypatch, domain, domain_name="corp", admin_account="admin")
    assert res.failed and "admin_account" in res.result["msg"]
    assert fake.writes() == []


def test_no_change_is_idempotent(monkeypatch, fake):
    fake.add("domains", domain_obj(description="d", ca_private_key="********", ca_public_key="ssh-rsa AAA"))
    res = run(monkeypatch, domain, domain_name="corp", description="d", ca_private_key="generate:RSA_4096")
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []


def test_update_sends_only_requested_fields(monkeypatch, fake):
    fake.add("domains", domain_obj(domain_real_name="corp.example.com", description="old"))
    res = run(monkeypatch, domain, domain_name="corp", description="new")
    assert res.result["changed"] and res.result["changed_fields"] == ["description"]
    method, path, body = fake.writes()[0]
    # The real PUT merges, and fails with HTTP 500 when sent the null fields GET returns.
    assert method == "PUT" and body == {"domain_name": "corp", "description": "new"}
    assert fake.objects("domains")[0]["domain_real_name"] == "corp.example.com"


def test_update_check_mode(monkeypatch, fake):
    fake.add("domains", domain_obj(description="old"))
    res = run(monkeypatch, domain, check_mode=True, domain_name="corp", description="new")
    assert res.result["changed"]
    assert res.result["diff"]["before"]["description"] == "old"
    assert res.result["diff"]["after"]["description"] == "new"
    assert fake.writes() == []


def test_secrets_are_set_when_the_domain_has_none(monkeypatch, fake):
    fake.add("domains", domain_obj())
    res = run(monkeypatch, domain, domain_name="corp", ca_private_key="generate:ED25519", passphrase="pp",
              enable_password_change=True, password_change_policy="default", password_change_plugin="Unix",
              password_change_plugin_parameters={"host": "192.0.2.1"})
    assert res.result["changed"]
    assert "ca_private_key" in res.result["changed_fields"]
    assert "password_change_plugin_parameters" in res.result["changed_fields"]
    body = fake.writes()[0][2]
    assert body["ca_private_key"] == "generate:ED25519" and body["passphrase"] == "pp"
    assert body["password_change_plugin_parameters"] == {"host": "192.0.2.1"}
    assert "password_change_plugin_parameters" not in res.result["domain"]


def test_existing_secrets_are_not_resent_on_create_only(monkeypatch, fake):
    fake.add("domains", domain_obj(ca_private_key="********", ca_public_key="ssh-rsa AAA",
                                   enable_password_change=True, password_change_policy="default",
                                   password_change_plugin="Unix",
                                   password_change_plugin_parameters={"host": "192.0.2.1"}))
    res = run(monkeypatch, domain, domain_name="corp", ca_private_key="-----BEGIN KEY-----", passphrase="pp",
              password_change_plugin_parameters={"host": "192.0.2.2"})
    assert not res.result["changed"] and fake.writes() == []


def test_update_password_always(monkeypatch, fake):
    fake.add("domains", domain_obj(ca_private_key="********", ca_public_key="ssh-rsa AAA",
                                   password_change_plugin_parameters={"host": "192.0.2.1"}))
    res = run(monkeypatch, domain, domain_name="corp", update_password="always", ca_private_key="-----BEGIN KEY-----",
              password_change_plugin_parameters={"host": "192.0.2.2"})
    assert res.result["changed"]
    assert res.result["changed_fields"] == ["ca_private_key", "password_change_plugin_parameters"]
    body = fake.writes()[0][2]
    assert body["ca_private_key"] == "-----BEGIN KEY-----"
    assert body["password_change_plugin_parameters"] == {"host": "192.0.2.2"}


def test_generate_never_replaces_an_existing_ca(monkeypatch, fake):
    fake.add("domains", domain_obj(ca_private_key="********", ca_public_key="ssh-rsa AAA"))
    run(monkeypatch, domain, domain_name="corp", update_password="always", ca_private_key="generate:RSA_4096",
        passphrase="pp", description="x")
    body = fake.writes()[0][2]
    assert "ca_private_key" not in body and "passphrase" not in body


def test_vault_plugin_is_create_only(monkeypatch, fake):
    fake.add("domains", domain_obj(vault_plugin="vault-a", vault_plugin_parameters={"url": "u"}))
    res = run(monkeypatch, domain, domain_name="corp", vault_plugin="vault-b")
    assert res.failed and "vault_plugin cannot be changed" in res.result["msg"]
    assert fake.writes() == []


def test_vault_plugin_conflicts(monkeypatch, fake):
    res = run(monkeypatch, domain, domain_name="corp", vault_plugin="v", enable_password_change=True)
    assert res.failed and "mutually exclusive" in res.result["msg"]
    res = run(monkeypatch, domain, domain_name="corp", vault_plugin="v", ca_private_key="k")
    assert res.failed and "mutually exclusive" in res.result["msg"]


def test_delete_and_delete_again(monkeypatch, fake):
    fake.add("domains", domain_obj())
    assert run(monkeypatch, domain, domain_name="corp", state="absent").result["changed"]
    assert fake.objects("domains") == []
    assert not run(monkeypatch, domain, domain_name="corp", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    fake.add("domains", domain_obj())
    assert run(monkeypatch, domain, check_mode=True, domain_name="corp", state="absent").result["changed"]
    assert len(fake.objects("domains")) == 1


def test_info_by_name_and_all_without_secrets(monkeypatch, fake):
    fake.add("domains", domain_obj(domain_name="corp", ca_private_key="********",
                                   password_change_plugin_parameters={"host": "h"}))
    fake.add("domains", domain_obj(domain_name="corp2"))
    one = run(monkeypatch, domain_info, domain_name="corp").result
    assert [d["domain_name"] for d in one["domains"]] == ["corp"] and not one["changed"]
    assert "ca_private_key" not in one["domains"][0]
    assert "password_change_plugin_parameters" not in one["domains"][0]
    assert len(run(monkeypatch, domain_info).result["domains"]) == 2
    assert run(monkeypatch, domain_info, domain_name="nope").result["domains"] == []
