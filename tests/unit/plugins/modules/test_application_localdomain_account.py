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
from ansible_collections.wallix.bastion.plugins.modules import application_localdomain_account, application_localdomain_account_info
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


API_ACC = {"account_name": "admin", "account_login": "admin", "description": "", "auto_change_password": True,
           "checkout_policy": "default", "certificate_validity": None, "can_edit_certificate_validity": False,
           "domain_password_change": False, "onboard_status": "manual", "first_seen": None, "last_seen": None,
           "credentials": [{"id": "c1", "type": "password", "password": "********"}]}
ACC = dict(application_name="web", domain_name="local", account_name="admin")


@pytest.fixture
def path(fake):
    app_id = fake.add("applications", {"application_name": "web", "category": "web_application"})["id"]
    domain_id = fake.add("applications/%s/localdomains" % app_id, {"domain_name": "local"})["id"]
    return "applications/%s/localdomains/%s/accounts" % (app_id, domain_id)


def test_create_defaults_checkout_policy(monkeypatch, fake, path):
    res = run(monkeypatch, application_localdomain_account, account_login="admin", **ACC)
    assert not res.failed and res.result["changed"]
    method, url, body = fake.writes()[0]
    assert (method, url) == ("POST", "/api/v3.12/" + path)
    assert body == {"account_name": "admin", "account_login": "admin", "checkout_policy": "default"}


def test_create_keeps_given_checkout_policy(monkeypatch, fake, path):
    run(monkeypatch, application_localdomain_account, account_login="admin", checkout_policy="strict", **ACC)
    assert fake.writes()[0][2]["checkout_policy"] == "strict"


def test_create_requires_login(monkeypatch, fake, path):
    res = run(monkeypatch, application_localdomain_account, **ACC)
    assert res.failed and "account_login required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake, path):
    res = run(monkeypatch, application_localdomain_account, check_mode=True, account_login="admin", **ACC)
    assert res.result["changed"] and fake.writes() == []


def test_missing_parents(monkeypatch, fake, path):
    for missing, label in ((dict(domain_name="nope"), "localdomain"), (dict(application_name="nope"), "application")):
        params = dict(ACC, account_login="admin", **missing)
        res = run(monkeypatch, application_localdomain_account, **params)
        assert res.failed and res.result["msg"] == "%s nope does not exist" % label
        res = run(monkeypatch, application_localdomain_account, state="absent", **dict(ACC, **missing))
        assert not res.failed and not res.result["changed"]


def test_no_change_is_idempotent(monkeypatch, fake, path):
    fake.add(path, API_ACC)
    res = run(monkeypatch, application_localdomain_account, account_login="admin", checkout_policy="default", **ACC)
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []


def test_update_keeps_unset_options_and_drops_nulls(monkeypatch, fake, path):
    obj = fake.add(path, API_ACC)
    res = run(monkeypatch, application_localdomain_account, auto_change_password=False, **ACC)
    assert res.result["changed"] and res.result["changed_fields"] == ["auto_change_password"]
    method, url, body = fake.writes()[0]
    assert method == "PUT" and url.endswith("/accounts/%s" % obj["id"])
    # Credentials and read-only fields are not sent back, so the PUT keeps the password.
    assert body == {"account_name": "admin", "account_login": "admin", "description": "",
                    "auto_change_password": False, "checkout_policy": "default"}


def test_result_hides_credential_secrets(monkeypatch, fake, path):
    fake.add(path, API_ACC)
    res = run(monkeypatch, application_localdomain_account, **ACC)
    assert res.result["account"]["credentials"] == [{"id": "c1", "type": "password"}]
    info = run(monkeypatch, application_localdomain_account_info, application_name="web", domain_name="local").result
    assert info["accounts"][0]["credentials"] == [{"id": "c1", "type": "password"}]


def test_update_check_mode(monkeypatch, fake, path):
    fake.add(path, API_ACC)
    res = run(monkeypatch, application_localdomain_account, check_mode=True, description="new", **ACC)
    assert res.result["changed"] and res.result["diff"]["after"]["description"] == "new"
    assert fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake, path):
    fake.add(path, API_ACC)
    assert run(monkeypatch, application_localdomain_account, state="absent", **ACC).result["changed"]
    assert fake.objects(path) == []
    assert not run(monkeypatch, application_localdomain_account, state="absent", **ACC).result["changed"]


def test_delete_check_mode(monkeypatch, fake, path):
    fake.add(path, API_ACC)
    assert run(monkeypatch, application_localdomain_account, check_mode=True, state="absent", **ACC).result["changed"]
    assert len(fake.objects(path)) == 1


def test_info(monkeypatch, fake, path):
    fake.add(path, API_ACC)
    fake.add(path, dict(API_ACC, account_name="admin2"))
    one = run(monkeypatch, application_localdomain_account_info, **ACC).result
    assert [a["account_name"] for a in one["accounts"]] == ["admin"] and not one["changed"]
    assert len(run(monkeypatch, application_localdomain_account_info, application_name="web",
                   domain_name="local").result["accounts"]) == 2
    for field in ("account_name", "domain_name", "application_name"):
        unknown = dict(ACC)
        unknown[field] = "x"
        res = run(monkeypatch, application_localdomain_account_info, **unknown)
        assert res.result["accounts"] == [] if field == "account_name" else res.failed
