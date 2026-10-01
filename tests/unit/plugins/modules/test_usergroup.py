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
from ansible_collections.wallix.bastion.plugins.modules import usergroup, usergroup_info
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


KILL = {"action": "kill", "rules": "rm -rf", "subprotocol": "SSH_SHELL_SESSION"}
NOTIFY = {"action": "notify", "rules": "ls", "subprotocol": "SSH_SHELL_SESSION"}


def api_restriction(r):
    # The API gives every restriction an id and a url.
    return dict(r, id="r" + r["action"], url="https://bastion.test/api/v3.12/usergroups/x/restrictions/r")


def existing(fake, **fields):
    obj = dict(group_name="grp", description="", timeframes=["allthetime"], users=["u1"], profile=None,
               language="en", email_list="", restrictions=[api_restriction(KILL)])
    obj.update(fields)
    return fake.add("usergroups", obj)


def test_create(monkeypatch, fake):
    res = run(monkeypatch, usergroup, group_name="grp", timeframes=["allthetime"], users=["u1"],
              restrictions=[KILL])
    assert not res.failed and res.result["changed"]
    assert fake.writes()[0][2] == {"group_name": "grp", "timeframes": ["allthetime"], "users": ["u1"],
                                   "restrictions": [KILL]}
    assert res.result["usergroup"]["id"]


def test_create_without_object_id_header(monkeypatch, fake):
    fake.return_object_id = False
    res = run(monkeypatch, usergroup, group_name="grp", timeframes=["allthetime"])
    assert res.result["changed"] and res.result["usergroup"]["id"]


def test_create_requires_timeframes(monkeypatch, fake):
    res = run(monkeypatch, usergroup, group_name="grp")
    assert res.failed and "timeframes required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, usergroup, check_mode=True, group_name="grp", timeframes=["allthetime"])
    assert res.result["changed"] and fake.writes() == []


def test_no_change_is_idempotent(monkeypatch, fake):
    existing(fake, users=["u2", "u1"], restrictions=[api_restriction(NOTIFY), api_restriction(KILL)])
    res = run(monkeypatch, usergroup, group_name="grp", timeframes=["allthetime"], users=["u1", "u2"],
              restrictions=[KILL, NOTIFY])
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert "id" not in res.result["usergroup"]["restrictions"][0]
    assert fake.writes() == []


def test_update_keeps_unset_options(monkeypatch, fake):
    existing(fake, description="keep me")
    res = run(monkeypatch, usergroup, group_name="grp", users=[])
    assert res.result["changed"] and res.result["changed_fields"] == ["users"]
    method, path, body = fake.writes()[0]
    assert method == "PUT"
    assert body == {"group_name": "grp", "timeframes": ["allthetime"], "description": "keep me",
                    "restrictions": [KILL], "users": []}
    assert fake.objects("usergroups")[0]["users"] == []


def test_update_sends_force_true(monkeypatch, fake):
    seen = []
    original = fake.handle

    def handle(client, method, url, data, headers, auth):
        seen.append((method, url))
        return original(client, method, url, data, headers, auth)

    fake.handle = handle
    existing(fake)
    run(monkeypatch, usergroup, group_name="grp", restrictions=[NOTIFY])
    assert [u for m, u in seen if m == "PUT"][0].endswith("?force=true")


def test_update_check_mode(monkeypatch, fake):
    existing(fake, description="old")
    res = run(monkeypatch, usergroup, check_mode=True, group_name="grp", description="new")
    assert res.result["changed"]
    assert res.result["diff"]["before"]["description"] == "old"
    assert res.result["diff"]["after"]["description"] == "new"
    assert fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake):
    existing(fake)
    assert run(monkeypatch, usergroup, group_name="grp", state="absent").result["changed"]
    assert fake.objects("usergroups") == []
    assert not run(monkeypatch, usergroup, group_name="grp", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    existing(fake)
    assert run(monkeypatch, usergroup, check_mode=True, group_name="grp", state="absent").result["changed"]
    assert len(fake.objects("usergroups")) == 1


def test_invalid_restriction_is_rejected(monkeypatch, fake):
    res = run(monkeypatch, usergroup, group_name="grp", timeframes=["allthetime"],
              restrictions=[dict(KILL, action="block")])
    assert res.failed and fake.writes() == []


def test_api_error_fails_with_status(monkeypatch, fake):
    res = run(monkeypatch, usergroup, group_name="grp", timeframes=["t"], bastion_token="wrong")
    assert res.failed and res.result["status"] == 401


def test_info_by_name_and_all(monkeypatch, fake):
    existing(fake)
    existing(fake, group_name="grp2")
    one = run(monkeypatch, usergroup_info, group_name="grp").result
    assert [g["group_name"] for g in one["usergroups"]] == ["grp"] and not one["changed"]
    assert one["usergroups"][0]["restrictions"] == [KILL]
    assert len(run(monkeypatch, usergroup_info).result["usergroups"]) == 2
    assert run(monkeypatch, usergroup_info, group_name="nope").result["usergroups"] == []
