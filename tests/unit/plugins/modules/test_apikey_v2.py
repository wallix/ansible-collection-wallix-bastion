# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

import pytest
import json

import pytest

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

try:
    from ansible.module_utils.testing import patch_module_args  # ansible-core >= 2.19
except ImportError:
    patch_module_args = None

from ansible_collections.wallix.bastion.plugins.module_utils import client as client_utils
from ansible_collections.wallix.bastion.plugins.modules import apikey_v2, apikey_v2_info
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


PATH = "apikeys-v2"
EXISTING = {"apikey_name": "mon", "apikey": "********", "profile": "auditor", "description": "keep me",
            "ip_limitation": "192.0.2.1"}

KEY = "generated-key-value-0123456789abcdefghijklm"


@pytest.fixture
def keygen(monkeypatch, fake):
    """Return the generated key in X-Auth-Key on POST, and mask it on GET, like the Bastion."""
    original = fake.handle

    def handle(client, method, url, data, headers, auth):
        resp = original(client, method, url, data, headers, auth)
        if method == "POST" and "/apikeys" in url:
            resp.headers["x-auth-key"] = KEY
            for obj in fake.objects(PATH):
                obj.setdefault("apikey", "********")
        return resp

    monkeypatch.setattr(fake, "handle", handle)
    return fake


def test_create_returns_key_once(monkeypatch, keygen):
    res = run(monkeypatch, apikey_v2, apikey_name="mon", profile="auditor", description="d")
    assert not res.failed and res.result["changed"]
    assert res.result["apikey"]["apikey"] == KEY and res.result["apikey"]["profile"] == "auditor"
    assert keygen.writes()[0][2] == {"apikey_name": "mon", "profile": "auditor", "description": "d"}
    again = run(monkeypatch, apikey_v2, apikey_name="mon", profile="auditor", description="d")
    assert not again.result["changed"] and "apikey" not in again.result["apikey"]


def test_create_requires_profile(monkeypatch, fake):
    res = run(monkeypatch, apikey_v2, apikey_name="mon", description="d")
    assert res.failed and "profile required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, keygen):
    res = run(monkeypatch, apikey_v2, check_mode=True, apikey_name="mon", profile="auditor")
    assert res.result["changed"] and "apikey" not in res.result["apikey"]
    assert keygen.writes() == []


def test_update_description_sends_only_writable_fields(monkeypatch, fake):
    fake.add(PATH, EXISTING)
    res = run(monkeypatch, apikey_v2, apikey_name="mon", profile="auditor", ip_limitation="192.0.2.1", description="new")
    assert res.result["changed"] and res.result["changed_fields"] == ["description"]
    assert fake.writes()[0][2] == {"apikey_name": "mon", "description": "new"}
    assert fake.objects(PATH)[0]["profile"] == "auditor"


def test_create_only_fields_fail(monkeypatch, fake):
    fake.add(PATH, EXISTING)
    res = run(monkeypatch, apikey_v2, apikey_name="mon", profile="user")
    assert res.failed and "profile cannot be changed" in res.result["msg"]
    res = run(monkeypatch, apikey_v2, check_mode=True, apikey_name="mon", ip_limitation="")
    assert res.failed and "ip_limitation cannot be changed" in res.result["msg"]
    assert fake.writes() == []


def test_update_check_mode(monkeypatch, fake):
    fake.add(PATH, EXISTING)
    res = run(monkeypatch, apikey_v2, check_mode=True, apikey_name="mon", description="new")
    assert res.result["changed"] and res.result["diff"]["after"]["description"] == "new"
    assert fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake):
    fake.add(PATH, EXISTING)
    assert run(monkeypatch, apikey_v2, apikey_name="mon", state="absent").result["changed"]
    assert fake.objects(PATH) == []
    assert not run(monkeypatch, apikey_v2, apikey_name="mon", state="absent").result["changed"]


def test_info_hides_masked_key(monkeypatch, fake):
    fake.add(PATH, EXISTING)
    one = run(monkeypatch, apikey_v2_info, apikey_name="mon").result
    assert one["apikeys"][0]["profile"] == "auditor" and "apikey" not in one["apikeys"][0]
    assert run(monkeypatch, apikey_v2_info, apikey_name="nope").result["apikeys"] == []
