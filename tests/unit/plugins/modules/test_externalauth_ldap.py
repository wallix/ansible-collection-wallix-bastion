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
from ansible_collections.wallix.bastion.plugins.modules import externalauth_ldap as ldap, externalauth_ldap_info as ldap_info
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


PATH = "/api/v3.12/externalauths"
REQUIRED = dict(host="192.0.2.13", port=389, timeout=3, ldap_base="dc=example,dc=com",
                login_attribute="uid", cn_attribute="cn")
EXISTING = dict(authentication_name="ldap", type="LDAP", description="", host="192.0.2.13", port=389,
                timeout=3.0, ldap_base="dc=example,dc=com", login_attribute="uid", cn_attribute="cn",
                is_anonymous_access=False, is_ssl=False, login="cn=bind", password="********",
                ca_certificate="/CN=Example CA", certificate="", private_key="")


def test_create_sends_type(monkeypatch, fake):
    res = run(monkeypatch, ldap, authentication_name="ldap", login="cn=bind", password="pw", **REQUIRED)
    assert not res.failed and res.result["changed"]
    method, path, body = fake.writes()[0]
    assert (method, path) == ("POST", PATH)
    expected = dict(REQUIRED, timeout=3.0)
    assert body == dict(expected, authentication_name="ldap", login="cn=bind", password="pw", type="LDAP")
    assert "password" not in res.result["externalauth"]


def test_create_requires_fields(monkeypatch, fake):
    res = run(monkeypatch, ldap, authentication_name="ldap", host="h")
    assert res.failed and "port, timeout, ldap_base, login_attribute, cn_attribute required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, ldap, check_mode=True, authentication_name="ldap", password="pw", **REQUIRED)
    assert res.result["changed"] and "password" not in res.result["diff"]["after"]
    assert "password" not in res.result["externalauth"]
    assert fake.writes() == []


def test_no_change_is_idempotent(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    res = run(monkeypatch, ldap, authentication_name="ldap", login="cn=bind", password="pw",
              ca_certificate="-----BEGIN CERTIFICATE-----...", **REQUIRED)
    assert not res.failed and not res.result["changed"]
    assert fake.writes() == []


def test_update_sends_only_requested_fields(monkeypatch, fake):
    obj = fake.add("externalauths", EXISTING)
    res = run(monkeypatch, ldap, authentication_name="ldap", description="new", password="pw", ca_certificate="PEM")
    assert res.result["changed"] and res.result["changed_fields"] == ["description"]
    assert fake.writes() == [("PUT", PATH + "/" + obj["id"], {"authentication_name": "ldap", "description": "new"})]
    assert fake.objects("externalauths")[0]["host"] == "192.0.2.13"


def test_update_check_mode(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    res = run(monkeypatch, ldap, check_mode=True, authentication_name="ldap", is_ssl=True, port=636)
    assert res.result["changed"] and res.result["changed_fields"] == ["is_ssl", "port"]
    assert res.result["diff"]["after"]["port"] == 636 and res.result["diff"]["before"]["port"] == 389
    assert fake.writes() == []


def test_update_password_always(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    res = run(monkeypatch, ldap, authentication_name="ldap", password="new", update_password="always")
    assert res.result["changed"] and res.result["changed_fields"] == ["password"]
    assert fake.writes()[0][2] == {"authentication_name": "ldap", "password": "new"}
    assert "password" not in res.result["externalauth"]


def test_empty_write_only_field_clears_it(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    res = run(monkeypatch, ldap, authentication_name="ldap", ca_certificate="")
    assert res.result["changed"] and res.result["changed_fields"] == ["ca_certificate"]
    assert fake.writes()[0][2] == {"authentication_name": "ldap", "ca_certificate": ""}


def test_unset_secret_is_sent_without_always(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    res = run(monkeypatch, ldap, authentication_name="ldap", certificate="PEM", private_key="KEY", passphrase="phrase")
    assert res.result["changed"] and res.result["changed_fields"] == ["certificate", "passphrase", "private_key"]
    assert fake.writes()[0][2] == {"authentication_name": "ldap", "certificate": "PEM", "private_key": "KEY",
                                   "passphrase": "phrase"}


def test_passphrase_requires_private_key(monkeypatch, fake):
    res = run(monkeypatch, ldap, authentication_name="ldap", passphrase="phrase")
    assert res.failed and fake.writes() == []


def test_other_type_with_same_name_fails(monkeypatch, fake):
    fake.add("externalauths", dict(authentication_name="ldap", type="RADIUS"))
    for state in ("present", "absent"):
        res = run(monkeypatch, ldap, authentication_name="ldap", state=state, **REQUIRED)
        assert res.failed and "type RADIUS, not LDAP" in res.result["msg"]
    assert fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    assert run(monkeypatch, ldap, authentication_name="ldap", state="absent").result["changed"]
    assert fake.objects("externalauths") == []
    assert not run(monkeypatch, ldap, authentication_name="ldap", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    assert run(monkeypatch, ldap, check_mode=True, authentication_name="ldap", state="absent").result["changed"]
    assert len(fake.objects("externalauths")) == 1


def test_info_filters_type_and_secrets(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    fake.add("externalauths", dict(EXISTING, authentication_name="ldap-2"))
    fake.add("externalauths", dict(authentication_name="ldap-radius", type="RADIUS", secret="********"))
    one = run(monkeypatch, ldap_info, authentication_name="ldap").result
    assert [o["authentication_name"] for o in one["externalauths"]] == ["ldap"] and not one["changed"]
    assert "password" not in one["externalauths"][0]
    assert sorted(o["authentication_name"] for o in run(monkeypatch, ldap_info).result["externalauths"]) == ["ldap", "ldap-2"]
    assert run(monkeypatch, ldap_info, authentication_name="ldap-radius").result["externalauths"] == []
