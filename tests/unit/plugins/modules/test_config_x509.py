# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

from urllib.parse import urlparse

import pytest

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

try:
    from ansible.module_utils.testing import patch_module_args  # ansible-core >= 2.19
except ImportError:
    patch_module_args = None

from ansible_collections.wallix.bastion.plugins.module_utils import client as client_utils
from ansible_collections.wallix.bastion.plugins.module_utils.client import Response
from ansible_collections.wallix.bastion.tests.unit.plugins.module_utils.fake_bastion import FakeBastion
from ansible_collections.wallix.bastion.plugins.modules import config_x509, config_x509_info

CONN = dict(bastion_host="bastion.test", bastion_user="admin", bastion_token="token")


class ModuleExit(Exception):
    def __init__(self, result, failed=False):
        super(ModuleExit, self).__init__(result)
        self.result = result
        self.failed = failed


class SingletonBastion(FakeBastion):
    """FakeBastion plus configuration singletons: one object at a fixed path, GET/PUT (POST/DELETE if allowed)."""

    def __init__(self):
        super(SingletonBastion, self).__init__()
        self.singletons = {}
        self.methods = {}
        self.put_status = 204

    def set(self, path, obj, methods=("GET", "PUT")):
        self.singletons[path] = obj
        self.methods[path] = methods

    def handle(self, client, method, url, data, headers, auth):
        prefix = "/api/%s/" % self.api_version
        path = urlparse(url).path
        rel = path[len(prefix):].strip("/") if path.startswith(prefix) else None
        if rel not in self.singletons:
            return super(SingletonBastion, self).handle(client, method, url, data, headers, auth)
        body = json.loads(data) if data else None
        self.calls.append((method, path, body))
        if method not in self.methods[rel]:
            return Response(405, '{"error": "method not allowed"}', {})
        if method == "GET":
            obj = self.singletons[rel]
            return Response(200, json.dumps(obj), {}) if obj is not None else Response(404, "{}", {})
        if self.put_status != 204:
            return Response(self.put_status, '{"error": "refused"}', {})
        self.on_write(rel, method, body)
        return Response(204, "", {})

    def on_write(self, path, method, body):
        if method == "DELETE":
            self.singletons[path] = None
        else:
            self.singletons[path] = dict(self.singletons[path] or {}, **body)


@pytest.fixture
def fake(monkeypatch):
    fake = SingletonBastion()
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


# Throwaway self-signed public certificates (no private key): CN=bastion.test and CN=users-ca.
SERVER_CERT = """-----BEGIN CERTIFICATE-----
MIIBuzCCAWGgAwIBAgIUb9ifZMRkWbelG6I4dT7naXq1oywwCgYIKoZIzj0EAwIw
MzELMAkGA1UEBhMCRlIxDTALBgNVBAoMBFRlc3QxFTATBgNVBAMMDGJhc3Rpb24u
dGVzdDAeFw0yNjEwMDExMjIyNThaFw0zNjA5MjgxMjIyNThaMDMxCzAJBgNVBAYT
AkZSMQ0wCwYDVQQKDARUZXN0MRUwEwYDVQQDDAxiYXN0aW9uLnRlc3QwWTATBgcq
hkjOPQIBBggqhkjOPQMBBwNCAATuPVxACvYMEbofIYBJazMKoTEaCt7a+e+wuTzN
QWBQilEWKZO3dqHyB2vuwVd59QYuUdK9bYAsdtGi7QNPC/FJo1MwUTAdBgNVHQ4E
FgQUFZg8WppRXIZF+3hNMkqcBnkGujAwHwYDVR0jBBgwFoAUFZg8WppRXIZF+3hN
MkqcBnkGujAwDwYDVR0TAQH/BAUwAwEB/zAKBggqhkjOPQQDAgNIADBFAiEApLwX
nKvtU6FQP+WM2kSgHMA23V/uFrQ4mNAOjns/hqQCIGShAL7Q5DtYowBeqPA7oQhz
Idtcxm8ggzZhIB3FVuV9
-----END CERTIFICATE-----
"""
CA_CERT = """-----BEGIN CERTIFICATE-----
MIIBszCCAVmgAwIBAgIUYmxMJC33KrAz/UKnMT7WrYVFhDAwCgYIKoZIzj0EAwIw
LzELMAkGA1UEBhMCRlIxDTALBgNVBAoMBFRlc3QxETAPBgNVBAMMCHVzZXJzLWNh
MB4XDTI2MTAwMTEyMjI1OFoXDTM2MDkyODEyMjI1OFowLzELMAkGA1UEBhMCRlIx
DTALBgNVBAoMBFRlc3QxETAPBgNVBAMMCHVzZXJzLWNhMFkwEwYHKoZIzj0CAQYI
KoZIzj0DAQcDQgAEgu54zprZPSEmlboFMhQjjDL16WOsYpuLg8p5pgiVU/SrdC/8
60Lw/iMubVDrChkJZyWitM3DPJVv1Ezg16sLeqNTMFEwHQYDVR0OBBYEFKsPb0kR
9wwjCKw2uChz5jgmeeP8MB8GA1UdIwQYMBaAFKsPb0kR9wwjCKw2uChz5jgmeeP8
MA8GA1UdEwEB/wQFMAMBAf8wCgYIKoZIzj0EAwIDSAAwRQIgR8ApwZdnmuRQnz1b
FtSFo8fHSbG97w3mSCXUG//ZCRECIQCvRiIINapfuZZ/+2ol75sXtieTbQm4EhIl
4hslaodSCQ==
-----END CERTIFICATE-----
"""
SUBJECTS = {SERVER_CERT: "/C=FR/O=Test/CN=bastion.test", CA_CERT: "/C=FR/O=Test/CN=users-ca"}
DEFAULT = dict(ca_certificate="/C=FR/O=WALLIX/CN=Default CA", server_private_key="********",
               server_public_key="/C=FR/O=WALLIX/CN=wab", enable=False, default=True)
KEY = "PRIVATE KEY PLACEHOLDER"


@pytest.fixture
def x509(fake, monkeypatch):
    monkeypatch.setattr(config_x509.time, "sleep", lambda seconds: None)
    fake.set("config/x509", dict(DEFAULT), methods=("GET", "POST", "PUT", "DELETE"))

    def on_write(path, method, body):
        if method == "DELETE":
            fake.singletons[path] = dict(DEFAULT)
            return
        fake.singletons[path] = dict(
            ca_certificate=SUBJECTS.get(body.get("ca_certificate"), ""), server_private_key="********",
            server_public_key=SUBJECTS[body["server_public_key"]], enable=body["enable"], default=False)
    fake.on_write = on_write
    return fake


def configure(fake, **overrides):
    obj = dict(ca_certificate="/C=FR/O=Test/CN=users-ca", server_private_key="********",
               server_public_key="/C=FR/O=Test/CN=bastion.test", enable=True, default=False)
    fake.singletons["config/x509"] = dict(obj, **overrides)


def test_subject_cn():
    assert config_x509.certificate_cns(type("M", (), {"params": {"c": SERVER_CERT + CA_CERT}})(), "c") == [
        "bastion.test", "users-ca"]
    assert config_x509.has_cn("/C=FR/O=Test/CN=bastion.test", ["bastion.test"])
    assert not config_x509.has_cn("/C=FR/O=Test/CN=bastion.test2", ["bastion.test"])


def test_install_posts(monkeypatch, x509):
    res = run(monkeypatch, config_x509, server_public_key=SERVER_CERT, server_private_key=KEY,
              ca_certificate=CA_CERT, enable=True)
    assert not res.failed and res.result["changed"]
    assert res.result["changed_fields"] == ["ca_certificate", "enable", "server_private_key", "server_public_key"]
    assert x509.writes() == [("POST", "/api/v3.12/config/x509", dict(
        server_public_key=SERVER_CERT, server_private_key=KEY, ca_certificate=CA_CERT, enable=True))]
    assert res.result["config_x509"] == dict(ca_certificate="/C=FR/O=Test/CN=users-ca", enable=True, default=False,
                                             server_public_key="/C=FR/O=Test/CN=bastion.test")


def test_install_check_mode(monkeypatch, x509):
    res = run(monkeypatch, config_x509, check_mode=True, server_public_key=SERVER_CERT, server_private_key=KEY)
    assert res.result["changed"] and x509.writes() == []
    assert res.result["diff"]["after"]["server_public_key"] == "/CN=bastion.test"
    assert res.result["diff"]["after"]["default"] is False


def test_idempotent(monkeypatch, x509):
    configure(x509)
    res = run(monkeypatch, config_x509, server_public_key=SERVER_CERT, server_private_key=KEY,
              ca_certificate=CA_CERT, enable=True)
    assert not res.result["changed"] and res.result["changed_fields"] == [] and x509.writes() == []
    assert "server_private_key" not in res.result["config_x509"]


def test_enable_change_puts_everything(monkeypatch, x509):
    configure(x509)
    res = run(monkeypatch, config_x509, server_public_key=SERVER_CERT, server_private_key=KEY, enable=False)
    assert res.result["changed_fields"] == ["enable", "server_private_key"]
    assert x509.writes() == [("PUT", "/api/v3.12/config/x509", dict(
        server_public_key=SERVER_CERT, server_private_key=KEY, enable=False))]


def test_unset_enable_keeps_current(monkeypatch, x509):
    configure(x509, ca_certificate="")
    res = run(monkeypatch, config_x509, server_public_key=SERVER_CERT, server_private_key=KEY, ca_certificate=CA_CERT)
    assert res.result["changed_fields"] == ["ca_certificate", "server_private_key"]
    assert x509.writes()[0][2]["enable"] is True


def test_other_certificate_is_a_change(monkeypatch, x509):
    configure(x509, server_public_key="/C=FR/O=Test/CN=old.test")
    res = run(monkeypatch, config_x509, check_mode=True, server_public_key=SERVER_CERT, server_private_key=KEY)
    assert "server_public_key" in res.result["changed_fields"] and x509.writes() == []


def test_update_password_always(monkeypatch, x509):
    configure(x509)
    res = run(monkeypatch, config_x509, server_public_key=SERVER_CERT, server_private_key=KEY,
              update_password="always")
    assert res.result["changed_fields"] == ["server_private_key"] and x509.writes()[0][0] == "PUT"


def test_invalid_certificate(monkeypatch, x509):
    res = run(monkeypatch, config_x509, server_public_key="not a cert", server_private_key=KEY)
    assert res.failed and "server_public_key" in res.result["msg"] and x509.writes() == []


def test_keys_required_when_present(monkeypatch, x509):
    assert run(monkeypatch, config_x509, enable=True).failed


def test_absent_deletes_and_again(monkeypatch, x509):
    configure(x509)
    assert run(monkeypatch, config_x509, check_mode=True, state="absent").result["changed"]
    assert x509.writes() == []
    res = run(monkeypatch, config_x509, state="absent")
    assert res.result["changed"] and res.result["config_x509"]["default"] is True
    assert x509.writes() == [("DELETE", "/api/v3.12/config/x509", None)]
    assert not run(monkeypatch, config_x509, state="absent").result["changed"]
    assert len(x509.writes()) == 1


def test_info(monkeypatch, x509):
    res = run(monkeypatch, config_x509_info).result
    assert res["config_x509"]["default"] is True and "server_private_key" not in res["config_x509"]
