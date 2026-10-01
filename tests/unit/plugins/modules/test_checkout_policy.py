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
from ansible_collections.wallix.bastion.plugins.modules import checkout_policy, checkout_policy_info
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


def existing(fake, **fields):
    obj = dict(checkout_policy_name="cp", description="", enable_lock=False, duration=0, extension=0,
               max_duration=0, change_credentials_at_checkin=False)
    obj.update(fields)
    return fake.add("checkoutpolicies", obj)


LOCK = dict(enable_lock=True, duration=3600, extension=600, max_duration=7200, change_credentials_at_checkin=True)


def test_create(monkeypatch, fake):
    res = run(monkeypatch, checkout_policy, checkout_policy_name="cp", description="d", **LOCK)
    assert not res.failed and res.result["changed"]
    assert fake.writes()[0][2] == dict(LOCK, checkout_policy_name="cp", description="d")
    assert res.result["checkout_policy"]["id"]


def test_create_minimal(monkeypatch, fake):
    res = run(monkeypatch, checkout_policy, checkout_policy_name="cp")
    assert res.result["changed"] and fake.writes()[0][2] == {"checkout_policy_name": "cp"}


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, checkout_policy, check_mode=True, checkout_policy_name="cp", **LOCK)
    assert res.result["changed"] and fake.writes() == []


def test_no_change_is_idempotent(monkeypatch, fake):
    existing(fake, **LOCK)
    res = run(monkeypatch, checkout_policy, checkout_policy_name="cp", **LOCK)
    assert not res.result["changed"] and res.result["changed_fields"] == [] and fake.writes() == []


def test_update_keeps_unset_options(monkeypatch, fake):
    existing(fake, description="keep me", **LOCK)
    res = run(monkeypatch, checkout_policy, checkout_policy_name="cp", duration=1800)
    assert res.result["changed"] and res.result["changed_fields"] == ["duration"]
    method, path, body = fake.writes()[0]
    assert method == "PUT" and body == dict(LOCK, checkout_policy_name="cp", description="keep me", duration=1800)


def test_lock_settings_without_lock_fail(monkeypatch, fake):
    res = run(monkeypatch, checkout_policy, checkout_policy_name="cp", duration=60)
    assert res.failed and "duration require enable_lock=true" in res.result["msg"] and fake.writes() == []
    existing(fake)
    res = run(monkeypatch, checkout_policy, checkout_policy_name="cp", extension=60, change_credentials_at_checkin=True)
    assert res.failed and "change_credentials_at_checkin, extension require" in res.result["msg"]
    res = run(monkeypatch, checkout_policy, checkout_policy_name="cp", enable_lock=False, duration=60)
    assert res.failed and fake.writes() == []


def test_lock_settings_on_locked_policy(monkeypatch, fake):
    existing(fake, **LOCK)
    res = run(monkeypatch, checkout_policy, checkout_policy_name="cp", extension=0, max_duration=3600)
    assert not res.failed and res.result["changed_fields"] == ["extension", "max_duration"]


def test_disable_lock_with_zero_settings(monkeypatch, fake):
    existing(fake, **LOCK)
    res = run(monkeypatch, checkout_policy, checkout_policy_name="cp", enable_lock=False, duration=0)
    assert not res.failed and res.result["changed"]


def test_update_check_mode(monkeypatch, fake):
    existing(fake, description="old")
    res = run(monkeypatch, checkout_policy, check_mode=True, checkout_policy_name="cp", description="new")
    assert res.result["changed"] and res.result["diff"]["after"]["description"] == "new"
    assert fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake):
    existing(fake)
    assert run(monkeypatch, checkout_policy, checkout_policy_name="cp", state="absent").result["changed"]
    assert fake.objects("checkoutpolicies") == []
    assert not run(monkeypatch, checkout_policy, checkout_policy_name="cp", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    existing(fake)
    assert run(monkeypatch, checkout_policy, check_mode=True, checkout_policy_name="cp", state="absent").result["changed"]
    assert len(fake.objects("checkoutpolicies")) == 1


def test_name_is_matched_exactly(monkeypatch, fake):
    existing(fake, checkout_policy_name="cp-long")
    res = run(monkeypatch, checkout_policy, check_mode=True, checkout_policy_name="cp")
    assert res.result["changed"] and "changed_fields" not in res.result


def test_info_by_name_and_all(monkeypatch, fake):
    existing(fake)
    existing(fake, checkout_policy_name="default")
    one = run(monkeypatch, checkout_policy_info, checkout_policy_name="cp").result
    assert [p["checkout_policy_name"] for p in one["checkout_policies"]] == ["cp"] and not one["changed"]
    assert len(run(monkeypatch, checkout_policy_info).result["checkout_policies"]) == 2
    assert run(monkeypatch, checkout_policy_info, checkout_policy_name="nope").result["checkout_policies"] == []
