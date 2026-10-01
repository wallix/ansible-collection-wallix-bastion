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
from ansible_collections.wallix.bastion.plugins.modules import connection_policy, connection_policy_info
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


def stored_policy(**kwargs):
    policy = {
        "connection_policy_name": "cp", "protocol": "SSH", "type": "SSH", "description": "keep me",
        "authentication_methods": ["PASSWORD_VAULT", "PASSWORD_MAPPING"], "is_default": False,
        "options": {
            "session": {"inactivity_timeout": 0, "allow_multi_channels": False, "server_keepalive_type": "none"},
            "trace": {"log_all_kbd": False, "log_group_membership": False},
        },
    }
    policy.update(kwargs)
    return policy


def put_urls(fake):
    urls = []
    handle = fake.handle

    def spy(client, method, url, *args):
        if method == "PUT":
            urls.append(url)
        return handle(client, method, url, *args)

    fake.handle = spy
    return urls


def test_create_defaults_type_to_protocol(monkeypatch, fake):
    res = run(monkeypatch, connection_policy, connection_policy_name="cp", protocol="SSH",
              authentication_methods=["PASSWORD_VAULT"], options={"session": {"inactivity_timeout": 600}})
    assert not res.failed and res.result["changed"]
    assert fake.writes()[0][2] == {"connection_policy_name": "cp", "protocol": "SSH", "type": "SSH",
                                   "authentication_methods": ["PASSWORD_VAULT"],
                                   "options": {"session": {"inactivity_timeout": 600}}}
    assert res.result["connection_policy"]["type"] == "SSH"


def test_create_v38_does_not_send_type(monkeypatch, fake):
    fake.api_version = "v3.8"
    run(monkeypatch, connection_policy, api_version="v3.8", connection_policy_name="cp", protocol="SSH")
    assert "type" not in fake.writes()[0][2]


def test_create_with_explicit_type(monkeypatch, fake):
    run(monkeypatch, connection_policy, connection_policy_name="cp", protocol="SSH", type="SSH-ccn")
    assert fake.objects("connectionpolicies")[0]["type"] == "SSH-ccn"


def test_create_requires_protocol(monkeypatch, fake):
    res = run(monkeypatch, connection_policy, connection_policy_name="cp")
    assert res.failed and "protocol required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, connection_policy, check_mode=True, connection_policy_name="cp", protocol="RDP")
    assert res.result["changed"] and res.result["diff"]["after"]["protocol"] == "RDP"
    assert fake.writes() == []


def test_options_subset_and_order_are_not_a_change(monkeypatch, fake):
    fake.add("connectionpolicies", stored_policy())
    res = run(monkeypatch, connection_policy, connection_policy_name="cp", protocol="SSH",
              authentication_methods=["PASSWORD_MAPPING", "PASSWORD_VAULT"],
              options={"trace": {"log_group_membership": False, "log_all_kbd": False},
                       "session": {"inactivity_timeout": 0}})
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []


def test_options_json_string_is_accepted(monkeypatch, fake):
    fake.add("connectionpolicies", stored_policy())
    res = run(monkeypatch, connection_policy, connection_policy_name="cp",
              options='{"session": {"inactivity_timeout": 0}}')
    assert not res.failed and not res.result["changed"]


def test_bool_and_int_are_different(monkeypatch, fake):
    fake.add("connectionpolicies", stored_policy())
    res = run(monkeypatch, connection_policy, check_mode=True, connection_policy_name="cp",
              options={"session": {"allow_multi_channels": 0}})
    assert res.result["changed"] and res.result["changed_fields"] == ["options"]


def test_options_update_sends_only_requested_keys(monkeypatch, fake):
    fake.add("connectionpolicies", stored_policy())
    urls = put_urls(fake)
    res = run(monkeypatch, connection_policy, connection_policy_name="cp",
              options={"session": {"inactivity_timeout": 600}})
    assert res.result["changed"] and res.result["changed_fields"] == ["options"]
    method, path, body = fake.writes()[0]
    assert method == "PUT" and urls[0].endswith("?force=true")
    assert body == {"connection_policy_name": "cp", "description": "keep me",
                    "authentication_methods": ["PASSWORD_VAULT", "PASSWORD_MAPPING"],
                    "options": {"session": {"inactivity_timeout": 600}}}


def test_update_without_options_does_not_send_them(monkeypatch, fake):
    fake.add("connectionpolicies", stored_policy())
    res = run(monkeypatch, connection_policy, connection_policy_name="cp", protocol="SSH", description="new")
    assert res.result["changed_fields"] == ["description"]
    body = fake.writes()[0][2]
    assert "options" not in body and "protocol" not in body and "type" not in body


def test_options_check_mode_shows_merged_options(monkeypatch, fake):
    fake.add("connectionpolicies", stored_policy())
    res = run(monkeypatch, connection_policy, check_mode=True, connection_policy_name="cp",
              options={"session": {"inactivity_timeout": 600}})
    after = res.result["diff"]["after"]["options"]
    assert after["session"] == {"inactivity_timeout": 600, "allow_multi_channels": False,
                                "server_keepalive_type": "none"}
    assert after["trace"] == {"log_all_kbd": False, "log_group_membership": False}
    assert fake.writes() == []


def test_protocol_and_type_are_create_only(monkeypatch, fake):
    fake.add("connectionpolicies", stored_policy())
    for change in ({"protocol": "RDP"}, {"type": "SSH-ccn"}):
        res = run(monkeypatch, connection_policy, connection_policy_name="cp", **change)
        assert res.failed and "cannot be changed after creation" in res.result["msg"]
    assert fake.writes() == []


def test_authentication_methods_replace(monkeypatch, fake):
    fake.add("connectionpolicies", stored_policy())
    res = run(monkeypatch, connection_policy, connection_policy_name="cp", authentication_methods=["PUBKEY_VAULT"])
    assert res.result["changed_fields"] == ["authentication_methods"]
    assert fake.objects("connectionpolicies")[0]["authentication_methods"] == ["PUBKEY_VAULT"]


def test_delete_and_delete_again(monkeypatch, fake):
    fake.add("connectionpolicies", stored_policy())
    assert run(monkeypatch, connection_policy, connection_policy_name="cp", state="absent").result["changed"]
    assert fake.objects("connectionpolicies") == []
    assert not run(monkeypatch, connection_policy, connection_policy_name="cp", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    fake.add("connectionpolicies", stored_policy())
    res = run(monkeypatch, connection_policy, check_mode=True, connection_policy_name="cp", state="absent")
    assert res.result["changed"] and len(fake.objects("connectionpolicies")) == 1


def test_info_by_name_and_all(monkeypatch, fake):
    fake.add("connectionpolicies", stored_policy(connection_policy_name="SSH"))
    fake.add("connectionpolicies", stored_policy(connection_policy_name="SSH-ccn"))
    one = run(monkeypatch, connection_policy_info, connection_policy_name="SSH").result
    assert [p["connection_policy_name"] for p in one["connection_policies"]] == ["SSH"] and not one["changed"]
    assert len(run(monkeypatch, connection_policy_info).result["connection_policies"]) == 2
    assert run(monkeypatch, connection_policy_info, connection_policy_name="nope").result["connection_policies"] == []
