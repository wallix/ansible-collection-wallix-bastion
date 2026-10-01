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
from ansible_collections.wallix.bastion.plugins.modules import authdomain_azuread, authdomain_azuread_info
from ansible_collections.wallix.bastion.tests.unit.plugins.module_utils.fake_bastion import FakeBastion

CONN = dict(bastion_host="bastion.test", bastion_user="admin", bastion_token="token")
CREATE = dict(domain_name="entra", auth_domain_name="corp.onmicrosoft.com", default_email_domain="example.com",
              default_language="en", external_auths=["entra-saml"], label="Sign in with Microsoft",
              client_id="00000000-0000-0000-0000-000000000001", entity_id="00000000-0000-0000-0000-000000000002")


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


def az_obj(**kwargs):
    obj = dict(CREATE, type="AzureAD", description="", is_default=False, secondary_auth=[], mappings=[],
               client_secret="********", certificate="", private_key="", passphrase="")
    obj.update(kwargs)
    return obj


def test_create_sends_secrets_and_never_returns_them(monkeypatch, fake):
    res = run(monkeypatch, authdomain_azuread, client_secret="s3cret", **CREATE)
    assert not res.failed and res.result["changed"]
    method, path, body = fake.writes()[0]
    assert method == "POST" and body == dict(CREATE, client_secret="s3cret", type="AzureAD")
    # The fake echoes the secret back in clear; the module must not.
    for key in ("client_secret", "certificate", "private_key", "passphrase"):
        assert key not in res.result["authdomain"]
        assert key not in res.result["diff"]["after"]


def test_create_requires_fields(monkeypatch, fake):
    res = run(monkeypatch, authdomain_azuread, domain_name="entra", label="x")
    assert res.failed and "client_id, entity_id required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, authdomain_azuread, check_mode=True, client_secret="s3cret", **CREATE)
    assert res.result["changed"] and fake.writes() == []
    assert "client_secret" not in res.result["authdomain"] and "client_secret" not in res.result["diff"]["after"]


def test_passphrase_requires_private_key(monkeypatch, fake):
    res = run(monkeypatch, authdomain_azuread, passphrase="pp", **CREATE)
    assert res.failed and "private_key" in res.result["msg"]


def test_secret_not_resent_on_create_only(monkeypatch, fake):
    fake.add("authdomains", az_obj())
    res = run(monkeypatch, authdomain_azuread, client_secret="other", **CREATE)
    assert not res.result["changed"] and fake.writes() == []


def test_update_password_always(monkeypatch, fake):
    fake.add("authdomains", az_obj())
    res = run(monkeypatch, authdomain_azuread, domain_name="entra", client_secret="new", update_password="always")
    assert res.result["changed"] and res.result["changed_fields"] == ["client_secret"]
    assert fake.writes()[0][2] == {"domain_name": "entra", "client_secret": "new", "type": "AzureAD"}
    assert "client_secret" not in res.result["authdomain"]


def test_update_without_secret(monkeypatch, fake):
    fake.add("authdomains", az_obj())
    res = run(monkeypatch, authdomain_azuread, domain_name="entra", label="New", client_secret="s")
    assert res.result["changed_fields"] == ["label"]
    assert fake.writes()[0][2] == {"domain_name": "entra", "label": "New", "type": "AzureAD"}


def test_delete(monkeypatch, fake):
    fake.add("authdomains", az_obj())
    assert run(monkeypatch, authdomain_azuread, domain_name="entra", state="absent").result["changed"]
    assert fake.objects("authdomains") == []


def test_info_hides_secrets(monkeypatch, fake):
    fake.add("authdomains", az_obj(client_secret="in-clear"))
    fake.add("authdomains", az_obj(domain_name="sso", type="SAML"))
    found = run(monkeypatch, authdomain_azuread_info).result["authdomains"]
    assert [d["domain_name"] for d in found] == ["entra"]
    assert "client_secret" not in found[0] and found[0]["client_id"] == CREATE["client_id"]
    assert run(monkeypatch, authdomain_azuread_info, domain_name="sso").result["authdomains"] == []
