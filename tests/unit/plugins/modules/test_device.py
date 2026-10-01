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
from ansible_collections.wallix.bastion.plugins.modules import device, device_info
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


def test_create(monkeypatch, fake):
    res = run(monkeypatch, device, device_name="srv", host="10.0.0.1", tags=[{"key": "env", "value": "prod"}])
    assert not res.failed and res.result["changed"]
    assert res.result["device"]["host"] == "10.0.0.1"
    assert fake.objects("devices")[0]["tags"] == [{"key": "env", "value": "prod"}]


def test_create_without_object_id_header(monkeypatch, fake):
    fake.return_object_id = False
    res = run(monkeypatch, device, device_name="srv", host="10.0.0.1")
    assert res.result["changed"] and res.result["device"]["id"]


def test_create_requires_host(monkeypatch, fake):
    res = run(monkeypatch, device, device_name="srv")
    assert res.failed and "host required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, device, check_mode=True, device_name="srv", host="10.0.0.1")
    assert res.result["changed"]
    assert res.result["diff"]["after"]["host"] == "10.0.0.1"
    assert fake.writes() == []


def test_no_change_is_idempotent(monkeypatch, fake):
    fake.add("devices", {"device_name": "srv", "host": "10.0.0.1", "alias": "", "description": "",
                         "tags": [{"key": "a", "value": "1"}, {"key": "b", "value": "2"}]})
    res = run(monkeypatch, device, device_name="srv", host="10.0.0.1",
              tags=[{"key": "b", "value": "2"}, {"key": "a", "value": "1"}])
    assert not res.result["changed"]
    assert res.result["changed_fields"] == []
    assert fake.writes() == []


def test_update_keeps_unset_options(monkeypatch, fake):
    fake.add("devices", {"device_name": "srv", "host": "10.0.0.1", "alias": "old", "description": "keep me",
                         "tags": [{"key": "env", "value": "prod"}]})
    res = run(monkeypatch, device, device_name="srv", alias="new")
    assert res.result["changed"] and res.result["changed_fields"] == ["alias"]
    method, path, body = fake.writes()[0]
    assert method == "PUT"
    assert body == {"device_name": "srv", "host": "10.0.0.1", "alias": "new", "description": "keep me",
                    "tags": [{"key": "env", "value": "prod"}]}


def test_update_check_mode(monkeypatch, fake):
    fake.add("devices", {"device_name": "srv", "host": "10.0.0.1", "alias": "old"})
    res = run(monkeypatch, device, check_mode=True, device_name="srv", alias="new")
    assert res.result["changed"]
    assert res.result["diff"] == {"before": {"device_name": "srv", "host": "10.0.0.1", "alias": "old"},
                                  "after": {"device_name": "srv", "host": "10.0.0.1", "alias": "new"}}
    assert fake.writes() == []


def test_empty_tags_clear_tags(monkeypatch, fake):
    fake.add("devices", {"device_name": "srv", "host": "h", "tags": [{"key": "env", "value": "prod"}]})
    res = run(monkeypatch, device, device_name="srv", tags=[])
    assert res.result["changed"] and fake.objects("devices")[0]["tags"] == []


def test_delete_and_delete_again(monkeypatch, fake):
    fake.add("devices", {"device_name": "srv", "host": "h"})
    assert run(monkeypatch, device, device_name="srv", state="absent").result["changed"]
    assert fake.objects("devices") == []
    assert not run(monkeypatch, device, device_name="srv", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    fake.add("devices", {"device_name": "srv", "host": "h"})
    assert run(monkeypatch, device, check_mode=True, device_name="srv", state="absent").result["changed"]
    assert len(fake.objects("devices")) == 1


def test_api_error_fails_with_status(monkeypatch, fake):
    res = run(monkeypatch, device, device_name="srv", host="h", bastion_token="wrong")
    assert res.failed and res.result["status"] == 401


def test_info_by_name_and_all(monkeypatch, fake):
    fake.add("devices", {"device_name": "web-01", "host": "h1"})
    fake.add("devices", {"device_name": "web-010", "host": "h2"})
    one = run(monkeypatch, device_info, device_name="web-01").result
    assert [d["host"] for d in one["devices"]] == ["h1"] and not one["changed"]
    assert len(run(monkeypatch, device_info).result["devices"]) == 2
    assert run(monkeypatch, device_info, device_name="nope").result["devices"] == []
