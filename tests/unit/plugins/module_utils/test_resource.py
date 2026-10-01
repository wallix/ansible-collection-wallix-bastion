# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""Generic BastionResource behaviour not covered by the device tests."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionClient
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionResource, find_parent
from ansible_collections.wallix.bastion.tests.unit.plugins.module_utils.fake_bastion import FakeBastion


class Exit(Exception):
    def __init__(self, result, failed):
        super(Exit, self).__init__(result)
        self.result = result
        self.failed = failed


class FakeModule:
    def __init__(self, fake, check_mode=False, **params):
        self.params = params
        self.check_mode = check_mode
        self.client = fake.bind(BastionClient("bastion.test", "admin", bastion_token="token"))

    def exit_json(self, **kwargs):
        raise Exit(kwargs, False)

    def fail_json(self, **kwargs):
        raise Exit(kwargs, True)


def ensure(resource, state="present"):
    with pytest.raises(Exit) as exc:
        resource.ensure(state)
    return exc.value


def user_resource(module, update_secrets=False):
    return BastionResource(module, "users", "user_name", ("user_name", "email", "password", "profile"),
                           result_key="user", secret_fields=("password",),
                           create_only_fields=("profile",), update_secrets=update_secrets)


@pytest.fixture
def fake():
    return FakeBastion()


def test_secret_sent_on_create_but_never_returned(fake):
    module = FakeModule(fake, user_name="jdoe", email="j@x", password="s3cret", profile="user")
    res = ensure(user_resource(module))
    assert res.result["changed"]
    assert fake.objects("users")[0]["password"] == "s3cret"
    assert "password" not in res.result["user"]
    assert "password" not in res.result["diff"]["after"]


def test_secret_ignored_on_update_by_default(fake):
    fake.add("users", {"user_name": "jdoe", "email": "j@x", "profile": "user"})
    res = ensure(user_resource(FakeModule(fake, user_name="jdoe", email="j@x", password="new")))
    assert not res.result["changed"]
    assert fake.writes() == []


def test_secret_always_updated_when_requested(fake):
    fake.add("users", {"user_name": "jdoe", "email": "j@x", "profile": "user"})
    res = ensure(user_resource(FakeModule(fake, user_name="jdoe", password="new"), update_secrets=True))
    assert res.result["changed"] and res.result["changed_fields"] == ["password"]
    assert fake.writes()[0][2]["password"] == "new"
    assert "password" not in res.result["user"]


def test_create_only_field_change_fails_without_writing(fake):
    fake.add("users", {"user_name": "jdoe", "profile": "user"})
    res = ensure(user_resource(FakeModule(fake, user_name="jdoe", profile="admin")))
    assert res.failed and "profile cannot be changed after creation" in res.result["msg"]
    assert fake.writes() == []


def test_child_resource_under_parent(fake):
    device = fake.add("devices", {"device_name": "srv"})
    module = FakeModule(fake, device_name="srv", service_name="SSH", port=22, state="present")
    parent_id = find_parent(module, "devices", "device_name", "srv", "device")
    assert parent_id == device["id"]
    child = "devices/%s/services" % parent_id
    res = ensure(BastionResource(module, child, "service_name", ("service_name", "port"), result_key="service"))
    assert res.result["changed"] and res.result["service"]["port"] == 22
    assert [o["service_name"] for o in fake.objects(child)] == ["SSH"]
    assert fake.writes()[0][:2] == ("POST", "/api/v3.12/" + child)


def test_missing_parent_fails_on_present(fake):
    module = FakeModule(fake, device_name="nope", state="present")
    with pytest.raises(Exit) as exc:
        find_parent(module, "devices", "device_name", "nope", "device")
    assert exc.value.failed and exc.value.result["msg"] == "device nope does not exist"


def test_missing_parent_is_fine_on_absent(fake):
    module = FakeModule(fake, device_name="nope", state="absent")
    assert find_parent(module, "devices", "device_name", "nope", "device") is None
