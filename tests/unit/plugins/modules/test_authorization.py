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
from ansible_collections.wallix.bastion.plugins.modules import authorization, authorization_info
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

    original_handle = fake.handle
    fake.urls = []

    def handle(client, method, url, data, headers, auth):
        fake.urls.append((method, url))
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


def existing(fake, **fields):
    # What the API returns, defaults included.
    obj = dict(authorization_name="auth", user_group="ug", target_group="tg", description="",
               subprotocols=["SSH_SHELL_SESSION", "SSH_SCP_UP"], is_critical=False, is_recorded=False,
               authorize_password_retrieval=True, authorize_sessions=True, approval_required=False,
               has_comment=False, mandatory_comment=False, has_ticket=False, mandatory_ticket=False,
               approvers=[], active_quorum=-1, inactive_quorum=-1, single_connection=False, approval_timeout=0,
               authorize_session_sharing=False, session_sharing_mode=None)
    obj.update(fields)
    return fake.add("authorizations", obj)


def test_create(monkeypatch, fake):
    res = run(monkeypatch, authorization, authorization_name="auth", user_group="ug", target_group="tg",
              authorize_sessions=True, subprotocols=["SSH_SHELL_SESSION"], authorize_password_retrieval=False)
    assert not res.failed and res.result["changed"]
    assert fake.writes()[0][2] == {"authorization_name": "auth", "user_group": "ug", "target_group": "tg",
                                   "authorize_sessions": True, "subprotocols": ["SSH_SHELL_SESSION"],
                                   "authorize_password_retrieval": False}
    assert res.result["authorization"]["id"]


def test_create_without_object_id_header(monkeypatch, fake):
    fake.return_object_id = False
    res = run(monkeypatch, authorization, authorization_name="auth", user_group="ug", target_group="tg",
              subprotocols=["SSH_SHELL_SESSION"])
    assert res.result["changed"] and res.result["authorization"]["id"]


def test_create_requires_groups(monkeypatch, fake):
    res = run(monkeypatch, authorization, authorization_name="auth", user_group="ug")
    assert res.failed and "target_group required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, authorization, check_mode=True, authorization_name="auth", user_group="ug",
              target_group="tg", subprotocols=["SSH_SHELL_SESSION"])
    assert res.result["changed"] and fake.writes() == []


def test_no_change_is_idempotent(monkeypatch, fake):
    existing(fake, approvers=["b", "a"])
    res = run(monkeypatch, authorization, authorization_name="auth", user_group="ug", target_group="tg",
              subprotocols=["SSH_SCP_UP", "SSH_SHELL_SESSION"], approvers=["a", "b"], authorize_sessions=True,
              active_quorum=-1)
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []


def test_update_sends_only_changes_with_force(monkeypatch, fake):
    existing(fake, description="keep me")
    res = run(monkeypatch, authorization, authorization_name="auth", user_group="ug", target_group="tg",
              subprotocols=["SSH_SHELL_SESSION"], is_recorded=True)
    assert res.result["changed"] and res.result["changed_fields"] == ["is_recorded", "subprotocols"]
    method, path, body = fake.writes()[0]
    # The API rejects user_group and target_group in a PUT.
    assert method == "PUT" and body == {"authorization_name": "auth", "subprotocols": ["SSH_SHELL_SESSION"],
                                        "is_recorded": True}
    assert [u for m, u in fake.urls if m == "PUT"][0].endswith("?force=true")
    auth = res.result["authorization"]
    assert auth["subprotocols"] == ["SSH_SHELL_SESSION"] and auth["description"] == "keep me"


def test_groups_cannot_change(monkeypatch, fake):
    existing(fake)
    res = run(monkeypatch, authorization, authorization_name="auth", target_group="other")
    assert res.failed and "target_group cannot be changed" in res.result["msg"]
    assert fake.writes() == []


def test_update_check_mode(monkeypatch, fake):
    existing(fake)
    res = run(monkeypatch, authorization, check_mode=True, authorization_name="auth", description="new")
    assert res.result["changed"] and fake.writes() == []
    assert res.result["diff"]["before"]["description"] == ""
    assert res.result["diff"]["after"]["description"] == "new"


def test_delete_and_delete_again(monkeypatch, fake):
    existing(fake)
    assert run(monkeypatch, authorization, authorization_name="auth", state="absent").result["changed"]
    assert fake.objects("authorizations") == []
    assert not run(monkeypatch, authorization, authorization_name="auth", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    existing(fake)
    assert run(monkeypatch, authorization, check_mode=True, authorization_name="auth", state="absent").result["changed"]
    assert len(fake.objects("authorizations")) == 1


def test_invalid_sharing_mode_is_rejected(monkeypatch, fake):
    res = run(monkeypatch, authorization, authorization_name="auth", session_sharing_mode="full")
    assert res.failed and fake.calls == []


def test_api_error_fails_with_status(monkeypatch, fake):
    res = run(monkeypatch, authorization, authorization_name="auth", user_group="ug", target_group="tg",
              bastion_token="wrong")
    assert res.failed and res.result["status"] == 401


def test_info_by_name_and_all(monkeypatch, fake):
    existing(fake)
    existing(fake, authorization_name="auth2", user_group="ug2")
    one = run(monkeypatch, authorization_info, authorization_name="auth").result
    assert [a["authorization_name"] for a in one["authorizations"]] == ["auth"] and not one["changed"]
    assert len(run(monkeypatch, authorization_info).result["authorizations"]) == 2
    assert run(monkeypatch, authorization_info, authorization_name="nope").result["authorizations"] == []
