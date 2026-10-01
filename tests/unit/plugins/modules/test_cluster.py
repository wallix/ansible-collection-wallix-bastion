# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

import pytest
import json

import pytest

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

try:
    from ansible.module_utils.testing import patch_module_args  # ansible-core >= 2.19
except ImportError:
    patch_module_args = None

from ansible_collections.wallix.bastion.plugins.module_utils import client as client_utils
from ansible_collections.wallix.bastion.plugins.modules import cluster, cluster_info
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


EXISTING = {"cluster_name": "farm", "description": "keep me", "accounts": ["adm@local@w1:RDP"],
            "account_mappings": [], "interactive_logins": ["w1:RDP", "w2:RDP"], "applications": []}


def test_create(monkeypatch, fake):
    res = run(monkeypatch, cluster, cluster_name="farm", interactive_logins=["w1:RDP", "w2:RDP"])
    assert not res.failed and res.result["changed"]
    assert res.result["cluster"]["interactive_logins"] == ["w1:RDP", "w2:RDP"]
    assert fake.writes()[0][2] == {"cluster_name": "farm", "interactive_logins": ["w1:RDP", "w2:RDP"]}


def test_create_without_object_id_header(monkeypatch, fake):
    fake.return_object_id = False
    res = run(monkeypatch, cluster, cluster_name="farm", accounts=["adm@local@w1:RDP"])
    assert res.result["changed"] and res.result["cluster"]["id"]


def test_create_needs_a_target(monkeypatch, fake):
    res = run(monkeypatch, cluster, cluster_name="farm", description="d", interactive_logins=[])
    assert res.failed and "at least one target" in res.result["msg"]
    res = run(monkeypatch, cluster, check_mode=True, cluster_name="farm")
    assert res.failed and "at least one target" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, cluster, check_mode=True, cluster_name="farm", account_mappings=["w1:RDP"])
    assert res.result["changed"]
    assert res.result["diff"]["after"]["account_mappings"] == ["w1:RDP"]
    assert fake.writes() == []


def test_no_change_is_idempotent_and_reads_once(monkeypatch, fake):
    fake.add("clusters", EXISTING)
    res = run(monkeypatch, cluster, cluster_name="farm", description="keep me",
              interactive_logins=["w2:RDP", "w1:RDP"], accounts=["adm@local@w1:RDP"])
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []
    reads = [c for c in fake.calls if c[0] == "GET"]
    assert len(reads) == 2  # one search, one GET of the object


def test_update_replaces_list_with_force_and_keeps_unset(monkeypatch, fake):
    obj = fake.add("clusters", EXISTING)
    res = run(monkeypatch, cluster, cluster_name="farm", interactive_logins=["w3:RDP"])
    assert res.result["changed"] and res.result["changed_fields"] == ["interactive_logins"]
    method, path, body = fake.writes()[0]
    assert method == "PUT" and path.endswith("/clusters/%s" % obj["id"])
    assert body["interactive_logins"] == ["w3:RDP"] and body["accounts"] == ["adm@local@w1:RDP"]
    assert body["description"] == "keep me" and "applications" not in body
    assert res.result["cluster"]["interactive_logins"] == ["w3:RDP"]


def test_update_uses_force_query(monkeypatch, fake):
    fake.add("clusters", EXISTING)
    urls = []
    original = fake.handle

    def handle(client, method, url, *args):
        urls.append((method, url))
        return original(client, method, url, *args)

    monkeypatch.setattr(fake, "handle", handle)
    run(monkeypatch, cluster, cluster_name="farm", description="new")
    assert [u for m, u in urls if m == "PUT"][0].endswith("?force=true")


def test_remove_last_targets_fails(monkeypatch, fake):
    fake.add("clusters", dict(EXISTING, accounts=[]))
    res = run(monkeypatch, cluster, cluster_name="farm", interactive_logins=[])
    assert res.failed and "at least one target" in res.result["msg"]
    res = run(monkeypatch, cluster, cluster_name="farm", interactive_logins=[], account_mappings=["w1:RDP"])
    assert not res.failed and res.result["changed"]
    assert fake.objects("clusters")[0]["interactive_logins"] == []


def test_update_check_mode(monkeypatch, fake):
    fake.add("clusters", EXISTING)
    res = run(monkeypatch, cluster, check_mode=True, cluster_name="farm", description="new")
    assert res.result["changed"] and res.result["diff"]["after"]["description"] == "new"
    assert fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake):
    fake.add("clusters", EXISTING)
    assert run(monkeypatch, cluster, cluster_name="farm", state="absent").result["changed"]
    assert fake.objects("clusters") == []
    assert not run(monkeypatch, cluster, cluster_name="farm", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    fake.add("clusters", EXISTING)
    assert run(monkeypatch, cluster, check_mode=True, cluster_name="farm", state="absent").result["changed"]
    assert len(fake.objects("clusters")) == 1


def test_api_error_fails_with_status(monkeypatch, fake):
    res = run(monkeypatch, cluster, cluster_name="farm", interactive_logins=["w1:RDP"], bastion_token="wrong")
    assert res.failed and res.result["status"] == 401


def test_info_by_name_and_all(monkeypatch, fake):
    fake.add("clusters", EXISTING)
    fake.add("clusters", dict(EXISTING, cluster_name="farm2"))
    one = run(monkeypatch, cluster_info, cluster_name="farm").result
    assert [c["cluster_name"] for c in one["clusters"]] == ["farm"] and not one["changed"]
    assert len(run(monkeypatch, cluster_info).result["clusters"]) == 2
    assert run(monkeypatch, cluster_info, cluster_name="nope").result["clusters"] == []
