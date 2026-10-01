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
from ansible_collections.wallix.bastion.plugins.modules import connection_message, connection_message_info
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


def existing(fake, name="motd_en", message="Hello\n"):
    return fake.add("connectionmessages", dict(id=name, message_name=name, message=message))


def test_update(monkeypatch, fake):
    existing(fake)
    res = run(monkeypatch, connection_message, message_name="motd_en", message_text="Bye\n")
    assert not res.failed and res.result["changed"] and res.result["changed_fields"] == ["message_text"]
    assert fake.writes() == [("PUT", "/api/v3.12/connectionmessages/motd_en", {"message": "Bye\n"})]
    assert res.result["connection_message"]["message"] == "Bye\n"
    assert res.result["diff"] == {"before": {"message": "Hello\n"}, "after": {"message": "Bye\n"}}


def test_no_change_is_idempotent(monkeypatch, fake):
    existing(fake)
    res = run(monkeypatch, connection_message, message_name="motd_en", message_text="Hello\n")
    assert not res.result["changed"] and fake.writes() == []


def test_trailing_newline_matters(monkeypatch, fake):
    existing(fake)
    assert run(monkeypatch, connection_message, check_mode=True, message_name="motd_en", message_text="Hello").result["changed"]


def test_check_mode_writes_nothing(monkeypatch, fake):
    existing(fake)
    res = run(monkeypatch, connection_message, check_mode=True, message_name="motd_en", message_text="Bye")
    assert res.result["changed"] and res.result["connection_message"]["message"] == "Bye" and fake.writes() == []


def test_missing_message_fails(monkeypatch, fake):
    res = run(monkeypatch, connection_message, message_name="motd_en", message_text="Bye")
    assert res.failed and fake.writes() == []


def test_absent_is_not_supported(monkeypatch, fake):
    existing(fake)
    res = run(monkeypatch, connection_message, message_name="motd_en", message_text="Bye", state="absent")
    assert res.failed and fake.writes() == []


def test_invalid_name(monkeypatch, fake):
    res = run(monkeypatch, connection_message, message_name="motd_it", message_text="Ciao")
    assert res.failed and fake.writes() == []


def test_info_one_and_all(monkeypatch, fake):
    existing(fake)
    existing(fake, name="login_en", message="Warning")
    one = run(monkeypatch, connection_message_info, message_name="login_en").result
    assert [m["message"] for m in one["connection_messages"]] == ["Warning"] and not one["changed"]
    assert len(run(monkeypatch, connection_message_info).result["connection_messages"]) == 2
    assert run(monkeypatch, connection_message_info, message_name="motd_fr").result["connection_messages"] == []
