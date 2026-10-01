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
from ansible_collections.wallix.bastion.plugins.modules import passwordchangepolicy, passwordchangepolicy_info
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


FIELDS = dict(password_length=20, lower_chars=2, upper_chars=2, digit_chars=2, special_chars=0,
              exclude_chars="Il0O", ssh_key_type="ED25519", ssh_key_size=256, change_period="0 3 * * 1")


def existing(fake, **fields):
    obj = dict(password_change_policy_name="pcp", description="", password_length=12, special_chars=None,
               lower_chars=1, upper_chars=None, digit_chars=None, exclude_chars=None, ssh_key_type=None,
               ssh_key_size=None, change_period="")
    obj.update(fields)
    return fake.add("passwordchangepolicies", obj)


def test_create(monkeypatch, fake):
    res = run(monkeypatch, passwordchangepolicy, password_change_policy_name="pcp", **FIELDS)
    assert not res.failed and res.result["changed"]
    assert fake.writes()[0][2] == dict(FIELDS, password_change_policy_name="pcp")
    assert res.result["passwordchangepolicy"]["id"]


def test_create_sends_only_set_options(monkeypatch, fake):
    run(monkeypatch, passwordchangepolicy, password_change_policy_name="pcp", password_length=12, lower_chars=0)
    assert fake.writes()[0][2] == {"password_change_policy_name": "pcp", "password_length": 12, "lower_chars": 0}


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, passwordchangepolicy, check_mode=True, password_change_policy_name="pcp", **FIELDS)
    assert res.result["changed"] and fake.writes() == []


def test_no_change_is_idempotent(monkeypatch, fake):
    existing(fake, **FIELDS)
    res = run(monkeypatch, passwordchangepolicy, password_change_policy_name="pcp", **FIELDS)
    assert not res.result["changed"] and fake.writes() == []


def test_zero_differs_from_unused_class(monkeypatch, fake):
    existing(fake)
    res = run(monkeypatch, passwordchangepolicy, password_change_policy_name="pcp", special_chars=0)
    assert res.result["changed_fields"] == ["special_chars"]


def test_update_keeps_unset_options_and_never_sends_nulls(monkeypatch, fake):
    existing(fake, description="keep me")
    res = run(monkeypatch, passwordchangepolicy, password_change_policy_name="pcp", change_period="0 0 * * *")
    assert res.result["changed_fields"] == ["change_period"]
    method, path, body = fake.writes()[0]
    assert method == "PUT" and body == {"password_change_policy_name": "pcp", "description": "keep me",
                                        "password_length": 12, "lower_chars": 1, "change_period": "0 0 * * *"}


def test_empty_change_period(monkeypatch, fake):
    existing(fake, change_period="0 3 * * 1")
    res = run(monkeypatch, passwordchangepolicy, password_change_policy_name="pcp", change_period="")
    assert res.result["changed"] and fake.objects("passwordchangepolicies")[0]["change_period"] == ""


def test_invalid_ssh_key_type(monkeypatch, fake):
    res = run(monkeypatch, passwordchangepolicy, password_change_policy_name="pcp", ssh_key_type="ed25519")
    assert res.failed and fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake):
    existing(fake)
    assert run(monkeypatch, passwordchangepolicy, password_change_policy_name="pcp", state="absent").result["changed"]
    assert fake.objects("passwordchangepolicies") == []
    assert not run(monkeypatch, passwordchangepolicy, password_change_policy_name="pcp", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    existing(fake)
    res = run(monkeypatch, passwordchangepolicy, check_mode=True, password_change_policy_name="pcp", state="absent")
    assert res.result["changed"] and len(fake.objects("passwordchangepolicies")) == 1


def test_info_by_name_and_all(monkeypatch, fake):
    existing(fake)
    existing(fake, password_change_policy_name="default")
    one = run(monkeypatch, passwordchangepolicy_info, password_change_policy_name="pcp").result
    assert [p["password_change_policy_name"] for p in one["passwordchangepolicies"]] == ["pcp"]
    assert len(run(monkeypatch, passwordchangepolicy_info).result["passwordchangepolicies"]) == 2
