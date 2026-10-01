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
from ansible_collections.wallix.bastion.plugins.modules import device_service, device_service_info
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


SSH = dict(service_name="SSH", connection_policy="SSH", port=22, protocol="SSH", subprotocols=["SSH_SHELL_SESSION"])


@pytest.fixture
def device_id(fake):
    return fake.add("devices", {"device_name": "srv", "host": "10.0.0.1"})["id"]


def services(fake, device_id):
    return fake.objects("devices/%s/services" % device_id)


def test_create(monkeypatch, fake, device_id):
    res = run(monkeypatch, device_service, device_name="srv", **SSH)
    assert not res.failed and res.result["changed"]
    assert res.result["service"]["port"] == 22 and res.result["service"]["id"]
    method, path, body = fake.writes()[0]
    assert (method, path) == ("POST", "/api/v3.12/devices/%s/services" % device_id)
    assert body == SSH


def test_create_requires_policy_port_protocol(monkeypatch, fake, device_id):
    res = run(monkeypatch, device_service, device_name="srv", service_name="SSH")
    assert res.failed and "connection_policy, port, protocol required" in res.result["msg"]
    assert fake.writes() == []


def test_create_check_mode_writes_nothing(monkeypatch, fake, device_id):
    res = run(monkeypatch, device_service, check_mode=True, device_name="srv", **SSH)
    assert res.result["changed"] and res.result["diff"]["after"]["port"] == 22
    assert fake.writes() == []


def test_missing_device_fails(monkeypatch, fake):
    res = run(monkeypatch, device_service, device_name="nope", **SSH)
    assert res.failed and res.result["msg"] == "device nope does not exist"


def test_missing_device_absent_is_ok(monkeypatch, fake):
    res = run(monkeypatch, device_service, device_name="nope", service_name="SSH", state="absent")
    assert not res.failed and not res.result["changed"]


def test_no_change_is_idempotent(monkeypatch, fake, device_id):
    fake.add("devices/%s/services" % device_id, dict(SSH, subprotocols=["SSH_SCP_UP", "SSH_SHELL_SESSION"],
                                                     global_domains=[]))
    params = dict(SSH)
    params["subprotocols"] = ["SSH_SHELL_SESSION", "SSH_SCP_UP"]
    res = run(monkeypatch, device_service, device_name="srv", **params)
    assert not res.result["changed"] and res.result["changed_fields"] == []
    assert fake.writes() == []


def test_update_keeps_unset_options_and_omits_read_only(monkeypatch, fake, device_id):
    obj = fake.add("devices/%s/services" % device_id, dict(SSH, global_domains=["corp"]))
    res = run(monkeypatch, device_service, device_name="srv", service_name="SSH", port=2222)
    assert res.result["changed"] and res.result["changed_fields"] == ["port"]
    method, path, body = fake.writes()[0]
    assert method == "PUT" and path.endswith("/services/%s" % obj["id"])
    # The API rejects service_name and protocol in a PUT.
    assert body == {"connection_policy": "SSH", "port": 2222, "subprotocols": ["SSH_SHELL_SESSION"],
                    "global_domains": ["corp"]}
    assert services(fake, device_id)[0]["port"] == 2222


def test_update_uses_force(monkeypatch, fake, device_id):
    fake.add("devices/%s/services" % device_id, SSH)
    urls = []
    handle = fake.handle

    def record(client, method, url, *args):
        urls.append((method, url))
        return handle(client, method, url, *args)

    monkeypatch.setattr(fake, "handle", record)
    run(monkeypatch, device_service, device_name="srv", service_name="SSH", port=2222)
    assert [u for m, u in urls if m == "PUT"][0].endswith("?force=true")


def test_protocol_is_create_only(monkeypatch, fake, device_id):
    fake.add("devices/%s/services" % device_id, SSH)
    res = run(monkeypatch, device_service, device_name="srv", service_name="SSH", protocol="RDP")
    assert res.failed and "protocol cannot be changed" in res.result["msg"]
    assert fake.writes() == []


def test_update_check_mode(monkeypatch, fake, device_id):
    fake.add("devices/%s/services" % device_id, SSH)
    res = run(monkeypatch, device_service, check_mode=True, device_name="srv", service_name="SSH", port=23)
    assert res.result["changed"] and res.result["diff"]["after"]["port"] == 23
    assert res.result["diff"]["before"]["port"] == 22
    assert fake.writes() == []


def test_delete_and_delete_again(monkeypatch, fake, device_id):
    fake.add("devices/%s/services" % device_id, SSH)
    assert run(monkeypatch, device_service, device_name="srv", service_name="SSH", state="absent").result["changed"]
    assert services(fake, device_id) == []
    assert not run(monkeypatch, device_service, device_name="srv", service_name="SSH", state="absent").result["changed"]


def test_delete_check_mode(monkeypatch, fake, device_id):
    fake.add("devices/%s/services" % device_id, SSH)
    res = run(monkeypatch, device_service, check_mode=True, device_name="srv", service_name="SSH", state="absent")
    assert res.result["changed"] and len(services(fake, device_id)) == 1


def test_info(monkeypatch, fake, device_id):
    fake.add("devices/%s/services" % device_id, SSH)
    fake.add("devices/%s/services" % device_id, dict(SSH, service_name="SSH2"))
    one = run(monkeypatch, device_service_info, device_name="srv", service_name="SSH").result
    assert [s["service_name"] for s in one["services"]] == ["SSH"] and not one["changed"]
    assert len(run(monkeypatch, device_service_info, device_name="srv").result["services"]) == 2
    assert run(monkeypatch, device_service_info, device_name="srv", service_name="x").result["services"] == []
    assert run(monkeypatch, device_service_info, device_name="nope").failed
