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
from ansible_collections.wallix.bastion.plugins.modules import targetgroup, targetgroup_info
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

    # Like the real API with force=true, a PUT replaces the session sub-lists it gets and keeps the others.
    original_handle = fake.handle
    fake.urls = []
    fake.put_bodies = []

    def handle(client, method, url, data, headers, auth):
        fake.urls.append((method, url))
        if method == "PUT" and data:
            body = json.loads(data)
            fake.put_bodies.append(json.loads(data))
            group = fake.collections.get("targetgroups", {}).get(url.split("?")[0].rsplit("/", 1)[-1])
            if group is not None:
                for parent in ("session", "password_retrieval"):
                    if parent in body:
                        body[parent] = dict(group.get(parent) or {}, **body[parent])
                data = json.dumps(body)
        return original_handle(client, method, url, data, headers, auth)

    fake.handle = handle

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


LOCAL = {"account": "root", "domain": "local", "domain_type": "local", "device": "srv", "service": "SSH"}
GLOBAL = {"account": "admin", "domain": "corp", "domain_type": "global", "device": "srv", "service": "SSH"}
LOGIN = {"device": "srv", "service": "SSH"}
PWD = {"account": "root", "domain": "local", "domain_type": "local", "device": "srv"}
KILL = {"action": "kill", "rules": "rm -rf", "subprotocol": "SSH_SHELL_SESSION"}


def api_item(item, **extra):
    # The API adds an id to every item, plus nulls for unset fields and service_protocol on sessions.
    out = dict(item, id="i-%s" % item.get("account", item.get("device")))
    out.setdefault("application", None)
    if "service" in item:
        out["service_protocol"] = "SSH"
    out.update(extra)
    return out


def existing(fake, **fields):
    obj = dict(
        group_name="tg", description="",
        session=dict(accounts=[api_item(LOCAL)], account_mappings=[], interactive_logins=[api_item(LOGIN)],
                     scenario_accounts=[]),
        password_retrieval=dict(accounts=[api_item(PWD)]),
        restrictions=[dict(KILL, id="r1", url="https://bastion.test/api/v3.12/targetgroups/x/restrictions/r1")],
    )
    obj.update(fields)
    return fake.add("targetgroups", obj)


def test_create_nests_the_lists(monkeypatch, fake):
    res = run(monkeypatch, targetgroup, group_name="tg", description="d", session_accounts=[LOCAL, GLOBAL],
              session_interactive_logins=[LOGIN], password_retrieval_accounts=[PWD], restrictions=[KILL])
    assert not res.failed and res.result["changed"]
    assert fake.writes()[0][2] == {
        "group_name": "tg", "description": "d",
        "session": {"accounts": [LOCAL, GLOBAL], "interactive_logins": [LOGIN]},
        "password_retrieval": {"accounts": [PWD]},
        "restrictions": [KILL],
    }
    tg = res.result["targetgroup"]
    assert tg["id"] and tg["session_accounts"] == [LOCAL, GLOBAL] and tg["session_scenario_accounts"] == []
    assert "session" not in tg


def test_create_without_object_id_header(monkeypatch, fake):
    fake.return_object_id = False
    res = run(monkeypatch, targetgroup, group_name="tg")
    assert res.result["changed"] and res.result["targetgroup"]["id"]


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, targetgroup, check_mode=True, group_name="tg", session_accounts=[LOCAL])
    assert res.result["changed"] and fake.writes() == []
    assert res.result["diff"]["after"]["session_accounts"] == [LOCAL]


def test_no_change_is_idempotent(monkeypatch, fake):
    existing(fake, session=dict(accounts=[api_item(GLOBAL), api_item(LOCAL)], interactive_logins=[api_item(LOGIN)]))
    res = run(monkeypatch, targetgroup, group_name="tg", description="",
              session_accounts=[LOCAL, dict(GLOBAL, application=None)], session_interactive_logins=[LOGIN],
              session_account_mappings=[], password_retrieval_accounts=[PWD], restrictions=[KILL])
    assert not res.failed and not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []
    assert "id" not in res.result["targetgroup"]["session_accounts"][0]


def test_update_replaces_one_list_and_keeps_the_others(monkeypatch, fake):
    existing(fake, description="keep me")
    res = run(monkeypatch, targetgroup, group_name="tg", session_accounts=[GLOBAL])
    assert res.result["changed"] and res.result["changed_fields"] == ["session_accounts"]
    assert [m for m, p, b in fake.writes()] == ["PUT"]
    assert fake.put_bodies == [{"group_name": "tg", "session": {"accounts": [GLOBAL]}}]
    assert [u for m, u in fake.urls if m == "PUT"][0].endswith("?force=true")
    tg = res.result["targetgroup"]
    assert tg["session_accounts"] == [GLOBAL]
    assert tg["session_interactive_logins"] == [LOGIN]
    assert tg["password_retrieval_accounts"] == [PWD]
    assert tg["restrictions"] == [KILL]
    assert tg["description"] == "keep me"


def test_update_empty_list(monkeypatch, fake):
    existing(fake)
    res = run(monkeypatch, targetgroup, group_name="tg", restrictions=[], session_interactive_logins=[])
    assert res.result["changed_fields"] == ["restrictions", "session_interactive_logins"]
    assert fake.put_bodies == [{"group_name": "tg", "restrictions": [], "session": {"interactive_logins": []}}]
    assert res.result["targetgroup"]["restrictions"] == []


def test_update_check_mode(monkeypatch, fake):
    existing(fake, description="old")
    res = run(monkeypatch, targetgroup, check_mode=True, group_name="tg", description="new")
    assert res.result["changed"] and fake.writes() == []
    assert res.result["diff"]["before"]["description"] == "old"
    assert res.result["diff"]["after"]["description"] == "new"


def test_delete_and_delete_again(monkeypatch, fake):
    existing(fake)
    assert run(monkeypatch, targetgroup, group_name="tg", state="absent").result["changed"]
    assert fake.objects("targetgroups") == []
    assert not run(monkeypatch, targetgroup, group_name="tg", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    existing(fake)
    assert run(monkeypatch, targetgroup, check_mode=True, group_name="tg", state="absent").result["changed"]
    assert len(fake.objects("targetgroups")) == 1


@pytest.mark.parametrize("option,item,error", [
    ("session_accounts", {"account": "a", "domain": "d", "domain_type": "local", "device": "srv"},
     "device and service, or application, must be set"),
    ("session_accounts", dict(LOCAL, application="app"), "application is mutually exclusive"),
    ("session_interactive_logins", {"device": "srv"}, "device and service must be set together"),
    ("session_account_mappings", {"service": "SSH", "application": "app"}, "application is mutually exclusive"),
    ("password_retrieval_accounts", {"account": "a", "domain": "d", "domain_type": "global", "device": "srv"},
     "must be unset with domain_type=global"),
    ("session_scenario_accounts", {"account": "a", "domain": "d", "domain_type": "local"},
     "must be set with domain_type=local"),
])
def test_inconsistent_items_fail_before_any_call(monkeypatch, fake, option, item, error):
    res = run(monkeypatch, targetgroup, group_name="tg", **{option: [item]})
    assert res.failed and error in res.result["msg"] and option in res.result["msg"]
    assert fake.calls == []


def test_api_error_fails_with_status(monkeypatch, fake):
    res = run(monkeypatch, targetgroup, group_name="tg", bastion_token="wrong")
    assert res.failed and res.result["status"] == 401


def test_info_by_name_and_all(monkeypatch, fake):
    existing(fake)
    existing(fake, group_name="tg2")
    one = run(monkeypatch, targetgroup_info, group_name="tg").result
    assert [g["group_name"] for g in one["targetgroups"]] == ["tg"] and not one["changed"]
    assert one["targetgroups"][0]["session_accounts"] == [LOCAL]
    assert one["targetgroups"][0]["restrictions"] == [KILL]
    assert len(run(monkeypatch, targetgroup_info).result["targetgroups"]) == 2
    assert run(monkeypatch, targetgroup_info, group_name="nope").result["targetgroups"] == []
