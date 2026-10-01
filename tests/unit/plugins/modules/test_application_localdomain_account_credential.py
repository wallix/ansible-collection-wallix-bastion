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
from ansible_collections.wallix.bastion.plugins.modules import application_localdomain_account_credential, application_localdomain_account_credential_info
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


CRED = dict(application_name="web", domain_name="local", account_name="admin", type="password")
API_PW = {"type": "password", "password": "********"}


@pytest.fixture
def path(fake):
    app_id = fake.add("applications", {"application_name": "web", "category": "web_application"})["id"]
    domain_id = fake.add("applications/%s/localdomains" % app_id, {"domain_name": "local"})["id"]
    account_id = fake.add("applications/%s/localdomains/%s/accounts" % (app_id, domain_id),
                          {"account_name": "admin", "account_login": "admin"})["id"]
    return "applications/%s/localdomains/%s/accounts/%s/credentials" % (app_id, domain_id, account_id)


def test_create_password(monkeypatch, fake, path):
    res = run(monkeypatch, application_localdomain_account_credential, password="s3cret", **CRED)
    assert not res.failed and res.result["changed"]
    method, url, body = fake.writes()[0]
    assert (method, url, body) == ("POST", "/api/v3.12/" + path, {"type": "password", "password": "s3cret"})
    assert "password" not in res.result["credential"] and res.result["credential"]["type"] == "password"
    assert "password" not in res.result["diff"]["after"]


def test_create_requires_password(monkeypatch, fake, path):
    res = run(monkeypatch, application_localdomain_account_credential, **CRED)
    assert res.failed and "password required" in res.result["msg"]
    assert fake.writes() == []


def test_only_password_type(monkeypatch, fake, path):
    params = dict(CRED)
    params["type"] = "ssh_key"
    res = run(monkeypatch, application_localdomain_account_credential, **params)
    assert res.failed and fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake, path):
    res = run(monkeypatch, application_localdomain_account_credential, check_mode=True, password="x", **CRED)
    assert res.result["changed"] and fake.writes() == []
    assert "password" not in res.result["credential"]


def test_existing_secret_not_resent(monkeypatch, fake, path):
    fake.add(path, API_PW)
    res = run(monkeypatch, application_localdomain_account_credential, password="other", **CRED)
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []


def test_update_password_always(monkeypatch, fake, path):
    obj = fake.add(path, API_PW)
    res = run(monkeypatch, application_localdomain_account_credential, password="new", update_password="always",
              **CRED)
    assert res.result["changed"] and res.result["changed_fields"] == ["password"]
    method, url, body = fake.writes()[0]
    assert method == "PUT" and url.endswith("/credentials/%s" % obj["id"])
    # The PUT requires the type next to the password.
    assert body == {"type": "password", "password": "new"}
    assert "password" not in res.result["credential"]


def test_update_password_always_check_mode(monkeypatch, fake, path):
    fake.add(path, API_PW)
    res = run(monkeypatch, application_localdomain_account_credential, check_mode=True, password="new",
              update_password="always", **CRED)
    assert res.result["changed"] and fake.writes() == []
    assert "password" not in res.result["credential"]


def test_missing_parents(monkeypatch, fake, path):
    for missing, label in ((dict(account_name="nope"), "account"), (dict(domain_name="nope"), "localdomain"),
                           (dict(application_name="nope"), "application")):
        params = dict(CRED, **missing)
        res = run(monkeypatch, application_localdomain_account_credential, password="x", **params)
        assert res.failed and res.result["msg"] == "%s nope does not exist" % label
        res = run(monkeypatch, application_localdomain_account_credential, state="absent", **params)
        assert not res.failed and not res.result["changed"]


def test_delete_and_delete_again(monkeypatch, fake, path):
    fake.add(path, API_PW)
    assert run(monkeypatch, application_localdomain_account_credential, state="absent", **CRED).result["changed"]
    assert fake.objects(path) == []
    assert not run(monkeypatch, application_localdomain_account_credential, state="absent",
                   **CRED).result["changed"]


def test_delete_check_mode(monkeypatch, fake, path):
    fake.add(path, API_PW)
    assert run(monkeypatch, application_localdomain_account_credential, check_mode=True, state="absent",
               **CRED).result["changed"]
    assert len(fake.objects(path)) == 1


def test_info(monkeypatch, fake, path):
    info = dict(CRED)
    del info["type"]
    assert run(monkeypatch, application_localdomain_account_credential_info, **info).result["credentials"] == []
    fake.add(path, API_PW)
    res = run(monkeypatch, application_localdomain_account_credential_info, **CRED).result
    assert not res["changed"] and len(res["credentials"]) == 1 and "password" not in res["credentials"][0]
    assert len(run(monkeypatch, application_localdomain_account_credential_info, **info).result["credentials"]) == 1
    info["account_name"] = "x"
    assert run(monkeypatch, application_localdomain_account_credential_info, **info).failed
