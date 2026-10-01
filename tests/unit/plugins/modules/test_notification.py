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
from ansible_collections.wallix.bastion.plugins.modules import notification, notification_info
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


CREATE = dict(notification_name="n", enabled=False, type="email", destination="ops@example.com", language="en")


def existing(fake, **fields):
    obj = dict(CREATE, description="", events=["raid_error", "daily_reporting"])
    obj.update(fields)
    return fake.add("notifications", obj)


def test_create(monkeypatch, fake):
    res = run(monkeypatch, notification, events=["raid_error"], **CREATE)
    assert not res.failed and res.result["changed"]
    assert fake.writes()[0][2] == dict(CREATE, events=["raid_error"])


def test_create_requires_fields(monkeypatch, fake):
    res = run(monkeypatch, notification, notification_name="n", enabled=True)
    assert res.failed and "type, destination, language required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, notification, check_mode=True, **CREATE)
    assert res.result["changed"] and fake.writes() == []


def test_no_change_is_idempotent(monkeypatch, fake):
    existing(fake)
    res = run(monkeypatch, notification, events=["daily_reporting", "raid_error"], **CREATE)
    assert not res.result["changed"] and fake.writes() == []


def test_update_events_with_force(monkeypatch, fake):
    seen = []
    original = fake.handle

    def handle(client, method, url, data, headers, auth):
        seen.append((method, url))
        return original(client, method, url, data, headers, auth)

    fake.handle = handle
    existing(fake, description="keep me")
    res = run(monkeypatch, notification, notification_name="n", events=[])
    assert res.result["changed_fields"] == ["events"]
    assert [u for m, u in seen if m == "PUT"][0].endswith("?force=true")
    body = fake.writes()[0][2]
    assert body == dict(CREATE, description="keep me", events=[])


def test_invalid_event(monkeypatch, fake):
    res = run(monkeypatch, notification, events=["bogus"], **CREATE)
    assert res.failed and fake.writes() == []


def test_update_check_mode(monkeypatch, fake):
    existing(fake)
    res = run(monkeypatch, notification, check_mode=True, notification_name="n", enabled=True)
    assert res.result["changed"] and res.result["diff"]["after"]["enabled"] is True and fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake):
    existing(fake)
    assert run(monkeypatch, notification, notification_name="n", state="absent").result["changed"]
    assert fake.objects("notifications") == []
    assert not run(monkeypatch, notification, notification_name="n", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    existing(fake)
    assert run(monkeypatch, notification, check_mode=True, notification_name="n", state="absent").result["changed"]
    assert len(fake.objects("notifications")) == 1


def test_info_by_name_and_all(monkeypatch, fake):
    existing(fake)
    existing(fake, notification_name="n2")
    one = run(monkeypatch, notification_info, notification_name="n").result
    assert [n["notification_name"] for n in one["notifications"]] == ["n"]
    assert len(run(monkeypatch, notification_info).result["notifications"]) == 2
    assert run(monkeypatch, notification_info, notification_name="x").result["notifications"] == []
