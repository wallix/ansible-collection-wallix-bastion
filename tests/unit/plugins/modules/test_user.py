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
from ansible_collections.wallix.bastion.plugins.modules import user, user_info
from ansible_collections.wallix.bastion.tests.unit.plugins.module_utils.fake_bastion import FakeBastion

CONN = dict(bastion_host="bastion.test", bastion_user="admin", bastion_token="token")


class ModuleExit(Exception):
    def __init__(self, result, failed=False):
        super(ModuleExit, self).__init__(result)
        self.result = result
        self.failed = failed


class UserFakeBastion(FakeBastion):
    """Users have no id on the real API: they are addressed by user_name, case-insensitively."""

    def add(self, collection, obj):
        if collection == "users":
            obj = dict(obj, id=obj["user_name"].lower())
        return super(UserFakeBastion, self).add(collection, obj)

    def handle(self, client, method, url, data, headers, auth):
        base, sep, rest = url.partition("/users/")
        if sep:
            url = base + sep + rest.lower()
        return super(UserFakeBastion, self).handle(client, method, url, data, headers, auth)


@pytest.fixture
def fake(monkeypatch):
    fake = UserFakeBastion()
    fake.return_object_id = False
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


BASE = dict(user_name="jdoe", email="j@example.com", profile="user", user_auths=["local_password"])


def existing(fake, **fields):
    obj = dict(BASE, display_name="", groups=[], password="********", ssh_public_key="", is_disabled=False)
    obj.update(fields)
    return fake.add("users", obj)


def test_create(monkeypatch, fake):
    res = run(monkeypatch, user, password="S3cret!", ssh_public_key="ssh-ed25519 AAAA k1", **BASE)
    assert not res.failed and res.result["changed"]
    method, path, body = fake.writes()[0]
    assert (method, path) == ("POST", "/api/v3.12/users")
    assert body["password"] == "S3cret!"
    assert "password" not in res.result["user"]
    assert "password" not in res.result["diff"]["after"]
    assert res.result["user"]["ssh_public_key"] == "ssh-ed25519 AAAA k1"


def test_create_requires_email_profile_user_auths(monkeypatch, fake):
    res = run(monkeypatch, user, user_name="jdoe", password="x")
    assert res.failed and "email, profile, user_auths required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, user, check_mode=True, password="S3cret!", **BASE)
    assert res.result["changed"] and "password" not in res.result["user"]
    assert fake.writes() == []


def test_no_change_is_idempotent(monkeypatch, fake):
    existing(fake, user_auths=["local_sshkey", "local_password"], groups=["b", "a"])
    args = dict(BASE, password="S3cret!", groups=["a", "b"])
    args["user_auths"] = ["local_password", "local_sshkey"]
    res = run(monkeypatch, user, **args)
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []


def test_user_name_case_is_not_a_change(monkeypatch, fake):
    existing(fake)
    args = dict(BASE)
    args["user_name"] = "JDoe"
    res = run(monkeypatch, user, **args)
    assert not res.result["changed"] and res.result["user"]["user_name"] == "jdoe"
    res = run(monkeypatch, user, user_name="JDoe", display_name="John")
    assert res.result["changed_fields"] == ["display_name"]
    assert fake.writes()[0][2]["user_name"] == "jdoe"


def test_update_keeps_unset_options_and_forces_lists(monkeypatch, fake):
    existing(fake, display_name="keep me", groups=["g1"])
    res = run(monkeypatch, user, user_name="jdoe", is_disabled=True, password="ignored")
    assert res.result["changed"] and res.result["changed_fields"] == ["is_disabled"]
    method, path, body = fake.writes()[0]
    assert (method, path) == ("PUT", "/api/v3.12/users/jdoe")
    assert body["display_name"] == "keep me" and body["groups"] == ["g1"] and body["is_disabled"] is True
    assert "password" not in body  # update_password=on_create


def test_update_sends_force_true(monkeypatch, fake):
    seen = []
    original = fake.handle

    def handle(client, method, url, data, headers, auth):
        seen.append((method, url))
        return original(client, method, url, data, headers, auth)

    fake.handle = handle
    existing(fake, groups=["g1"])
    res = run(monkeypatch, user, user_name="jdoe", groups=[])
    assert res.result["changed"] and res.result["user"]["groups"] == []
    assert [u for m, u in seen if m == "PUT"] == ["https://bastion.test:443/api/v3.12/users/jdoe?force=true"]


def test_update_password_always(monkeypatch, fake):
    existing(fake)
    res = run(monkeypatch, user, user_name="jdoe", password="N3w!", update_password="always")
    assert res.result["changed"] and res.result["changed_fields"] == ["password"]
    assert fake.writes()[0][2]["password"] == "N3w!"
    assert "N3w!" not in json.dumps(res.result)


def test_update_password_on_create_with_other_change(monkeypatch, fake):
    existing(fake)
    res = run(monkeypatch, user, user_name="jdoe", password="N3w!", display_name="John")
    assert res.result["changed_fields"] == ["display_name"]
    assert "password" not in fake.writes()[0][2]


def test_update_check_mode(monkeypatch, fake):
    existing(fake, display_name="old")
    res = run(monkeypatch, user, check_mode=True, user_name="jdoe", display_name="new")
    assert res.result["changed"]
    assert res.result["diff"]["before"]["display_name"] == "old"
    assert res.result["diff"]["after"]["display_name"] == "new"
    assert "password" not in res.result["diff"]["before"]
    assert fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake):
    existing(fake)
    res = run(monkeypatch, user, user_name="jdoe", state="absent")
    assert res.result["changed"] and fake.writes()[0][:2] == ("DELETE", "/api/v3.12/users/jdoe")
    assert fake.objects("users") == []
    assert not run(monkeypatch, user, user_name="jdoe", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    existing(fake)
    assert run(monkeypatch, user, check_mode=True, user_name="jdoe", state="absent").result["changed"]
    assert len(fake.objects("users")) == 1


def test_api_error_fails_with_status(monkeypatch, fake):
    res = run(monkeypatch, user, bastion_token="wrong", **BASE)
    assert res.failed and res.result["status"] == 401


def test_info_by_name_and_all(monkeypatch, fake):
    existing(fake)
    existing(fake, user_name="jdoe2")
    one = run(monkeypatch, user_info, user_name="jdoe").result
    assert [u["user_name"] for u in one["users"]] == ["jdoe"] and not one["changed"]
    assert "password" not in one["users"][0]
    assert len(run(monkeypatch, user_info).result["users"]) == 2
    assert run(monkeypatch, user_info, user_name="nope").result["users"] == []
