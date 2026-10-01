# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.wallix.bastion.plugins.module_utils.client import (
    BastionClient,
    BastionError,
    resolve_connection,
    validate_connection,
)
from ansible_collections.wallix.bastion.tests.unit.plugins.module_utils.fake_bastion import FakeBastion

ENV = ("WALLIX_BASTION_HOST", "WALLIX_BASTION_USER", "WALLIX_BASTION_PASSWORD", "WALLIX_BASTION_TOKEN",
       "WALLIX_BASTION_PORT", "WALLIX_BASTION_API_VERSION", "WALLIX_BASTION_VALIDATE_CERTS",
       "WALLIX_INSECURE_SKIP_VERIFY", "WALLIX_CSRF_ENABLED")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ENV:
        monkeypatch.delenv(name, raising=False)


def client(fake, **kwargs):
    params = dict(bastion_host="bastion.test", bastion_user="admin", bastion_token="token")
    params.update(kwargs)
    return fake.bind(BastionClient.from_params(params))


def test_defaults_match_terraform_provider():
    conn = resolve_connection(dict(bastion_host="h", bastion_user="u"))
    assert conn["bastion_port"] == 443
    assert conn["api_version"] == "v3.12"
    assert conn["validate_certs"] is True
    assert conn["csrf_enabled"] is True


def test_environment_fallback(monkeypatch):
    monkeypatch.setenv("WALLIX_BASTION_HOST", "env-host")
    monkeypatch.setenv("WALLIX_BASTION_USER", "env-user")
    monkeypatch.setenv("WALLIX_BASTION_TOKEN", "env-token")
    monkeypatch.setenv("WALLIX_BASTION_PORT", "8443")
    monkeypatch.setenv("WALLIX_INSECURE_SKIP_VERIFY", "true")
    conn = resolve_connection(dict(bastion_host=None, bastion_user=None))
    assert (conn["bastion_host"], conn["bastion_user"], conn["bastion_token"]) == ("env-host", "env-user", "env-token")
    assert conn["bastion_port"] == 8443
    assert conn["validate_certs"] is False


def test_explicit_option_beats_environment(monkeypatch):
    monkeypatch.setenv("WALLIX_BASTION_HOST", "env-host")
    monkeypatch.setenv("WALLIX_BASTION_VALIDATE_CERTS", "false")
    conn = resolve_connection(dict(bastion_host="param-host", validate_certs=True))
    assert conn["bastion_host"] == "param-host"
    assert conn["validate_certs"] is True


@pytest.mark.parametrize("params, error", [
    (dict(bastion_user="u", bastion_token="t"), "bastion_host"),
    (dict(bastion_host="h", bastion_token="t"), "bastion_user"),
    (dict(bastion_host="h", bastion_user="u"), "bastion_password or bastion_token"),
    (dict(bastion_host="h", bastion_user="u", bastion_token="t", bastion_port=70000), "bastion_port"),
    (dict(bastion_host="h", bastion_user="u", bastion_token="t", api_version="v2"), "api_version"),
])
def test_validate_connection(params, error):
    assert error in validate_connection(resolve_connection(params))


def test_ipv6_host_is_bracketed():
    assert BastionClient("2001:db8::1", "u", bastion_token="t").base_url == "https://[2001:db8::1]:443"


def test_token_login_then_versioned_calls():
    fake = FakeBastion()
    c = client(fake)
    assert c.get("devices") == []
    assert fake.calls[0][:2] == ("POST", "/api")
    assert fake.calls[1][:2] == ("GET", "/api/v3.12/devices")


def test_password_login():
    fake = FakeBastion()
    c = client(fake, bastion_token=None, bastion_password="secret")
    assert c.get("devices") == []


def test_bad_credentials_raise():
    with pytest.raises(BastionError, match="Authentication to WALLIX Bastion failed: HTTP 401"):
        client(FakeBastion(), bastion_token="wrong").get("devices")


def test_reauthenticates_once_on_401():
    fake = FakeBastion()
    c = client(fake)
    c.get("devices")
    fake.expire_session_once = True
    assert c.get("devices") == []
    assert fake.logins == 2


def test_sends_csrf_token_from_login():
    fake = FakeBastion(csrf_token="csrf-123")
    c = client(fake)
    c.call("POST", "devices", {"device_name": "d", "host": "h"})
    assert len(fake.objects("devices")) == 1


def test_csrf_disabled_does_not_send_token():
    fake = FakeBastion(csrf_token="csrf-123")
    c = client(fake, csrf_enabled=False)
    with pytest.raises(BastionError, match="HTTP 403"):
        c.call("POST", "devices", {"device_name": "d", "host": "h"})


def test_find_is_exact_match_despite_substring_search():
    fake = FakeBastion()
    fake.add("devices", {"device_name": "web-01"})
    fake.add("devices", {"device_name": "web-010"})
    found = client(fake).find("devices", "device_name", "web-01")
    assert found["device_name"] == "web-01"


def test_find_quotes_names():
    fake = FakeBastion()
    fake.add("devices", {"device_name": "a b&c"})
    assert client(fake).find("devices", "device_name", "a b&c")["device_name"] == "a b&c"


def test_get_returns_none_on_404():
    assert client(FakeBastion()).get("devices/missing") is None


def test_unexpected_status_raises():
    with pytest.raises(BastionError, match="DELETE devices/missing returned HTTP 404"):
        client(FakeBastion()).call("DELETE", "devices/missing")
