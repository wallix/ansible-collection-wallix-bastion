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
from ansible_collections.wallix.bastion.plugins.modules import externalauth_kerberos as kerberos, externalauth_kerberos_info as kerberos_info
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
REQUIRED = dict(host="192.0.2.12", port=88, ker_dom_controller="EXAMPLE.COM", keytab="BQI...")
EXISTING = dict(authentication_name="krb", type="KERBEROS", description="", host="192.0.2.12", port=88,
                ker_dom_controller="EXAMPLE.COM", keytab="********", use_primary_auth_domain=False,
                principal_list=["HTTP/x@EXAMPLE.COM :: aes256-cts-hmac-sha1-96 :: 1"])


def test_create(monkeypatch, fake):
    res = run(monkeypatch, kerberos, authentication_name="krb", **REQUIRED)
    assert not res.failed and res.result["changed"]
    assert fake.writes()[0] == ("POST", PATH, dict(REQUIRED, authentication_name="krb", type="KERBEROS"))
    assert res.result["externalauth"]["kerberos_password"] is False
    assert "keytab" not in res.result["externalauth"]


def test_create_kerberos_password(monkeypatch, fake):
    res = run(monkeypatch, kerberos, authentication_name="krb", kerberos_password=True, **REQUIRED)
    assert fake.writes()[0][2] == dict(REQUIRED, authentication_name="krb", type="KERBEROS-PASSWORD")
    assert res.result["externalauth"]["kerberos_password"] is True


def test_create_requires_keytab(monkeypatch, fake):
    res = run(monkeypatch, kerberos, authentication_name="krb", host="h", port=88, ker_dom_controller="R")
    assert res.failed and "keytab required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, kerberos, check_mode=True, authentication_name="krb", **REQUIRED)
    assert res.result["changed"] and "keytab" not in res.result["externalauth"]
    assert fake.writes() == []


def test_no_change_is_idempotent(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    res = run(monkeypatch, kerberos, authentication_name="krb", kerberos_password=False, **REQUIRED)
    assert not res.result["changed"] and fake.writes() == []


def test_update_keeps_unset_options(monkeypatch, fake):
    obj = fake.add("externalauths", EXISTING)
    res = run(monkeypatch, kerberos, authentication_name="krb", description="new", kerberos_password=False)
    assert res.result["changed_fields"] == ["description"]
    assert fake.writes() == [("PUT", PATH + "/" + obj["id"], {"authentication_name": "krb", "description": "new"})]


def test_kerberos_password_cannot_change(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    res = run(monkeypatch, kerberos, authentication_name="krb", kerberos_password=True)
    assert res.failed and "kerberos_password cannot be changed" in res.result["msg"]
    assert fake.writes() == []


def test_kerberos_password_type_is_managed(monkeypatch, fake):
    fake.add("externalauths", dict(EXISTING, type="KERBEROS-PASSWORD"))
    res = run(monkeypatch, kerberos, authentication_name="krb", kerberos_password=True)
    assert not res.failed and not res.result["changed"]


def test_update_keytab_always(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    res = run(monkeypatch, kerberos, authentication_name="krb", keytab="new", update_password="always")
    assert res.result["changed_fields"] == ["keytab"]
    assert fake.writes()[0][2] == {"authentication_name": "krb", "keytab": "new"}


def test_delete_and_delete_again(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    assert run(monkeypatch, kerberos, authentication_name="krb", state="absent").result["changed"]
    assert not run(monkeypatch, kerberos, authentication_name="krb", state="absent").result["changed"]
    assert fake.objects("externalauths") == []


def test_info(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    fake.add("externalauths", dict(EXISTING, authentication_name="krb-pw", type="KERBEROS-PASSWORD"))
    fake.add("externalauths", dict(authentication_name="rad", type="RADIUS"))
    res = run(monkeypatch, kerberos_info).result["externalauths"]
    assert sorted((o["authentication_name"], o["kerberos_password"]) for o in res) == [("krb", False), ("krb-pw", True)]
    assert all("keytab" not in o for o in res)
