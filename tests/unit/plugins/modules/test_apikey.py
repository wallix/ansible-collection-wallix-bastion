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
from ansible_collections.wallix.bastion.plugins.modules import apikey, apikey_info
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


PATH = "apikeys"

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
    res = run(monkeypatch, apikey, apikey_name="ci", ip_limitation="192.0.2.1")
    assert not res.failed and res.result["changed"]
    assert res.result["apikey"]["apikey"] == KEY
    assert res.result["apikey"]["ip_limitation"] == "192.0.2.1"
    assert KEY not in str(res.result["diff"])
    assert keygen.writes()[0][2] == {"apikey_name": "ci", "ip_limitation": "192.0.2.1"}
    again = run(monkeypatch, apikey, apikey_name="ci", ip_limitation="192.0.2.1")
    assert not again.result["changed"] and "apikey" not in again.result["apikey"]
    assert len(keygen.writes()) == 1


def test_create_without_key_header_or_object_id(monkeypatch, fake):
    fake.return_object_id = False
    res = run(monkeypatch, apikey, apikey_name="ci")
    assert res.result["changed"] and res.result["apikey"]["id"] and "apikey" not in res.result["apikey"]


def test_create_check_mode_writes_nothing(monkeypatch, keygen):
    res = run(monkeypatch, apikey, check_mode=True, apikey_name="ci")
    assert res.result["changed"] and "apikey" not in res.result["apikey"]
    assert keygen.writes() == []


def test_update_ip_limitation(monkeypatch, fake):
    fake.add(PATH, {"apikey_name": "ci", "apikey": "********", "ip_limitation": ""})
    res = run(monkeypatch, apikey, apikey_name="ci", ip_limitation="192.0.2.1,192.0.2.2")
    assert res.result["changed"] and res.result["changed_fields"] == ["ip_limitation"]
    assert fake.writes()[0][2] == {"apikey_name": "ci", "ip_limitation": "192.0.2.1,192.0.2.2"}
    assert "apikey" not in res.result["apikey"]


def test_update_check_mode(monkeypatch, fake):
    fake.add(PATH, {"apikey_name": "ci", "apikey": "********", "ip_limitation": ""})
    res = run(monkeypatch, apikey, check_mode=True, apikey_name="ci", ip_limitation="192.0.2.1")
    assert res.result["changed"] and fake.writes() == []
    assert "apikey" not in res.result["apikey"]


def test_delete_and_delete_again(monkeypatch, fake):
    fake.add(PATH, {"apikey_name": "ci", "apikey": "********", "ip_limitation": ""})
    other = fake.add(PATH, {"apikey_name": "ci-other", "apikey": "********", "ip_limitation": ""})
    assert run(monkeypatch, apikey, apikey_name="ci", state="absent").result["changed"]
    assert fake.objects(PATH) == [other]
    assert not run(monkeypatch, apikey, apikey_name="ci", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    fake.add(PATH, {"apikey_name": "ci", "apikey": "********", "ip_limitation": ""})
    assert run(monkeypatch, apikey, check_mode=True, apikey_name="ci", state="absent").result["changed"]
    assert len(fake.objects(PATH)) == 1


def test_info_hides_masked_key(monkeypatch, fake):
    fake.add(PATH, {"apikey_name": "ci", "apikey": "********", "ip_limitation": ""})
    fake.add(PATH, {"apikey_name": "ci2", "apikey": "********", "ip_limitation": ""})
    one = run(monkeypatch, apikey_info, apikey_name="ci").result
    assert [k["apikey_name"] for k in one["apikeys"]] == ["ci"] and "apikey" not in one["apikeys"][0]
    assert len(run(monkeypatch, apikey_info).result["apikeys"]) == 2
    assert run(monkeypatch, apikey_info, apikey_name="nope").result["apikeys"] == []
