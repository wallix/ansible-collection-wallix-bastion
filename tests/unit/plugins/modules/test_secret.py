# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

import pytest

from http.cookiejar import Cookie
from urllib.parse import parse_qs, unquote, urlparse

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

try:
    from ansible.module_utils.testing import patch_module_args  # ansible-core >= 2.19
except ImportError:
    patch_module_args = None

from ansible_collections.wallix.bastion.plugins.module_utils import client as client_utils
from ansible_collections.wallix.bastion.plugins.module_utils.client import Response
from ansible_collections.wallix.bastion.plugins.modules import secret

CONN = dict(bastion_host="bastion.test", bastion_user="admin", bastion_token="token")
TARGET = "root@local@srv"
PASSWORD = "S3cr3t-Pa55"
CHECKOUT = {
    "login": "root",
    "locked": True,
    "checkin_change_password": False,
    "checkin_time": "2026-10-01 11:48:03",
    "deconnection_time": "2099-12-30 23:59:59",
    "password": PASSWORD,
    "ssh_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nAAAA\n-----END OPENSSH PRIVATE KEY-----\n",
    "ssh_key_type": "ssh-ed25519",
    "ssh_certificate": "",
    "remaining_time": 600,
}


class FakeSecrets:
    """In-memory /api/<version>/targetpasswords endpoints, with the answers of a real Bastion 12.4."""

    def __init__(self):
        self.accounts = {TARGET: dict(CHECKOUT)}
        self.checked_out = set()
        self.calls = []

    def handle(self, client, method, url, data=None, headers=None, **kwargs):
        parsed = urlparse(url)
        headers = headers or {}
        self.calls.append(dict(method=method, path=parsed.path, query=parse_qs(parsed.query), headers=dict(headers)))
        if parsed.path == "/api":
            ok = headers.get("X-Auth-Key") == "token" or kwargs.get("url_password") == "secret"
            if not ok:
                return Response(401, '{"error": "Authentication failure"}', {})
            client._cookies.set_cookie(Cookie(0, "wab_session_id", "s", None, False, "bastion.test", False, False,
                                              "/", True, True, None, False, None, None, {}))
            return Response(204, "", {})

        prefix = "/api/v3.12/targetpasswords/"
        assert parsed.path.startswith(prefix), parsed.path
        action, target = parsed.path[len(prefix):].split("/", 1)
        target = unquote(target)
        if target.count("@") not in (1, 2):
            return Response(400, json.dumps({"error": "Bad Request", "description": "Invalid target format.",
                                             "reason": "BAD_TARGET_FORMAT"}), {})
        if target not in self.accounts:
            return Response(403, json.dumps({
                "error": "Access denied",
                "description": "The target does not exist or you don't have the right to access it.",
                "reason": "NOT_AUTHORIZED"}), {})
        if action == "checkout":
            self.checked_out.add(target)
            return Response(200, json.dumps(self.accounts[target]), {})
        if action == "extendcheckout":
            if not self.accounts[target]["locked"]:
                return Response(503, json.dumps({"error": "Service Unavailable",
                                                 "description": "The account checkout period cannot be extended",
                                                 "reason": "UNKNOWN_ERROR"}), {})
            if target not in self.checked_out:
                return Response(409, json.dumps({"error": "Constraint violation",
                                                 "description": "The account is not currently checked out!",
                                                 "reason": "NOT_CHECKED_OUT"}), {})
            return Response(200, json.dumps({"message": None, "extended": True,
                                             "checkin_time": "2026-10-01 11:53:03", "remaining_time": 419}), {})
        if action == "checkin":
            if target not in self.checked_out:
                return Response(409, json.dumps({"error": "Constraint violation",
                                                 "description": "The account is not checked out.",
                                                 "reason": "NOT_CHECKED_OUT"}), {})
            self.checked_out.discard(target)
            return Response(200, "{}", {})
        return Response(404, '{"error": "Resource not found"}', {})

    def api_calls(self):
        return [c for c in self.calls if c["path"] != "/api"]


class ModuleExit(Exception):
    def __init__(self, result, failed=False):
        super(ModuleExit, self).__init__(result)
        self.result = result
        self.failed = failed


@pytest.fixture
def fake(monkeypatch):
    fake = FakeSecrets()

    def _open(self, method, url, data=None, headers=None, **kwargs):
        return fake.handle(self, method, url, data, headers, **kwargs)

    monkeypatch.setattr(client_utils.BastionClient, "_open", _open)

    def exit_json(self, **kwargs):
        raise ModuleExit(kwargs)

    def fail_json(self, **kwargs):
        raise ModuleExit(kwargs, failed=True)

    monkeypatch.setattr(basic.AnsibleModule, "exit_json", exit_json)
    monkeypatch.setattr(basic.AnsibleModule, "fail_json", fail_json)
    for env in ("WALLIX_BASTION_HOST", "WALLIX_BASTION_USER", "WALLIX_BASTION_PASSWORD", "WALLIX_BASTION_TOKEN",
                "WALLIX_BASTION_PORT", "WALLIX_BASTION_API_VERSION"):
        monkeypatch.delenv(env, raising=False)
    return fake


def run(monkeypatch, check_mode=False, **params):
    args = dict(CONN, **params)
    if check_mode:
        args["_ansible_check_mode"] = True
    if patch_module_args is None:
        monkeypatch.setattr(basic, "_ANSIBLE_ARGS", to_bytes(json.dumps({"ANSIBLE_MODULE_ARGS": args})))
        with pytest.raises(ModuleExit) as exc:
            secret.main()
    else:
        with patch_module_args(args), pytest.raises(ModuleExit) as exc:
            secret.main()
    return exc.value


def test_checkout(monkeypatch, fake):
    res = run(monkeypatch, account="root", domain="local", device="srv")
    assert not res.failed and res.result["changed"]
    assert res.result["target"] == TARGET
    assert res.result["login"] == "root"
    assert res.result["password"] == PASSWORD
    assert res.result["ssh_key"].startswith("-----BEGIN")
    assert "ssh_certificate" not in res.result  # empty in the API response
    assert res.result["checkout"]["locked"] is True
    assert "password" not in res.result["checkout"] and "ssh_key" not in res.result["checkout"]
    call = fake.api_calls()[0]
    assert call["method"] == "GET"
    assert call["path"] == "/api/v3.12/targetpasswords/checkout/root@local@srv"
    assert call["query"] == {}


def test_checkout_options_in_query_and_passphrase_in_header(monkeypatch, fake):
    res = run(monkeypatch, account="root", domain="local", device="srv", authorization="auth-1",
              duration=120, key_format="putty", cert_format="openssh", key_passphrase="pass phrase")
    assert not res.failed
    call = fake.api_calls()[0]
    assert call["query"] == {"authorization": ["auth-1"], "duration": ["120"], "key_format": ["putty"],
                             "cert_format": ["openssh"]}
    assert call["headers"]["X-Key-Passphrase"] == "pass phrase"
    assert "pass phrase" not in json.dumps(call["query"])
    login = [c for c in fake.calls if c["path"] == "/api"][0]
    assert "X-Key-Passphrase" not in login["headers"]


def test_checkout_check_mode(monkeypatch, fake):
    res = run(monkeypatch, check_mode=True, account="root", domain="local", device="srv")
    assert not res.failed and res.result["changed"]
    assert "password" not in res.result and "login" not in res.result
    assert res.result["checkout"] == {}
    assert fake.calls == []


@pytest.mark.parametrize("state", ["extend", "checkin"])
def test_check_mode_other_states_make_no_call(monkeypatch, fake, state):
    res = run(monkeypatch, check_mode=True, account="root", domain="local", device="srv", state=state)
    assert not res.failed and res.result["changed"]
    assert fake.calls == []


@pytest.mark.parametrize("params,target", [
    (dict(account="root", domain="local", device="srv"), "root@local@srv"),
    (dict(account="app", domain="local", application="erp"), "app@local@erp"),
    (dict(account="svc", domain="corp.example.com"), "svc@corp.example.com"),
    (dict(account="my account", domain="local", device="srv 1"), "my account@local@srv 1"),
])
def test_target_format(monkeypatch, fake, params, target):
    fake.accounts[target] = dict(CHECKOUT)
    res = run(monkeypatch, **params)
    assert not res.failed and res.result["target"] == target
    path = fake.api_calls()[0]["path"]
    assert unquote(path) == "/api/v3.12/targetpasswords/checkout/" + target
    assert " " not in path


def test_device_and_application_are_exclusive(monkeypatch, fake):
    res = run(monkeypatch, account="root", domain="local", device="srv", application="erp")
    assert res.failed and "mutually exclusive" in res.result["msg"]


def test_unknown_account_fails_cleanly(monkeypatch, fake):
    res = run(monkeypatch, account="nobody", domain="local", device="srv")
    assert res.failed
    assert res.result["status"] == 403
    assert "NOT_AUTHORIZED" in res.result["msg"] and "nobody@local@srv" in res.result["msg"]
    assert "password" not in res.result
    assert PASSWORD not in json.dumps(res.result)


def test_extend(monkeypatch, fake):
    fake.checked_out.add(TARGET)
    res = run(monkeypatch, account="root", domain="local", device="srv", state="extend", authorization="auth-1",
              duration=60)
    assert not res.failed and res.result["changed"]
    assert res.result["checkout"]["extended"] is True
    assert "password" not in res.result
    call = fake.api_calls()[0]
    assert call["path"] == "/api/v3.12/targetpasswords/extendcheckout/root@local@srv"
    assert call["query"] == {"authorization": ["auth-1"]}  # duration only applies to checkout


def test_extend_not_checked_out_fails(monkeypatch, fake):
    res = run(monkeypatch, account="root", domain="local", device="srv", state="extend")
    assert res.failed and res.result["status"] == 409
    assert "NOT_CHECKED_OUT" in res.result["msg"]


def test_extend_without_lock_fails(monkeypatch, fake):
    fake.accounts[TARGET]["locked"] = False
    fake.checked_out.add(TARGET)
    res = run(monkeypatch, account="root", domain="local", device="srv", state="extend")
    assert res.failed and res.result["status"] == 503
    assert "cannot be extended" in res.result["msg"]


def test_checkin_then_checkin_again(monkeypatch, fake):
    fake.checked_out.add(TARGET)
    res = run(monkeypatch, account="root", domain="local", device="srv", state="checkin")
    assert not res.failed and res.result["changed"]
    assert fake.checked_out == set()
    again = run(monkeypatch, account="root", domain="local", device="srv", state="checkin")
    assert not again.failed and not again.result["changed"]
    assert fake.api_calls()[-1]["path"] == "/api/v3.12/targetpasswords/checkin/root@local@srv"


def test_forced_checkin_requires_comment(monkeypatch, fake):
    res = run(monkeypatch, account="root", domain="local", device="srv", state="checkin", force=True)
    assert res.failed and "comment" in res.result["msg"]
    assert fake.calls == []


def test_forced_checkin(monkeypatch, fake):
    fake.checked_out.add(TARGET)
    res = run(monkeypatch, account="root", domain="local", device="srv", state="checkin", force=True,
              comment="left without checkin")
    assert not res.failed and res.result["changed"]
    assert fake.api_calls()[0]["query"] == {"force": ["true"], "comment": ["left without checkin"]}


def test_passphrase_not_sent_outside_checkout(monkeypatch, fake):
    fake.checked_out.add(TARGET)
    run(monkeypatch, account="root", domain="local", device="srv", state="checkin", key_passphrase="pp")
    assert all("X-Key-Passphrase" not in c["headers"] for c in fake.calls)


def test_missing_connection(monkeypatch, fake):
    res = run(monkeypatch, account="root", domain="local", device="srv", bastion_host=None)
    assert res.failed and "bastion_host" in res.result["msg"]
