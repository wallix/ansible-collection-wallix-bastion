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
from ansible_collections.wallix.bastion.plugins.modules import authdomain_ad, authdomain_ad_info
from ansible_collections.wallix.bastion.tests.unit.plugins.module_utils.fake_bastion import FakeBastion

CONN = dict(bastion_host="bastion.test", bastion_user="admin", bastion_token="token")
CREATE = dict(domain_name="corp", auth_domain_name="corp.example.com", default_email_domain="example.com",
              default_language="en", external_auths=["dc01"])


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


def ad_obj(**kwargs):
    """An AD domain as GET /authdomains/<id> returns it on Bastion 12.4."""
    obj = {"domain_name": "corp", "type": "AD", "description": "", "is_default": False,
           "auth_domain_name": "corp.example.com", "external_auths": ["dc01"], "secondary_auth": [],
           "default_language": "en", "default_email_domain": "example.com", "mappings": [],
           "certificate_authority": "", "enable_ca": False, "check_x509_san_email": False, "san_domain_name": "",
           "x509_condition": "", "x509_search_filter": "", "group_attribute": "", "display_name_attribute": "",
           "pubkey_attribute": "", "email_attribute": "", "language_attribute": ""}
    obj.update(kwargs)
    return obj


def test_create_sends_the_type(monkeypatch, fake):
    res = run(monkeypatch, authdomain_ad, group_attribute="memberOf", **CREATE)
    assert not res.failed and res.result["changed"]
    method, path, body = fake.writes()[0]
    assert method == "POST" and path.endswith("/authdomains")
    assert body == dict(CREATE, group_attribute="memberOf", type="AD")
    assert res.result["authdomain"]["group_attribute"] == "memberOf"
    assert res.result["diff"]["before"] == {}


def test_create_requires_fields(monkeypatch, fake):
    res = run(monkeypatch, authdomain_ad, domain_name="corp", auth_domain_name="corp.example.com")
    assert res.failed
    assert "default_email_domain, default_language, external_auths required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, authdomain_ad, check_mode=True, **CREATE)
    assert res.result["changed"] and res.result["diff"]["after"]["external_auths"] == ["dc01"]
    assert fake.writes() == []


def test_bad_language_is_refused(monkeypatch, fake):
    params = dict(CREATE)
    params["default_language"] = "it"
    res = run(monkeypatch, authdomain_ad, **params)
    assert res.failed and "default_language" in res.result["msg"]


def test_no_change_is_idempotent(monkeypatch, fake):
    fake.add("authdomains", ad_obj())
    res = run(monkeypatch, authdomain_ad, **CREATE)
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []


def test_update_sends_only_requested_fields_with_force(monkeypatch, fake):
    fake.add("authdomains", ad_obj(description="old", group_attribute="memberOf"))
    res = run(monkeypatch, authdomain_ad, domain_name="corp", external_auths=["dc02", "dc01"], secondary_auth=[])
    assert res.result["changed"] and res.result["changed_fields"] == ["external_auths"]
    method, path, body = fake.writes()[0]
    assert method == "PUT" and path.endswith("/authdomains/%s" % fake.objects("authdomains")[0]["id"])
    # The real PUT merges, and appends to lists unless ?force=true.
    assert body == {"domain_name": "corp", "external_auths": ["dc02", "dc01"], "secondary_auth": [], "type": "AD"}
    assert res.result["authdomain"]["description"] == "old"
    assert res.result["authdomain"]["group_attribute"] == "memberOf"


def test_update_uses_force(monkeypatch, fake):
    fake.add("authdomains", ad_obj())
    calls = []
    original = fake.handle

    def handle(client, method, url, data, headers, auth):
        calls.append((method, url))
        return original(client, method, url, data, headers, auth)

    fake.handle = handle
    run(monkeypatch, authdomain_ad, domain_name="corp", description="x")
    assert [u for m, u in calls if m == "PUT"][0].endswith("?force=true")


def test_list_order_matters(monkeypatch, fake):
    fake.add("authdomains", ad_obj(external_auths=["dc01", "dc02"]))
    res = run(monkeypatch, authdomain_ad, domain_name="corp", external_auths=["dc02", "dc01"])
    assert res.result["changed"] and res.result["changed_fields"] == ["external_auths"]


def test_update_check_mode(monkeypatch, fake):
    fake.add("authdomains", ad_obj(description="old"))
    res = run(monkeypatch, authdomain_ad, check_mode=True, domain_name="corp", description="new")
    assert res.result["changed"]
    assert res.result["diff"]["before"]["description"] == "old"
    assert res.result["diff"]["after"]["description"] == "new"
    assert fake.writes() == []


def test_domain_of_another_type_is_not_touched(monkeypatch, fake):
    fake.add("authdomains", ad_obj(type="LDAP"))
    res = run(monkeypatch, authdomain_ad, domain_name="corp", description="x")
    assert res.failed and "type LDAP" in res.result["msg"] and "authdomain_ldap" in res.result["msg"]
    res = run(monkeypatch, authdomain_ad, domain_name="corp", state="absent")
    assert res.failed
    assert fake.writes() == []


def test_exact_name_match(monkeypatch, fake):
    fake.add("authdomains", ad_obj(domain_name="corp-eu"))
    res = run(monkeypatch, authdomain_ad, check_mode=True, **CREATE)
    assert res.result["changed"] and res.result["diff"]["before"] == {}


def test_delete_and_delete_again(monkeypatch, fake):
    fake.add("authdomains", ad_obj())
    res = run(monkeypatch, authdomain_ad, domain_name="corp", state="absent")
    assert res.result["changed"] and res.result["authdomain"] is None
    assert fake.objects("authdomains") == []
    assert not run(monkeypatch, authdomain_ad, domain_name="corp", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    fake.add("authdomains", ad_obj())
    assert run(monkeypatch, authdomain_ad, check_mode=True, domain_name="corp", state="absent").result["changed"]
    assert len(fake.objects("authdomains")) == 1


def test_info_filters_on_type(monkeypatch, fake):
    fake.add("authdomains", ad_obj(domain_name="corp"))
    fake.add("authdomains", ad_obj(domain_name="corp2"))
    fake.add("authdomains", ad_obj(domain_name="ldap", type="LDAP"))
    one = run(monkeypatch, authdomain_ad_info, domain_name="corp").result
    assert [d["domain_name"] for d in one["authdomains"]] == ["corp"] and not one["changed"]
    assert sorted(d["domain_name"] for d in run(monkeypatch, authdomain_ad_info).result["authdomains"]) == ["corp", "corp2"]
    assert run(monkeypatch, authdomain_ad_info, domain_name="ldap").result["authdomains"] == []
    assert run(monkeypatch, authdomain_ad_info, domain_name="nope").result["authdomains"] == []
