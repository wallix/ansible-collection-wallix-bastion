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
from ansible_collections.wallix.bastion.plugins.modules import encryption, encryption_info

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


def setup(fake, **state):
    fake.set("encryption", state)

    def on_write(path, method, body):
        fake.singletons[path] = dict(seal_state="unsealed",
                                     encryption_mode="passphrase" if body["new_passphrase"] else "unprotected")
    fake.on_write = on_write


def test_setup_when_needed(monkeypatch, fake):
    setup(fake, seal_state="need_setup", encryption_mode="need_setup")
    res = run(monkeypatch, encryption, new_passphrase="pass")
    assert res.result["changed"] and res.result["action"] == "setup"
    assert fake.writes() == [("PUT", "/api/v3.12/encryption", {"new_passphrase": "pass"})]
    assert res.result["encryption"] == {"seal_state": "unsealed", "encryption_mode": "passphrase", "enabled": True}


def test_setup_check_mode(monkeypatch, fake):
    setup(fake, seal_state="need_setup", encryption_mode="need_setup")
    res = run(monkeypatch, encryption, check_mode=True, new_passphrase="")
    assert res.result["changed"] and res.result["encryption"]["encryption_mode"] == "unprotected"
    assert fake.writes() == []


def test_protected_without_current_is_unchanged(monkeypatch, fake):
    setup(fake, seal_state="unsealed", encryption_mode="passphrase")
    res = run(monkeypatch, encryption, new_passphrase="pass")
    assert not res.result["changed"] and res.result["action"] == "none" and fake.writes() == []


def test_unprotected_with_empty_passphrase_is_unchanged(monkeypatch, fake):
    setup(fake, seal_state="unsealed", encryption_mode="unprotected")
    assert not run(monkeypatch, encryption, new_passphrase="").result["changed"]
    assert fake.writes() == []


def test_unprotected_gets_a_passphrase(monkeypatch, fake):
    setup(fake, seal_state="unsealed", encryption_mode="unprotected")
    res = run(monkeypatch, encryption, new_passphrase="pass")
    assert res.result["changed"] and fake.writes()[0][2] == {"new_passphrase": "pass"}
    assert res.result["diff"]["before"]["encryption_mode"] == "unprotected"
    assert res.result["diff"]["after"]["encryption_mode"] == "passphrase"


def test_unprotected_check_mode(monkeypatch, fake):
    setup(fake, seal_state="unsealed", encryption_mode="unprotected")
    res = run(monkeypatch, encryption, check_mode=True, new_passphrase="pass")
    assert res.result["changed"] and res.result["action"] == "change_passphrase" and fake.writes() == []


def test_rotation(monkeypatch, fake):
    setup(fake, seal_state="unsealed", encryption_mode="passphrase")
    res = run(monkeypatch, encryption, current_passphrase="old", new_passphrase="new")
    assert res.result["changed"]
    assert fake.writes()[0][2] == {"passphrase": "old", "new_passphrase": "new"}


def test_same_passphrase_is_unchanged(monkeypatch, fake):
    setup(fake, seal_state="unsealed", encryption_mode="passphrase")
    assert not run(monkeypatch, encryption, current_passphrase="p", new_passphrase="p").result["changed"]


def test_sealed_fails(monkeypatch, fake):
    setup(fake, seal_state="sealed", encryption_mode="passphrase")
    res = run(monkeypatch, encryption, current_passphrase="old", new_passphrase="new")
    assert res.failed and "sealed" in res.result["msg"] and fake.writes() == []


def test_wrong_passphrase_fails(monkeypatch, fake):
    setup(fake, seal_state="unsealed", encryption_mode="passphrase")
    fake.put_status = 400
    res = run(monkeypatch, encryption, current_passphrase="bad", new_passphrase="new")
    assert res.failed and res.result["status"] == 400


def test_v38_state(monkeypatch, fake):
    fake.api_version = "v3.8"
    setup(fake, encryption="ready")
    res = run(monkeypatch, encryption, api_version="v3.8", new_passphrase="p")
    assert not res.result["changed"] and res.result["encryption"]["enabled"]


def test_info(monkeypatch, fake):
    setup(fake, seal_state="unsealed", encryption_mode="unprotected")
    res = run(monkeypatch, encryption_info).result
    assert res["encryption"] == {"seal_state": "unsealed", "encryption_mode": "unprotected", "enabled": True}
    assert not res["changed"]
