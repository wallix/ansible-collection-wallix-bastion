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
from ansible_collections.wallix.bastion.plugins.modules import application_localdomain, application_localdomain_info
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


API_LD = {"domain_name": "local", "description": "d", "admin_account": None, "enable_password_change": False,
          "password_change_policy": None, "password_change_plugin": None,
          "password_change_plugin_parameters": None, "ca_private_key": "", "ca_public_key": ""}
LD = dict(application_name="web", domain_name="local")


@pytest.fixture
def app_id(fake):
    return fake.add("applications", {"application_name": "web", "category": "web_application"})["id"]


def domains(fake, app_id):
    return fake.objects("applications/%s/localdomains" % app_id)


def test_create(monkeypatch, fake, app_id):
    res = run(monkeypatch, application_localdomain, description="d", **LD)
    assert not res.failed and res.result["changed"]
    method, path, body = fake.writes()[0]
    assert (method, path) == ("POST", "/api/v3.12/applications/%s/localdomains" % app_id)
    assert body == {"domain_name": "local", "description": "d"}
    assert res.result["localdomain"]["id"]


def test_create_with_plugin_parameters_hides_them(monkeypatch, fake, app_id):
    res = run(monkeypatch, application_localdomain, enable_password_change=True, password_change_policy="default",
              password_change_plugin="Unix", password_change_plugin_parameters={"k": "v"}, **LD)
    assert fake.writes()[0][2]["password_change_plugin_parameters"] == {"k": "v"}
    assert "password_change_plugin_parameters" not in res.result["localdomain"]
    assert "password_change_plugin_parameters" not in res.result["diff"]["after"]


def test_create_check_mode_writes_nothing(monkeypatch, fake, app_id):
    res = run(monkeypatch, application_localdomain, check_mode=True, **LD)
    assert res.result["changed"] and fake.writes() == []


def test_create_with_admin_account_fails(monkeypatch, fake, app_id):
    res = run(monkeypatch, application_localdomain, check_mode=True, admin_account="root", **LD)
    assert res.failed and "admin_account cannot be set when creating" in res.result["msg"]
    assert fake.writes() == []


def test_missing_application(monkeypatch, fake):
    res = run(monkeypatch, application_localdomain, **LD)
    assert res.failed and res.result["msg"] == "application web does not exist"
    res = run(monkeypatch, application_localdomain, state="absent", **LD)
    assert not res.failed and not res.result["changed"]


def test_no_change_is_idempotent_and_secrets_on_create_only(monkeypatch, fake, app_id):
    fake.add("applications/%s/localdomains" % app_id, API_LD)
    res = run(monkeypatch, application_localdomain, description="d", password_change_plugin_parameters={"a": 1},
              **LD)
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []


def test_update_password_always_sends_secrets(monkeypatch, fake, app_id):
    fake.add("applications/%s/localdomains" % app_id, API_LD)
    res = run(monkeypatch, application_localdomain, password_change_plugin_parameters={"a": 1},
              update_password="always", **LD)
    assert res.result["changed"] and res.result["changed_fields"] == ["password_change_plugin_parameters"]
    assert fake.writes()[0][2]["password_change_plugin_parameters"] == {"a": 1}


def test_update_admin_account_keeps_unset_options(monkeypatch, fake, app_id):
    obj = fake.add("applications/%s/localdomains" % app_id, API_LD)
    res = run(monkeypatch, application_localdomain, admin_account="admin", **LD)
    assert res.result["changed"] and res.result["changed_fields"] == ["admin_account"]
    method, path, body = fake.writes()[0]
    assert method == "PUT" and path.endswith("/localdomains/%s" % obj["id"])
    # Only the requested fields: the Bastion refuses admin_account next to enable_password_change=false.
    assert body == {"domain_name": "local", "admin_account": "admin"}


def test_update_check_mode(monkeypatch, fake, app_id):
    fake.add("applications/%s/localdomains" % app_id, API_LD)
    res = run(monkeypatch, application_localdomain, check_mode=True, description="new", **LD)
    assert res.result["changed"] and res.result["diff"]["after"]["description"] == "new"
    assert fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake, app_id):
    fake.add("applications/%s/localdomains" % app_id, API_LD)
    assert run(monkeypatch, application_localdomain, state="absent", **LD).result["changed"]
    assert domains(fake, app_id) == []
    assert not run(monkeypatch, application_localdomain, state="absent", **LD).result["changed"]


def test_delete_check_mode(monkeypatch, fake, app_id):
    fake.add("applications/%s/localdomains" % app_id, API_LD)
    res = run(monkeypatch, application_localdomain, check_mode=True, state="absent", **LD)
    assert res.result["changed"] and len(domains(fake, app_id)) == 1


def test_info(monkeypatch, fake, app_id):
    fake.add("applications/%s/localdomains" % app_id, API_LD)
    fake.add("applications/%s/localdomains" % app_id, dict(API_LD, domain_name="local2"))
    one = run(monkeypatch, application_localdomain_info, **LD).result
    assert [d["domain_name"] for d in one["localdomains"]] == ["local"] and not one["changed"]
    assert len(run(monkeypatch, application_localdomain_info, application_name="web").result["localdomains"]) == 2
    assert run(monkeypatch, application_localdomain_info, application_name="web",
               domain_name="x").result["localdomains"] == []
    assert run(monkeypatch, application_localdomain_info, application_name="nope").failed
