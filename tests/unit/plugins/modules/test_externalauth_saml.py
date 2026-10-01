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
from ansible_collections.wallix.bastion.plugins.modules import externalauth_saml as saml, externalauth_saml_info as saml_info
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


PATH = "/api/v3.12/externalauths"
METADATA = "<md:EntityDescriptor entityID='https://idp.example.com'/>"
EXISTING = dict(authentication_name="idp", type="SAML", description="", timeout=10.0, certificate="",
                private_key="", idp_metadata=METADATA, idp_entity_id="https://idp.example.com",
                claim_customization={"username": "uid", "email": "mail"}, sp_entity_id="https://bastion/api/saml/metadata")


def test_create(monkeypatch, fake):
    res = run(monkeypatch, saml, authentication_name="idp", idp_metadata=METADATA, timeout=10,
              claim_customization={"username": "uid", "email": "mail"})
    assert not res.failed and res.result["changed"]
    assert fake.writes()[0] == ("POST", PATH, dict(authentication_name="idp", idp_metadata=METADATA, timeout=10.0,
                                                   claim_customization={"username": "uid", "email": "mail"}, type="SAML"))


def test_create_requires_fields(monkeypatch, fake):
    res = run(monkeypatch, saml, authentication_name="idp", idp_metadata=METADATA)
    assert res.failed and "timeout, claim_customization required" in res.result["msg"]
    assert fake.writes() == []


def test_timeout_range(monkeypatch, fake):
    res = run(monkeypatch, saml, authentication_name="idp", timeout=901)
    assert res.failed and "between 1 and 900" in res.result["msg"]


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    res = run(monkeypatch, saml, check_mode=True, authentication_name="idp", idp_metadata=METADATA, timeout=10,
              claim_customization={"username": "uid"}, certificate="PEM", private_key="KEY")
    assert res.result["changed"] and "private_key" not in res.result["externalauth"]
    assert fake.writes() == []


def test_no_change_is_idempotent(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    res = run(monkeypatch, saml, authentication_name="idp", idp_metadata=METADATA, timeout=10,
              claim_customization={"email": "mail", "username": "uid"})
    assert not res.result["changed"] and fake.writes() == []


def test_claim_customization_is_replaced(monkeypatch, fake):
    obj = fake.add("externalauths", EXISTING)
    res = run(monkeypatch, saml, authentication_name="idp", claim_customization={"username": "uid"})
    assert res.result["changed_fields"] == ["claim_customization"]
    assert fake.writes() == [("PUT", PATH + "/" + obj["id"],
                              {"authentication_name": "idp", "claim_customization": {"username": "uid"}})]


def test_signing_key_set_once(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    res = run(monkeypatch, saml, authentication_name="idp", certificate="PEM", private_key="KEY", passphrase="phrase")
    assert res.result["changed_fields"] == ["certificate", "passphrase", "private_key"]
    assert "private_key" not in res.result["externalauth"]
    fake.objects("externalauths")[0].update(certificate="/CN=sp", private_key="********")
    res = run(monkeypatch, saml, authentication_name="idp", certificate="PEM", private_key="KEY", passphrase="phrase")
    assert not res.result["changed"] and len(fake.writes()) == 1


def test_delete_and_delete_again(monkeypatch, fake):
    fake.add("externalauths", EXISTING)
    assert run(monkeypatch, saml, authentication_name="idp", state="absent").result["changed"]
    assert not run(monkeypatch, saml, authentication_name="idp", state="absent").result["changed"]
    assert fake.objects("externalauths") == []


def test_info(monkeypatch, fake):
    fake.add("externalauths", dict(EXISTING, private_key="********"))
    fake.add("externalauths", dict(authentication_name="rad", type="RADIUS"))
    res = run(monkeypatch, saml_info, authentication_name="idp").result["externalauths"]
    assert len(res) == 1 and "private_key" not in res[0] and res[0]["sp_entity_id"]
