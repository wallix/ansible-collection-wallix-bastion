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
from ansible_collections.wallix.bastion.plugins.modules import authdomain_saml, authdomain_saml_info
from ansible_collections.wallix.bastion.tests.unit.plugins.module_utils.fake_bastion import FakeBastion

CONN = dict(bastion_host="bastion.test", bastion_user="admin", bastion_token="token")
CREATE = dict(domain_name="sso", auth_domain_name="sso.example.com", default_email_domain="example.com",
              default_language="en", external_auths=["idp"], label="Sign in")


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


def saml_obj(**kwargs):
    """A SAML domain as GET /authdomains/<id> returns it on Bastion 12.4."""
    obj = {"domain_name": "sso", "type": "SAML", "description": "", "is_default": False,
           "auth_domain_name": "sso.example.com", "external_auths": ["idp"], "secondary_auth": [],
           "default_language": "en", "default_email_domain": "example.com", "mappings": [], "label": "Sign in",
           "idp_initiated_url": "https://bastion.test/api/v3.12/saml?domain=sso&redirect=true", "force_authn": False}
    obj.update(kwargs)
    return obj


def test_create(monkeypatch, fake):
    res = run(monkeypatch, authdomain_saml, force_authn=True, **CREATE)
    assert not res.failed and res.result["changed"]
    method, path, body = fake.writes()[0]
    assert method == "POST" and body == dict(CREATE, force_authn=True, type="SAML")


def test_create_requires_label(monkeypatch, fake):
    params = dict(CREATE)
    del params["label"]
    res = run(monkeypatch, authdomain_saml, **params)
    assert res.failed and "label required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, authdomain_saml, check_mode=True, **CREATE)
    assert res.result["changed"] and fake.writes() == []


def test_no_change_ignores_read_only_fields(monkeypatch, fake):
    fake.add("authdomains", saml_obj())
    res = run(monkeypatch, authdomain_saml, force_authn=False, **CREATE)
    assert not res.result["changed"] and fake.writes() == []
    assert res.result["authdomain"]["idp_initiated_url"].endswith("domain=sso&redirect=true")


def test_update(monkeypatch, fake):
    fake.add("authdomains", saml_obj())
    res = run(monkeypatch, authdomain_saml, domain_name="sso", label="New label", force_authn=True)
    assert res.result["changed_fields"] == ["force_authn", "label"]
    body = fake.writes()[0][2]
    # The PUT refuses read-only fields such as idp_initiated_url.
    assert body == {"domain_name": "sso", "label": "New label", "force_authn": True, "type": "SAML"}


def test_domain_of_another_type_is_not_touched(monkeypatch, fake):
    fake.add("authdomains", saml_obj(type="AzureAD"))
    res = run(monkeypatch, authdomain_saml, domain_name="sso", label="x")
    assert res.failed and "authdomain_azuread" in res.result["msg"]
    assert fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake):
    fake.add("authdomains", saml_obj())
    assert run(monkeypatch, authdomain_saml, domain_name="sso", state="absent").result["changed"]
    assert fake.objects("authdomains") == []
    assert not run(monkeypatch, authdomain_saml, domain_name="sso", state="absent").result["changed"]


def test_info_filters_on_type(monkeypatch, fake):
    fake.add("authdomains", saml_obj())
    fake.add("authdomains", saml_obj(domain_name="corp", type="AD"))
    assert [d["domain_name"] for d in run(monkeypatch, authdomain_saml_info).result["authdomains"]] == ["sso"]
    assert len(run(monkeypatch, authdomain_saml_info, domain_name="sso").result["authdomains"]) == 1
    assert run(monkeypatch, authdomain_saml_info, domain_name="corp").result["authdomains"] == []
