# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible.errors import AnsibleError
from ansible.plugins.loader import lookup_loader
from ansible.utils.unsafe_proxy import AnsibleUnsafe

try:
    from ansible.template import is_trusted_as_template  # ansible-core >= 2.19
except ImportError:
    is_trusted_as_template = None

from ansible_collections.wallix.bastion.plugins.module_utils import client as client_utils
from ansible_collections.wallix.bastion.tests.unit.plugins.modules.test_secret import (
    CHECKOUT,
    PASSWORD,
    TARGET,
    FakeSecrets,
)


def is_unsafe(value):
    """True when templating will never evaluate value, whatever the ansible-core version."""
    if is_trusted_as_template is not None:
        return not is_trusted_as_template(value)
    return isinstance(value, AnsibleUnsafe)


@pytest.fixture
def fake(monkeypatch):
    fake = FakeSecrets()

    def _open(self, method, url, data=None, headers=None, **kwargs):
        return fake.handle(self, method, url, data, headers, **kwargs)

    monkeypatch.setattr(client_utils.BastionClient, "_open", _open)
    for env in ("WALLIX_BASTION_HOST", "WALLIX_BASTION_USER", "WALLIX_BASTION_PASSWORD", "WALLIX_BASTION_TOKEN",
                "WALLIX_BASTION_PORT", "WALLIX_BASTION_API_VERSION"):
        monkeypatch.delenv(env, raising=False)
    return fake


def lookup(terms, variables=None, **kwargs):
    return lookup_loader.get("wallix.bastion.secret").run(terms, variables=variables or {}, **kwargs)


@pytest.fixture
def lookup_env(fake, monkeypatch):
    monkeypatch.setenv("WALLIX_BASTION_HOST", "bastion.test")
    monkeypatch.setenv("WALLIX_BASTION_USER", "admin")
    monkeypatch.setenv("WALLIX_BASTION_TOKEN", "token")
    return fake


def test_lookup_password_from_env(lookup_env):
    result = lookup([TARGET])
    assert result == [PASSWORD]
    assert is_unsafe(result[0])
    assert lookup_env.api_calls()[0]["path"] == "/api/v3.12/targetpasswords/checkout/root@local@srv"
    assert TARGET in lookup_env.checked_out


def test_lookup_connection_from_vars(fake):
    variables = dict(wallix_bastion_host="bastion.test", wallix_bastion_user="admin", wallix_bastion_password="secret",
                     wallix_bastion_api_version="v3.12")
    assert lookup([TARGET], variables=variables) == [PASSWORD]
    login = [c for c in fake.calls if c["path"] == "/api"][0]
    assert "X-Auth-Key" not in login["headers"]


def test_lookup_direct_options_win_over_vars(fake):
    variables = dict(wallix_bastion_host="bastion.test", wallix_bastion_user="admin", wallix_bastion_token="wrong")
    assert lookup([TARGET], variables=variables, bastion_token="token") == [PASSWORD]


def test_lookup_options(lookup_env):
    result = lookup([TARGET], field="ssh_key", authorization="auth-1", duration=30, key_format="pkcs1",
                    cert_format="ssh.com", key_passphrase="pp")
    assert result[0].startswith("-----BEGIN")
    call = lookup_env.api_calls()[0]
    assert call["query"] == {"authorization": ["auth-1"], "duration": ["30"], "key_format": ["pkcs1"],
                             "cert_format": ["ssh.com"]}
    assert call["headers"]["X-Key-Passphrase"] == "pp"


def test_lookup_all_and_checkin(lookup_env):
    result = lookup([TARGET], field="all", checkin=True, authorization="auth-1")
    assert result[0]["login"] == "root" and result[0]["password"] == PASSWORD
    assert is_unsafe(result[0]["password"])
    paths = [c["path"].rsplit("/", 2)[1] for c in lookup_env.api_calls()]
    assert paths == ["checkout", "checkin"]
    assert lookup_env.api_calls()[1]["query"] == {"authorization": ["auth-1"]}
    assert lookup_env.checked_out == set()


def test_lookup_several_terms(lookup_env):
    lookup_env.accounts["svc@corp"] = dict(CHECKOUT, password="other")
    assert lookup([TARGET, "svc@corp"]) == [PASSWORD, "other"]


def test_lookup_missing_field(lookup_env):
    lookup_env.accounts[TARGET]["password"] = ""
    with pytest.raises(AnsibleError, match="has no password .available: ssh_key"):
        lookup([TARGET])


def test_lookup_unknown_account(lookup_env):
    with pytest.raises(AnsibleError) as exc:
        lookup(["nobody@local@srv"])
    assert "NOT_AUTHORIZED" in str(exc.value) and PASSWORD not in str(exc.value)


def test_lookup_missing_connection(fake):
    with pytest.raises(AnsibleError, match="bastion_host is required"):
        lookup([TARGET])
