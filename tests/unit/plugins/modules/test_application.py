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
from ansible_collections.wallix.bastion.plugins.modules import application, application_info
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


API_WEB = {"application_name": "web", "description": "", "category": "web_application", "last_connection": None,
           "local_domains": [], "global_domains": [], "application_url": "https://example.com",
           "login_button_selector": None, "login_form_url": None, "allow_non_post_form": False,
           "tags": [{"key": "k1", "value": "v1"}, {"key": "k2", "value": "v2"}], "connection_policy": "WEBAPP"}
API_STD = {"application_name": "erp", "description": "", "category": "standard", "last_connection": None,
           "local_domains": [], "global_domains": ["corp.local"], "parameters": "-x", "cluster": "jump",
           "target": "jump", "paths": [{"target": "Interactive@srv:RDP", "program": "C:\\erp.exe", "working_dir": ""}],
           "tags": [], "connection_policy": "RDP"}
PATHS = [{"target": "Interactive@srv:RDP", "program": "C:\\erp.exe"}]


def test_create_standard_defaults_category(monkeypatch, fake):
    res = run(monkeypatch, application, application_name="erp", connection_policy="RDP", target="jump", paths=PATHS)
    assert not res.failed and res.result["changed"]
    method, path, body = fake.writes()[0]
    assert (method, path) == ("POST", "/api/v3.12/applications")
    assert body == {"application_name": "erp", "connection_policy": "RDP", "category": "standard", "target": "jump",
                    "paths": [{"target": "Interactive@srv:RDP", "program": "C:\\erp.exe", "working_dir": ""}]}
    assert res.result["application"]["id"]


def test_create_web_application(monkeypatch, fake):
    res = run(monkeypatch, application, application_name="web", connection_policy="WEBAPP",
              category="web_application", application_url="https://example.com")
    assert res.result["changed"]
    assert fake.writes()[0][2] == {"application_name": "web", "connection_policy": "WEBAPP",
                                   "category": "web_application", "application_url": "https://example.com"}


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, application, check_mode=True, application_name="web", connection_policy="WEBAPP",
              category="web_application", application_url="https://example.com")
    assert res.result["changed"] and fake.writes() == []
    assert res.result["application"]["application_url"] == "https://example.com"


def test_create_requires_category_options(monkeypatch, fake):
    res = run(monkeypatch, application, check_mode=True, application_name="erp", connection_policy="RDP",
              paths=PATHS)
    assert res.failed and "target required to create a standard application" in res.result["msg"]
    res = run(monkeypatch, application, application_name="web", connection_policy="WEBAPP",
              category="web_application")
    assert res.failed and "application_url required to create a web_application" in res.result["msg"]
    res = run(monkeypatch, application, application_name="web", category="web_application",
              application_url="https://example.com")
    assert res.failed and "connection_policy required" in res.result["msg"]
    assert fake.writes() == []


def test_empty_paths_fails(monkeypatch, fake):
    fake.add("applications", API_STD)
    res = run(monkeypatch, application, application_name="erp", paths=[])
    assert res.failed and "paths cannot be empty" in res.result["msg"] and fake.writes() == []


def test_no_change_is_idempotent(monkeypatch, fake):
    fake.add("applications", API_STD)
    fake.add("applications", API_WEB)
    res = run(monkeypatch, application, application_name="erp", connection_policy="RDP", category="standard",
              target="jump", paths=PATHS, global_domains=["corp.local"], parameters="-x", tags=[])
    assert not res.result["changed"] and res.result["changed_fields"] == []
    res = run(monkeypatch, application, application_name="web", category="web_application",
              application_url="https://example.com",
              tags=[{"key": "k2", "value": "v2"}, {"key": "k1", "value": "v1"}])
    assert not res.result["changed"]
    assert fake.writes() == []


def test_update_replaces_lists_and_keeps_unset_options(monkeypatch, fake):
    obj = fake.add("applications", API_WEB)
    res = run(monkeypatch, application, application_name="web", tags=[{"key": "k1", "value": "v1"}],
              global_domains=["corp.local"])
    assert res.result["changed"] and res.result["changed_fields"] == ["global_domains", "tags"]
    method, path, body = fake.writes()[0]
    assert (method, path) == ("PUT", "/api/v3.12/applications/%s" % obj["id"])
    # The category is refused in a PUT; read-only and null fields are not sent back.
    assert body == {"application_name": "web", "connection_policy": "WEBAPP", "description": "",
                    "application_url": "https://example.com", "global_domains": ["corp.local"],
                    "tags": [{"key": "k1", "value": "v1"}]}
    assert fake.objects("applications")[0]["tags"] == [{"key": "k1", "value": "v1"}]


def test_update_sends_force_true(monkeypatch, fake):
    seen = []
    original = fake.handle

    def handle(client, method, url, data, headers, auth):
        seen.append((method, url))
        return original(client, method, url, data, headers, auth)

    fake.handle = handle
    fake.add("applications", API_WEB)
    run(monkeypatch, application, application_name="web", tags=[])
    assert [u for m, u in seen if m == "PUT"][0].endswith("?force=true")


def test_update_path_working_dir(monkeypatch, fake):
    fake.add("applications", API_STD)
    res = run(monkeypatch, application, application_name="erp",
              paths=[dict(PATHS[0], working_dir="C:\\")])
    assert res.result["changed"] and res.result["changed_fields"] == ["paths"]
    assert fake.writes()[0][2]["paths"] == [{"target": "Interactive@srv:RDP", "program": "C:\\erp.exe",
                                             "working_dir": "C:\\"}]
    assert "category" not in fake.writes()[0][2]


def test_category_cannot_change(monkeypatch, fake):
    fake.add("applications", API_WEB)
    res = run(monkeypatch, application, application_name="web", category="standard")
    assert res.failed and "category cannot be changed" in res.result["msg"] and fake.writes() == []


def test_update_check_mode(monkeypatch, fake):
    fake.add("applications", API_WEB)
    res = run(monkeypatch, application, check_mode=True, application_name="web", description="new")
    assert res.result["changed"] and res.result["diff"]["after"]["description"] == "new"
    assert res.result["diff"]["before"]["description"] == ""
    assert fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake):
    fake.add("applications", API_WEB)
    assert run(monkeypatch, application, application_name="web", state="absent").result["changed"]
    assert fake.objects("applications") == []
    assert not run(monkeypatch, application, application_name="web", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    fake.add("applications", API_WEB)
    assert run(monkeypatch, application, check_mode=True, application_name="web", state="absent").result["changed"]
    assert len(fake.objects("applications")) == 1


def test_info(monkeypatch, fake):
    fake.add("applications", API_WEB)
    fake.add("applications", API_STD)
    one = run(monkeypatch, application_info, application_name="web").result
    assert [a["application_name"] for a in one["applications"]] == ["web"] and not one["changed"]
    assert len(run(monkeypatch, application_info).result["applications"]) == 2
    assert run(monkeypatch, application_info, application_name="nope").result["applications"] == []
