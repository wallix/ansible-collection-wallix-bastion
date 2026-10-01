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
from ansible_collections.wallix.bastion.plugins.modules import timeframe, timeframe_info
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


P1 = {"start_date": "2026-01-01", "end_date": "2026-12-31", "start_time": "08:00", "end_time": "18:00",
      "week_days": ["tuesday", "monday"]}
P2 = {"start_date": "2026-02-01", "end_date": "2026-03-31", "start_time": "09:00", "end_time": "10:00",
      "week_days": ["sunday"]}
STORED_P1 = dict(P1, week_days=["monday", "tuesday"])


def test_create(monkeypatch, fake):
    res = run(monkeypatch, timeframe, timeframe_name="tf", description="d", periods=[P1, P2])
    assert not res.failed and res.result["changed"]
    stored = fake.objects("timeframes")[0]
    assert stored["periods"] == [STORED_P1, P2]
    assert res.result["timeframe"]["description"] == "d"


def test_create_name_only(monkeypatch, fake):
    res = run(monkeypatch, timeframe, timeframe_name="tf")
    assert res.result["changed"] and fake.writes()[0][2] == {"timeframe_name": "tf"}


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, timeframe, check_mode=True, timeframe_name="tf", periods=[P1])
    assert res.result["changed"]
    assert res.result["diff"]["after"]["periods"] == [STORED_P1]
    assert fake.writes() == []


def test_period_and_week_day_order_is_not_a_change(monkeypatch, fake):
    fake.add("timeframes", {"timeframe_name": "tf", "description": "", "is_overtimable": False,
                            "periods": [STORED_P1, P2]})
    res = run(monkeypatch, timeframe, timeframe_name="tf", is_overtimable=False,
              periods=[P2, dict(P1, week_days=["tuesday", "monday"])])
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []


def test_update_keeps_unset_options(monkeypatch, fake):
    fake.add("timeframes", {"timeframe_name": "tf", "description": "keep me", "is_overtimable": True,
                            "periods": [STORED_P1]})
    res = run(monkeypatch, timeframe, timeframe_name="tf", periods=[P2])
    assert res.result["changed"] and res.result["changed_fields"] == ["periods"]
    method, path, body = fake.writes()[0]
    assert method == "PUT"
    assert body == {"timeframe_name": "tf", "description": "keep me", "is_overtimable": True, "periods": [P2]}
    assert fake.objects("timeframes")[0]["periods"] == [P2]


def test_update_uses_force(monkeypatch, fake):
    fake.add("timeframes", {"timeframe_name": "tf", "periods": [STORED_P1]})
    urls = []
    handle = fake.handle

    def spy(client, method, url, *args):
        urls.append((method, url))
        return handle(client, method, url, *args)

    fake.handle = spy
    run(monkeypatch, timeframe, timeframe_name="tf", periods=[])
    assert [u for m, u in urls if m == "PUT"][0].endswith("?force=true")
    assert fake.objects("timeframes")[0]["periods"] == []


def test_update_check_mode(monkeypatch, fake):
    fake.add("timeframes", {"timeframe_name": "tf", "description": "old", "periods": []})
    res = run(monkeypatch, timeframe, check_mode=True, timeframe_name="tf", description="new")
    assert res.result["changed"]
    assert res.result["diff"]["before"]["description"] == "old"
    assert res.result["diff"]["after"]["description"] == "new"
    assert fake.writes() == []


def test_invalid_formats_fail_before_any_call(monkeypatch, fake):
    for bad in (dict(P1, start_time="8:00"), dict(P1, end_date="2026-13-01"), dict(P1, week_days=[])):
        res = run(monkeypatch, timeframe, timeframe_name="tf", periods=[bad])
        assert res.failed and "periods[0]" in res.result["msg"]
    res = run(monkeypatch, timeframe, timeframe_name="tf", periods=[dict(P1, week_days=["Monday"])])
    assert res.failed
    assert fake.calls == []


def test_delete_and_delete_again(monkeypatch, fake):
    fake.add("timeframes", {"timeframe_name": "tf", "periods": []})
    assert run(monkeypatch, timeframe, timeframe_name="tf", state="absent").result["changed"]
    assert fake.objects("timeframes") == []
    assert not run(monkeypatch, timeframe, timeframe_name="tf", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    fake.add("timeframes", {"timeframe_name": "tf", "periods": []})
    assert run(monkeypatch, timeframe, check_mode=True, timeframe_name="tf", state="absent").result["changed"]
    assert len(fake.objects("timeframes")) == 1


def test_info_by_name_and_all(monkeypatch, fake):
    fake.add("timeframes", {"timeframe_name": "office", "periods": []})
    fake.add("timeframes", {"timeframe_name": "office-2", "periods": []})
    one = run(monkeypatch, timeframe_info, timeframe_name="office").result
    assert [t["timeframe_name"] for t in one["timeframes"]] == ["office"] and not one["changed"]
    assert len(run(monkeypatch, timeframe_info).result["timeframes"]) == 2
    assert run(monkeypatch, timeframe_info, timeframe_name="nope").result["timeframes"] == []
