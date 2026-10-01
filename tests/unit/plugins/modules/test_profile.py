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
from ansible_collections.wallix.bastion.plugins.modules import profile, profile_info
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


FEATURES = ["wab_audit", "system_audit", "users", "user_groups", "devices", "target_groups", "authorizations",
            "profiles", "wab_settings", "system_settings", "backup", "approval", "credential_recovery"]


def rights(keys, **set_rights):
    return {k: set_rights.get(k) for k in keys}


def features(**kw):
    return rights(FEATURES, **kw)


def transmission(**kw):
    return rights(FEATURES[1:], **kw)


def existing(fake, **fields):
    obj = dict(profile_name="prof", editable=True, description="", gui_features=features(users="modify"),
               gui_transmission=transmission(users="view"), ip_limitation="", target_access=False,
               user_groups_limitation={"enabled": False}, target_groups_limitation={"enabled": False},
               dashboards=["audit"])
    obj.update(fields)
    return fake.add("profiles", obj)


def test_create(monkeypatch, fake):
    res = run(monkeypatch, profile, profile_name="prof", gui_features=dict(users="modify", wab_audit="view"),
              dashboards=["audit"], target_groups_limitation=dict(enabled=True, target_groups=["b", "a"]))
    assert not res.failed and res.result["changed"]
    body = fake.writes()[0][2]
    # Unset rights are sent as null: the Bastion only clears a right on an explicit null.
    assert body["gui_features"] == features(users="modify", wab_audit="view")
    assert body["target_groups_limitation"] == {"enabled": True, "target_groups": ["a", "b"]}
    assert "gui_transmission" not in body


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, profile, check_mode=True, profile_name="prof")
    assert res.result["changed"] and fake.writes() == []


def test_no_change_is_idempotent(monkeypatch, fake):
    existing(fake, dashboards=["opsadmin", "audit"],
             target_groups_limitation={"enabled": True, "target_groups": ["b", "a"], "default_target_group": "b"},
             user_groups_limitation={"enabled": True})
    res = run(monkeypatch, profile, profile_name="prof", gui_features=dict(users="modify"),
              gui_transmission=dict(users="view"), dashboards=["audit", "opsadmin"],
              target_groups_limitation=dict(enabled=True, target_groups=["a", "b"]),
              user_groups_limitation=dict(enabled=True, user_groups=[]))
    assert not res.failed and not res.result["changed"], res.result
    assert res.result["profile"]["target_groups_limitation"]["target_groups"] == ["a", "b"]
    assert fake.writes() == []


def test_update_replaces_rights_and_keeps_the_rest(monkeypatch, fake):
    existing(fake, description="keep me")
    res = run(monkeypatch, profile, profile_name="prof", gui_features=dict(users="view"))
    assert res.result["changed_fields"] == ["gui_features"]
    method, path, body = fake.writes()[0]
    assert method == "PUT" and path.endswith(fake.objects("profiles")[0]["id"])
    assert "profile_name" not in body and "editable" not in body
    assert body["gui_features"] == features(users="view")
    assert body["gui_transmission"] == transmission(users="view")
    assert body["description"] == "keep me" and body["dashboards"] == ["audit"]
    assert body["target_groups_limitation"] == {"enabled": False}


def test_update_sends_force_true(monkeypatch, fake):
    seen = []
    original = fake.handle

    def handle(client, method, url, data, headers, auth):
        seen.append((method, url))
        return original(client, method, url, data, headers, auth)

    fake.handle = handle
    existing(fake)
    run(monkeypatch, profile, profile_name="prof", dashboards=[])
    assert [u for m, u in seen if m == "PUT"][0].endswith("?force=true")


def test_remove_target_group_drops_old_default(monkeypatch, fake):
    existing(fake, target_groups_limitation={"enabled": True, "target_groups": ["a", "b"], "default_target_group": "a"})
    res = run(monkeypatch, profile, profile_name="prof", target_groups_limitation=dict(enabled=True, target_groups=["b"]))
    assert res.result["changed_fields"] == ["target_groups_limitation"]
    assert fake.writes()[0][2]["target_groups_limitation"] == {"enabled": True, "target_groups": ["b"]}


def test_change_default_target_group_keeps_groups(monkeypatch, fake):
    existing(fake, target_groups_limitation={"enabled": True, "target_groups": ["a", "b"], "default_target_group": "a"})
    res = run(monkeypatch, profile, profile_name="prof",
              target_groups_limitation=dict(enabled=True, default_target_group="b"))
    assert res.result["changed_fields"] == ["target_groups_limitation"]
    assert fake.writes()[0][2]["target_groups_limitation"] == {
        "enabled": True, "target_groups": ["a", "b"], "default_target_group": "b"}


def test_disable_limitation(monkeypatch, fake):
    existing(fake, user_groups_limitation={"enabled": True, "user_groups": ["g"]})
    res = run(monkeypatch, profile, profile_name="prof", user_groups_limitation=dict(enabled=False))
    assert res.result["changed_fields"] == ["user_groups_limitation"]
    assert fake.writes()[0][2]["user_groups_limitation"] == {"enabled": False}
    res = run(monkeypatch, profile, profile_name="prof", user_groups_limitation=dict(enabled=False))
    assert not res.result["changed"]


def test_disabled_limitation_with_groups_fails(monkeypatch, fake):
    res = run(monkeypatch, profile, profile_name="prof", user_groups_limitation=dict(enabled=False, user_groups=["g"]))
    assert res.failed and "user_groups_limitation.user_groups require" in res.result["msg"] and fake.writes() == []


def test_invalid_right(monkeypatch, fake):
    res = run(monkeypatch, profile, profile_name="prof", gui_features=dict(profiles="view"))
    assert res.failed and fake.writes() == []
    res = run(monkeypatch, profile, profile_name="prof", gui_transmission=dict(wab_audit="view"))
    assert res.failed and fake.writes() == []


def test_update_check_mode(monkeypatch, fake):
    existing(fake)
    res = run(monkeypatch, profile, check_mode=True, profile_name="prof", ip_limitation="10.0.0.0/8")
    assert res.result["changed"] and res.result["diff"]["after"]["ip_limitation"] == "10.0.0.0/8"
    assert fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake):
    existing(fake)
    assert run(monkeypatch, profile, profile_name="prof", state="absent").result["changed"]
    assert fake.objects("profiles") == []
    assert not run(monkeypatch, profile, profile_name="prof", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    existing(fake)
    assert run(monkeypatch, profile, check_mode=True, profile_name="prof", state="absent").result["changed"]
    assert len(fake.objects("profiles")) == 1


def test_info_by_name_and_all(monkeypatch, fake):
    existing(fake, user_groups_limitation={"enabled": True, "user_groups": ["z", "a"]})
    existing(fake, profile_name="user")
    one = run(monkeypatch, profile_info, profile_name="prof").result
    assert [p["profile_name"] for p in one["profiles"]] == ["prof"]
    assert one["profiles"][0]["user_groups_limitation"]["user_groups"] == ["a", "z"]
    assert len(run(monkeypatch, profile_info).result["profiles"]) == 2
