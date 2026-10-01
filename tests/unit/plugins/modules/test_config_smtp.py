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
from ansible_collections.wallix.bastion.plugins.modules import config_smtp, config_smtp_info

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


SMTP = dict(protocol="starttls", authentication_method="off", server="smtp.example.com", port=587,
            postmaster_email="postmaster@example.com", sender_name="Bastion", sender_email="bastion@example.com",
            certificate_hash="", user="", password="")


def setup_smtp(fake, **overrides):
    fake.set("config/smtp", dict(SMTP, **overrides))


def test_update_one_field_sends_the_mandatory_ones(monkeypatch, fake):
    setup_smtp(fake)
    res = run(monkeypatch, config_smtp, sender_name="Bastion PROD")
    assert not res.failed and res.result["changed"] and res.result["changed_fields"] == ["sender_name"]
    method, path, body = fake.writes()[0]
    assert (method, path) == ("PUT", "/api/v3.12/config/smtp")
    assert body == dict(protocol="starttls", authentication_method="off", server="smtp.example.com", port=587,
                        postmaster_email="postmaster@example.com", sender_name="Bastion PROD",
                        sender_email="bastion@example.com")
    assert res.result["config_smtp"]["sender_name"] == "Bastion PROD"
    assert "password" not in res.result["config_smtp"]


def test_no_change_is_idempotent(monkeypatch, fake):
    setup_smtp(fake)
    res = run(monkeypatch, config_smtp, server="smtp.example.com", port=587, protocol="starttls")
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []


def test_check_mode_writes_nothing(monkeypatch, fake):
    setup_smtp(fake)
    res = run(monkeypatch, config_smtp, check_mode=True, port=25)
    assert res.result["changed"]
    assert res.result["diff"]["before"]["port"] == 587 and res.result["diff"]["after"]["port"] == 25
    assert fake.writes() == []


def test_password_sent_when_none_is_set(monkeypatch, fake):
    setup_smtp(fake)
    res = run(monkeypatch, config_smtp, authentication_method="login", user="u", password="pw")
    assert res.result["changed"] and "password" in res.result["changed_fields"]
    assert fake.writes()[0][2]["password"] == "pw"
    assert "password" not in res.result["config_smtp"] and "password" not in res.result["diff"]["after"]


def test_masked_password_not_sent_on_create_mode(monkeypatch, fake):
    setup_smtp(fake, authentication_method="login", user="u", password="********")
    res = run(monkeypatch, config_smtp, user="u", password="other")
    assert not res.result["changed"] and fake.writes() == []


def test_clear_text_password_compared(monkeypatch, fake):
    setup_smtp(fake, authentication_method="login", user="u", password="pw")
    assert not run(monkeypatch, config_smtp, password="pw").result["changed"]
    res = run(monkeypatch, config_smtp, password="new")
    assert res.result["changed_fields"] == ["password"] and fake.writes()[0][2]["password"] == "new"


def test_password_always(monkeypatch, fake):
    setup_smtp(fake, authentication_method="login", user="u", password="********")
    res = run(monkeypatch, config_smtp, password="pw", update_password="always")
    assert res.result["changed"] and res.result["changed_fields"] == ["password"]
    assert fake.writes()[0][2]["password"] == "pw"


def test_merge_does_not_send_masked_password(monkeypatch, fake):
    setup_smtp(fake, authentication_method="login", user="u", password="********")
    run(monkeypatch, config_smtp, sender_name="x")
    assert "password" not in fake.writes()[0][2]


def test_api_error_fails(monkeypatch, fake):
    setup_smtp(fake)
    fake.put_status = 400
    res = run(monkeypatch, config_smtp, sender_name="x")
    assert res.failed and res.result["status"] == 400


def test_bad_port(monkeypatch, fake):
    setup_smtp(fake)
    assert run(monkeypatch, config_smtp, port=70000).failed


def test_state_absent_not_supported(monkeypatch, fake):
    setup_smtp(fake)
    assert run(monkeypatch, config_smtp, state="absent").failed
    assert fake.writes() == []


def test_info(monkeypatch, fake):
    setup_smtp(fake, password="secret")
    res = run(monkeypatch, config_smtp_info).result
    assert not res["changed"] and res["config_smtp"]["server"] == "smtp.example.com"
    assert "password" not in res["config_smtp"]
