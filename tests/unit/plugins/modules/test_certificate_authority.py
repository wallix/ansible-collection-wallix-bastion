# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

import pytest
import json

import pytest

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

try:
    from ansible.module_utils.testing import patch_module_args  # ansible-core >= 2.19
except ImportError:
    patch_module_args = None

from ansible_collections.wallix.bastion.plugins.module_utils import client as client_utils
from ansible_collections.wallix.bastion.plugins.modules import certificate_authority, certificate_authority_info
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


PEM = "-----BEGIN CERTIFICATE-----\nMIIBszCCAVmgAwIBAgIUQ\n-----END CERTIFICATE-----\n"
PEM2 = "-----BEGIN CERTIFICATE-----\nMIIBszCCAVmgAwIBAgIUZ\n-----END CERTIFICATE-----\n"
SSH = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIC8AUFSJcx test-ca\n"
EXISTING = {"certificate_authority_name": "ca", "ca_type": "X509", "ca_certificate": PEM, "description": "keep me"}


def test_create(monkeypatch, fake):
    res = run(monkeypatch, certificate_authority, certificate_authority_name="ca", ca_type="X509", ca_certificate=PEM)
    assert not res.failed and res.result["changed"]
    assert res.result["certificate_authority"]["ca_certificate"] == PEM
    assert fake.objects("certificate_authorities")[0]["ca_type"] == "X509"


def test_create_without_object_id_header(monkeypatch, fake):
    fake.return_object_id = False
    res = run(monkeypatch, certificate_authority, certificate_authority_name="ca", ca_type="SSH", ca_certificate=SSH)
    assert res.result["changed"] and res.result["certificate_authority"]["id"]


def test_create_requires_type_and_certificate(monkeypatch, fake):
    res = run(monkeypatch, certificate_authority, certificate_authority_name="ca", ca_type="X509")
    assert res.failed and "ca_certificate required" in res.result["msg"]
    res = run(monkeypatch, certificate_authority, certificate_authority_name="ca", ca_certificate=PEM)
    assert res.failed and "ca_type required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, certificate_authority, check_mode=True, certificate_authority_name="ca",
              ca_type="X509", ca_certificate=PEM)
    assert res.result["changed"] and res.result["diff"]["after"]["ca_type"] == "X509"
    assert fake.writes() == []


def test_no_change_ignores_blanks_and_line_endings(monkeypatch, fake):
    fake.add("certificate_authorities", EXISTING)
    res = run(monkeypatch, certificate_authority, certificate_authority_name="ca", ca_type="X509",
              ca_certificate="  " + PEM.strip().replace("\n", "\r\n"), description="keep me")
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []


def test_update_certificate_keeps_unset(monkeypatch, fake):
    fake.add("certificate_authorities", EXISTING)
    res = run(monkeypatch, certificate_authority, certificate_authority_name="ca", ca_certificate=PEM2)
    assert res.result["changed"] and res.result["changed_fields"] == ["ca_certificate"]
    method, path, body = fake.writes()[0]
    assert method == "PUT"
    assert body == dict(EXISTING, ca_certificate=PEM2)


def test_update_type_and_certificate(monkeypatch, fake):
    fake.add("certificate_authorities", EXISTING)
    res = run(monkeypatch, certificate_authority, certificate_authority_name="ca", ca_type="SSH", ca_certificate=SSH)
    assert res.result["changed_fields"] == ["ca_certificate", "ca_type"]
    assert fake.objects("certificate_authorities")[0]["ca_type"] == "SSH"


def test_update_check_mode(monkeypatch, fake):
    fake.add("certificate_authorities", EXISTING)
    res = run(monkeypatch, certificate_authority, check_mode=True, certificate_authority_name="ca", description="new")
    assert res.result["changed"] and res.result["diff"]["after"]["description"] == "new"
    assert fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake):
    fake.add("certificate_authorities", EXISTING)
    assert run(monkeypatch, certificate_authority, certificate_authority_name="ca", state="absent").result["changed"]
    assert fake.objects("certificate_authorities") == []
    assert not run(monkeypatch, certificate_authority, certificate_authority_name="ca", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake):
    fake.add("certificate_authorities", EXISTING)
    res = run(monkeypatch, certificate_authority, check_mode=True, certificate_authority_name="ca", state="absent")
    assert res.result["changed"] and len(fake.objects("certificate_authorities")) == 1


def test_info_by_name_and_all(monkeypatch, fake):
    fake.add("certificate_authorities", EXISTING)
    fake.add("certificate_authorities", dict(EXISTING, certificate_authority_name="ca2"))
    one = run(monkeypatch, certificate_authority_info, certificate_authority_name="ca").result
    assert [c["certificate_authority_name"] for c in one["certificate_authorities"]] == ["ca"]
    assert len(run(monkeypatch, certificate_authority_info).result["certificate_authorities"]) == 2
    assert run(monkeypatch, certificate_authority_info, certificate_authority_name="x").result["certificate_authorities"] == []
