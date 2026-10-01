# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

from urllib.parse import urlparse

import pytest

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

try:
    from ansible.module_utils.testing import patch_module_args  # ansible-core >= 2.19
except ImportError:
    patch_module_args = None

from ansible_collections.wallix.bastion.plugins.module_utils import client as client_utils
from ansible_collections.wallix.bastion.plugins.module_utils.client import Response
from ansible_collections.wallix.bastion.tests.unit.plugins.module_utils.fake_bastion import FakeBastion
from ansible_collections.wallix.bastion.plugins.modules import config_wsm, config_wsm_info

CONN = dict(bastion_host="bastion.test", bastion_user="admin", bastion_token="token")


class ModuleExit(Exception):
    def __init__(self, result, failed=False):
        super(ModuleExit, self).__init__(result)
        self.result = result
        self.failed = failed


class SingletonBastion(FakeBastion):
    """FakeBastion plus configuration singletons: one object at a fixed path, GET/PUT (POST/DELETE if allowed)."""

    def __init__(self):
        super(SingletonBastion, self).__init__()
        self.singletons = {}
        self.methods = {}
        self.put_status = 204

    def set(self, path, obj, methods=("GET", "PUT")):
        self.singletons[path] = obj
        self.methods[path] = methods

    def handle(self, client, method, url, data, headers, auth):
        prefix = "/api/%s/" % self.api_version
        path = urlparse(url).path
        rel = path[len(prefix):].strip("/") if path.startswith(prefix) else None
        if rel not in self.singletons:
            return super(SingletonBastion, self).handle(client, method, url, data, headers, auth)
        body = json.loads(data) if data else None
        self.calls.append((method, path, body))
        if method not in self.methods[rel]:
            return Response(405, '{"error": "method not allowed"}', {})
        if method == "GET":
            obj = self.singletons[rel]
            return Response(200, json.dumps(obj), {}) if obj is not None else Response(404, "{}", {})
        if self.put_status != 204:
            return Response(self.put_status, '{"error": "refused"}', {})
        self.on_write(rel, method, body)
        return Response(204, "", {})

    def on_write(self, path, method, body):
        if method == "DELETE":
            self.singletons[path] = None
        else:
            self.singletons[path] = dict(self.singletons[path] or {}, **body)


@pytest.fixture
def fake(monkeypatch):
    fake = SingletonBastion()
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


WSM = dict(hostname="wsm.example.com", jwe_public=None, jws_private="********", jws_public="-----BEGIN PUBLIC KEY-----")


def test_update_hostname_sends_both_fields(monkeypatch, fake):
    fake.set("config/wsm", dict(WSM))
    res = run(monkeypatch, config_wsm, hostname="wsm2.example.com")
    assert res.result["changed"] and res.result["changed_fields"] == ["hostname"]
    assert fake.writes() == [("PUT", "/api/v3.12/config/wsm", {"hostname": "wsm2.example.com", "jwe_public": None})]
    assert res.result["config_wsm"] == {"hostname": "wsm2.example.com", "jwe_public": "",
                                        "jws_public": "-----BEGIN PUBLIC KEY-----"}


def test_idempotent_and_null_equals_empty(monkeypatch, fake):
    fake.set("config/wsm", dict(WSM))
    res = run(monkeypatch, config_wsm, hostname="wsm.example.com", jwe_public="")
    assert not res.result["changed"] and fake.writes() == []


def test_clear_hostname_sends_null(monkeypatch, fake):
    fake.set("config/wsm", dict(WSM, jwe_public="KEY"))
    res = run(monkeypatch, config_wsm, hostname="")
    assert res.result["changed"]
    assert fake.writes()[0][2] == {"hostname": None, "jwe_public": "KEY"}


def test_check_mode(monkeypatch, fake):
    fake.set("config/wsm", dict(WSM))
    res = run(monkeypatch, config_wsm, check_mode=True, jwe_public="KEY")
    assert res.result["changed"] and res.result["diff"] == {
        "before": {"hostname": "wsm.example.com", "jwe_public": ""},
        "after": {"hostname": "wsm.example.com", "jwe_public": "KEY"}}
    assert fake.writes() == []


def test_v38_refused(monkeypatch, fake):
    res = run(monkeypatch, config_wsm, api_version="v3.8", hostname="x")
    assert res.failed and "v3.12" in res.result["msg"]
    assert run(monkeypatch, config_wsm_info, api_version="v3.8").failed


def test_info(monkeypatch, fake):
    fake.set("config/wsm", dict(WSM))
    res = run(monkeypatch, config_wsm_info).result
    assert res["config_wsm"] == {"hostname": "wsm.example.com", "jwe_public": "",
                                 "jws_public": "-----BEGIN PUBLIC KEY-----"}
