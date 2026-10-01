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
from ansible_collections.wallix.bastion.plugins.modules import externalauth_tacacs as tacacs, externalauth_tacacs_info as tacacs_info
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
EXISTING = dict(authentication_name="tac", type="TACACS+", description="", host="192.0.2.11", port=49,
                secret="********", use_primary_auth_domain=False)


def test_create(monkeypatch, fake):
    res = run(monkeypatch, tacacs, authentication_name="tac", host="192.0.2.11", port=49, secret="s")
    assert not res.failed and res.result["changed"]
    assert fake.writes()[0] == ("POST", PATH, dict(authentication_name="tac", host="192.0.2.11", port=49,
                                                   secret="s", type="TACACS+"))
    assert "secret" not in res.result["externalauth"]


def test_create_requires_fields(monkeypatch, fake):
    res = run(monkeypatch, tacacs, authentication_name="tac", host="h")
    assert res.failed and "port, secret required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, tacacs, check_mode=True, authentication_name="tac", host="h", port=49, secret="s")
    assert res.result["changed"] and fake.writes() == []


def test_no_change_is_idempotent(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    res = run(monkeypatch, tacacs, authentication_name="tac", host="192.0.2.11", port=49, secret="other")
    assert not res.result["changed"] and fake.writes() == []


def test_update_keeps_unset_options(monkeypatch, fake):
    obj = fake.add("externalauths", EXISTING)
    res = run(monkeypatch, tacacs, authentication_name="tac", use_primary_auth_domain=True)
    assert res.result["changed"] and res.result["changed_fields"] == ["use_primary_auth_domain"]
    assert fake.writes() == [("PUT", PATH + "/" + obj["id"], {"authentication_name": "tac", "use_primary_auth_domain": True})]


def test_update_secret_always(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    res = run(monkeypatch, tacacs, authentication_name="tac", secret="new", update_password="always")
    assert res.result["changed_fields"] == ["secret"] and fake.writes()[0][2]["secret"] == "new"


def test_delete_and_delete_again(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    assert run(monkeypatch, tacacs, authentication_name="tac", state="absent").result["changed"]
    assert not run(monkeypatch, tacacs, authentication_name="tac", state="absent").result["changed"]
    assert fake.objects("externalauths") == []


def test_info(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    fake.add("externalauths", dict(authentication_name="rad", type="RADIUS"))
    res = run(monkeypatch, tacacs_info).result
    assert [o["authentication_name"] for o in res["externalauths"]] == ["tac"] and "secret" not in res["externalauths"][0]
    assert len(run(monkeypatch, tacacs_info, authentication_name="tac").result["externalauths"]) == 1
