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
from ansible_collections.wallix.bastion.plugins.module_utils.client import Response
from ansible_collections.wallix.bastion.plugins.modules import configoption_info, local_password_policy_info, version_info
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


VERSION = dict(version="v3.12", version_decimal=3.012, wab_version="12.4", wab_form_factor="appliance",
               wab_version_decimal=12.004, wab_version_hotfix="12.4.1", wab_version_hotfix_decimal=12.004001,
               wab_complete_version="12.4.1 (build 9685)")


def test_version(monkeypatch, fake):
    original = fake.handle

    def handle(client, method, url, data, headers, auth):
        if url.endswith("/api/v3.12/version"):
            fake.calls.append((method, url, None))
            return Response(200, json.dumps(VERSION), {})
        return original(client, method, url, data, headers, auth)

    fake.handle = handle
    res = run(monkeypatch, version_info)
    assert not res.failed and not res.result["changed"] and res.result["version"] == VERSION
    assert fake.writes() == []


def test_version_error(monkeypatch, fake):
    res = run(monkeypatch, version_info, bastion_token="wrong")
    assert res.failed and res.result["status"] == 401


def config(name, sections):
    return dict(id=name, config_name=name, name=name.upper(), date="2026-07-09 11:37:32",
                options=[dict(name=s, options=[dict(name="port", value=3389)]) for s in sections])


def test_configoption_one(monkeypatch, fake):
    fake.add("configoptions", config("rdpproxy", ["globals", "client"]))
    seen = []
    original = fake.handle

    def handle(client, method, url, data, headers, auth):
        seen.append(url)
        return original(client, method, url, data, headers, auth)

    fake.handle = handle
    res = run(monkeypatch, configoption_info, config_id="rdpproxy", options_list=["globals", "client"])
    assert [c["config_name"] for c in res.result["configoptions"]] == ["rdpproxy"]
    assert seen[-1].endswith("/configoptions/rdpproxy?options=globals,client")
    assert run(monkeypatch, configoption_info, config_id="nope").result["configoptions"] == []


def test_configoption_all(monkeypatch, fake):
    fake.add("configoptions", config("rdpproxy", ["globals"]))
    fake.add("configoptions", config("sesman", ["sesman"]))
    assert len(run(monkeypatch, configoption_info).result["configoptions"]) == 2


def test_configoption_options_list_needs_config_id(monkeypatch, fake):
    assert run(monkeypatch, configoption_info, options_list=["globals"]).failed


def test_local_password_policy(monkeypatch, fake):
    fake.add("localpasswordpolicies", dict(password_policy_name="default", password_min_length=12))
    fake.add("localpasswordpolicies", dict(password_policy_name="default-strict", password_min_length=16))
    one = run(monkeypatch, local_password_policy_info, password_policy_name="default").result
    assert [p["password_min_length"] for p in one["local_password_policies"]] == [12] and not one["changed"]
    assert len(run(monkeypatch, local_password_policy_info).result["local_password_policies"]) == 2
    assert fake.writes() == []
