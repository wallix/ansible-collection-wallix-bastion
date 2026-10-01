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
from ansible_collections.wallix.bastion.plugins.modules import authdomain_mapping, authdomain_mapping_info
from ansible_collections.wallix.bastion.tests.unit.plugins.module_utils.fake_bastion import FakeBastion

CONN = dict(bastion_host="bastion.test", bastion_user="admin", bastion_token="token")
MAPPING = dict(domain_name="corp", user_group="admins", external_group="CN=Admins,DC=example,DC=com")


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


def add_domain(fake):
    domain = fake.add("authdomains", {"domain_name": "corp", "type": "AD"})
    return "authdomains/%s/mappings" % domain["id"]


def add_mapping(fake, path, user_group="admins", external_group="CN=Admins,DC=example,DC=com"):
    return fake.add(path, {"domain": "corp", "user_group": user_group, "external_group": external_group})


def test_create(monkeypatch, fake):
    path = add_domain(fake)
    res = run(monkeypatch, authdomain_mapping, **MAPPING)
    assert not res.failed and res.result["changed"]
    method, url, body = fake.writes()[0]
    assert method == "POST" and url.endswith(path)
    assert body == {"user_group": "admins", "external_group": "CN=Admins,DC=example,DC=com"}
    assert res.result["mapping"]["id"]


def test_create_check_mode_writes_nothing(monkeypatch, fake):
    add_domain(fake)
    res = run(monkeypatch, authdomain_mapping, check_mode=True, **MAPPING)
    assert res.result["changed"] and fake.writes() == []


def test_existing_pair_is_idempotent_ignoring_case(monkeypatch, fake):
    path = add_domain(fake)
    add_mapping(fake, path, external_group="cn=admins,dc=example,dc=com")
    res = run(monkeypatch, authdomain_mapping, **MAPPING)
    assert not res.result["changed"] and res.result["changed_fields"] == [] and fake.writes() == []


def test_other_external_group_of_same_user_group_is_a_new_mapping(monkeypatch, fake):
    path = add_domain(fake)
    add_mapping(fake, path, external_group="CN=Others,DC=example,DC=com")
    add_mapping(fake, path, user_group="admins-eu")
    res = run(monkeypatch, authdomain_mapping, **MAPPING)
    assert res.result["changed"] and fake.writes()[0][0] == "POST"
    assert len(fake.objects(path)) == 3


def test_missing_domain(monkeypatch, fake):
    res = run(monkeypatch, authdomain_mapping, **MAPPING)
    assert res.failed and "authentication domain corp does not exist" in res.result["msg"]
    res = run(monkeypatch, authdomain_mapping, state="absent", **MAPPING)
    assert not res.failed and not res.result["changed"]


def test_delete_only_the_pair(monkeypatch, fake):
    path = add_domain(fake)
    add_mapping(fake, path)
    other = add_mapping(fake, path, external_group="CN=Others,DC=example,DC=com")
    assert run(monkeypatch, authdomain_mapping, check_mode=True, state="absent", **MAPPING).result["changed"]
    assert len(fake.objects(path)) == 2
    assert run(monkeypatch, authdomain_mapping, state="absent", **MAPPING).result["changed"]
    assert fake.objects(path) == [other]
    assert not run(monkeypatch, authdomain_mapping, state="absent", **MAPPING).result["changed"]


def test_info(monkeypatch, fake):
    path = add_domain(fake)
    add_mapping(fake, path)
    add_mapping(fake, path, external_group="CN=Others,DC=example,DC=com")
    add_mapping(fake, path, user_group="admins-eu")
    assert len(run(monkeypatch, authdomain_mapping_info, domain_name="corp").result["mappings"]) == 3
    assert len(run(monkeypatch, authdomain_mapping_info, domain_name="corp", user_group="admins").result["mappings"]) == 2
    one = run(monkeypatch, authdomain_mapping_info, domain_name="corp", user_group="admins",
              external_group="cn=others,dc=example,dc=com").result
    assert [m["external_group"] for m in one["mappings"]] == ["CN=Others,DC=example,DC=com"] and not one["changed"]
    res = run(monkeypatch, authdomain_mapping_info, domain_name="nope")
    assert res.failed and "does not exist" in res.result["msg"]
