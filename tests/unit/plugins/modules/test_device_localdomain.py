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
from ansible_collections.wallix.bastion.plugins.modules import device_localdomain, device_localdomain_info
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


API_LD = {"domain_name": "local", "description": "d", "admin_account": None, "enable_password_change": False,
          "password_change_policy": None, "password_change_plugin": None,
          "password_change_plugin_parameters": None, "ca_private_key": "********", "ca_public_key": "ssh-ed25519 AAA"}


@pytest.fixture
def device_id(fake):
    return fake.add("devices", {"device_name": "srv", "host": "10.0.0.1"})["id"]


def domains(fake, device_id):
    return fake.objects("devices/%s/localdomains" % device_id)


def test_create_with_secrets(monkeypatch, fake, device_id):
    res = run(monkeypatch, device_localdomain, device_name="srv", domain_name="local", description="d",
              ca_private_key="generate:ED25519", passphrase="s3cret")
    assert not res.failed and res.result["changed"]
    method, path, body = fake.writes()[0]
    assert (method, path) == ("POST", "/api/v3.12/devices/%s/localdomains" % device_id)
    assert body == {"domain_name": "local", "description": "d", "ca_private_key": "generate:ED25519",
                    "passphrase": "s3cret"}
    assert "ca_private_key" not in res.result["localdomain"] and "passphrase" not in res.result["localdomain"]
    assert "passphrase" not in res.result["diff"]["after"]


def test_create_check_mode_writes_nothing(monkeypatch, fake, device_id):
    res = run(monkeypatch, device_localdomain, check_mode=True, device_name="srv", domain_name="local",
              ca_private_key="generate:ED25519")
    assert res.result["changed"] and fake.writes() == []
    assert "ca_private_key" not in res.result["localdomain"]


def test_create_with_admin_account_fails(monkeypatch, fake, device_id):
    res = run(monkeypatch, device_localdomain, check_mode=True, device_name="srv", domain_name="local",
              admin_account="root")
    assert res.failed and "admin_account cannot be set when creating" in res.result["msg"]
    assert fake.writes() == []


def test_missing_device(monkeypatch, fake):
    assert run(monkeypatch, device_localdomain, device_name="nope", domain_name="local").failed
    res = run(monkeypatch, device_localdomain, device_name="nope", domain_name="local", state="absent")
    assert not res.failed and not res.result["changed"]


def test_no_change_is_idempotent_and_secrets_on_create_only(monkeypatch, fake, device_id):
    fake.add("devices/%s/localdomains" % device_id, API_LD)
    res = run(monkeypatch, device_localdomain, device_name="srv", domain_name="local", description="d",
              ca_private_key="generate:ED25519", passphrase="s3cret")
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []


def test_update_password_always_sends_secrets(monkeypatch, fake, device_id):
    fake.add("devices/%s/localdomains" % device_id, API_LD)
    res = run(monkeypatch, device_localdomain, device_name="srv", domain_name="local", passphrase="new",
              ca_private_key="key", update_password="always")
    assert res.result["changed"] and res.result["changed_fields"] == ["ca_private_key", "passphrase"]
    method, path, body = fake.writes()[0]
    assert method == "PUT" and body["passphrase"] == "new" and body["ca_private_key"] == "key"


def test_update_keeps_unset_options(monkeypatch, fake, device_id):
    obj = fake.add("devices/%s/localdomains" % device_id, API_LD)
    res = run(monkeypatch, device_localdomain, device_name="srv", domain_name="local", enable_password_change=True,
              password_change_policy="default", password_change_plugin="Unix",
              password_change_plugin_parameters={})
    assert res.result["changed"]
    assert res.result["changed_fields"] == ["enable_password_change", "password_change_plugin", "password_change_policy"]
    method, path, body = fake.writes()[0]
    assert method == "PUT" and path.endswith("/localdomains/%s" % obj["id"])
    # Nulls, read-only and masked fields are not sent back; secrets only with update_password=always.
    assert body == {"domain_name": "local", "description": "d", "enable_password_change": True,
                    "password_change_policy": "default", "password_change_plugin": "Unix"}


def test_update_check_mode(monkeypatch, fake, device_id):
    fake.add("devices/%s/localdomains" % device_id, API_LD)
    res = run(monkeypatch, device_localdomain, check_mode=True, device_name="srv", domain_name="local",
              description="new")
    assert res.result["changed"] and res.result["diff"]["after"]["description"] == "new"
    assert "ca_private_key" not in res.result["diff"]["before"]
    assert fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake, device_id):
    fake.add("devices/%s/localdomains" % device_id, API_LD)
    assert run(monkeypatch, device_localdomain, device_name="srv", domain_name="local", state="absent").result["changed"]
    assert domains(fake, device_id) == []
    assert not run(monkeypatch, device_localdomain, device_name="srv", domain_name="local",
                   state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake, device_id):
    fake.add("devices/%s/localdomains" % device_id, API_LD)
    res = run(monkeypatch, device_localdomain, check_mode=True, device_name="srv", domain_name="local", state="absent")
    assert res.result["changed"] and len(domains(fake, device_id)) == 1


def test_passphrase_requires_private_key(monkeypatch, fake, device_id):
    res = run(monkeypatch, device_localdomain, device_name="srv", domain_name="local", passphrase="x")
    assert res.failed and fake.writes() == []


def test_info(monkeypatch, fake, device_id):
    fake.add("devices/%s/localdomains" % device_id, API_LD)
    fake.add("devices/%s/localdomains" % device_id, dict(API_LD, domain_name="local2"))
    one = run(monkeypatch, device_localdomain_info, device_name="srv", domain_name="local").result
    assert [d["domain_name"] for d in one["localdomains"]] == ["local"] and not one["changed"]
    assert len(run(monkeypatch, device_localdomain_info, device_name="srv").result["localdomains"]) == 2
    assert run(monkeypatch, device_localdomain_info, device_name="srv", domain_name="x").result["localdomains"] == []
    assert run(monkeypatch, device_localdomain_info, device_name="nope").failed
