#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: config_x509
short_description: Manage the X.509 configuration of a WALLIX Bastion
version_added: 1.1.0
description:
  - Install the certificate the Bastion GUI and API serve, and configure the X.509 authentication of users.
  - With O(state=absent), restore the default configuration of the Bastion (its own certificate,
    X.509 authentication disabled).
  - Equivalent of the C(wallix-bastion_config_x509) Terraform resource.
  - The X.509 configuration is a singleton. The Bastion API returns the subject of the certificates, not
    the certificates themselves, so the module compares the common name (CN) of the certificates given
    with the subjects returned, like the Terraform provider does. The private key cannot be compared,
    see O(update_password).
author:
  - WALLIX (@wallix)
extends_documentation_fragment:
  - wallix.bastion.connection
attributes:
  check_mode:
    description: Can run in check_mode and return changed status prediction without modifying target.
    support: full
  diff_mode:
    description: Will return details on what has changed (or possibly needs changing in check_mode), when in diff mode.
    support: full
options:
  server_public_key:
    description:
      - Server certificate the GUI and the API serve, in PEM format.
      - Required when O(state=present).
    type: str
  server_private_key:
    description:
      - Private key of O(server_public_key), in PEM format.
      - Required when O(state=present). Sent with every change.
    type: str
  ca_certificate:
    description:
      - Certificate, or chain, in PEM format of the authority the certificates of the users
        must be signed by, for X.509 authentication.
      - When the configuration is written and this option is not set, the Bastion may drop its current CA.
    type: str
  enable:
    description:
      - Whether X.509 authentication of users is enabled.
      - When unset, a change keeps the current value, or V(false) when installing the configuration.
    type: bool
  update_password:
    description:
      - V(on_create) writes the configuration only when it is not installed yet or when a compared
        option differs.
      - V(always) writes it on every run, which then always reports a change. Use it to replace
        O(server_private_key) or a certificate with the same common name.
    type: str
    choices: [always, on_create]
    default: on_create
  state:
    description:
      - V(present) installs the configuration. V(absent) restores the default one.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Every change restarts the HTTPS listener of the Bastion. The module waits for the API to answer again.
  - Changing the certificate changes what O(validate_certs) checks. Enabling X.509 authentication may change
    how the API authenticates the account used by Ansible. Test on a non-production Bastion first.
"""

EXAMPLES = r"""
- name: Install the ACME certificate and enable X.509 authentication
  wallix.bastion.config_x509:
    server_public_key: "{{ lookup('ansible.builtin.file', 'cert.pem') }}"
    server_private_key: "{{ lookup('ansible.builtin.file', 'privkey.pem') }}"
    ca_certificate: "{{ lookup('ansible.builtin.file', 'chain.pem') }}"
    enable: true

- name: Go back to the default certificate of the Bastion
  wallix.bastion.config_x509:
    state: absent
"""

RETURN = r"""
config_x509:
  description:
    - The X.509 configuration as returned by the Bastion API after the change, without the private key.
    - Certificates are returned as their subject.
    - In check mode, the expected configuration.
  returned: always
  type: dict
  sample:
    ca_certificate: /C=FR/O=WALLIX/CN=Users CA
    server_public_key: /C=FR/O=WALLIX/CN=bastion.example.com
    enable: true
    default: false
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when O(state=present)
  type: list
  elements: str
  sample: [enable]
"""

import base64
import re
import time

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule

PATH = "config/x509"
VIEW = ("ca_certificate", "server_public_key", "enable", "default")
CN_OID = b"\x55\x04\x03"
PEM_RE = re.compile(r"-----BEGIN CERTIFICATE-----(.+?)-----END CERTIFICATE-----", re.S)
# Like the provider: wait for the HTTPS listener to restart with the new certificate.
SETTLE_SECONDS = 3
RETRIES = 10


def _der(data, pos):
    """(tag, start of content, end of content) of the DER element at pos."""
    tag = data[pos]
    length = data[pos + 1]
    pos += 2
    if length & 0x80:
        count = length & 0x7F
        length = int.from_bytes(data[pos:pos + count], "big")
        pos += count
    if pos + length > len(data):
        raise ValueError("truncated DER")
    return tag, pos, pos + length


def _children(data, start, end):
    while start < end:
        tag, cstart, cend = _der(data, start)
        yield tag, cstart, cend
        start = cend


def subject_cn(der):
    """Common name of the subject of a DER certificate, or None."""
    start, end = _der(der, 0)[1:]  # Certificate
    start, end = _der(der, start)[1:]  # tbsCertificate
    fields = list(_children(der, start, end))
    if fields and fields[0][0] == 0xA0:  # explicit version
        fields = fields[1:]
    start, end = fields[4][1:]  # serial, signature, issuer, validity, subject
    for rdn in _children(der, start, end):  # RelativeDistinguishedName (SET)
        for attr in _children(der, rdn[1], rdn[2]):  # AttributeTypeAndValue
            oid, value = list(_children(der, attr[1], attr[2]))[:2]
            ostart, oend = oid[1:]
            vtag, vs, ve = value
            if der[ostart:oend] == CN_OID:
                raw = der[vs:ve]
                return raw.decode("utf-16-be" if vtag == 0x1E else "utf-8", errors="replace")
    return None


def certificate_cns(module, option):
    """Common names of the certificates of a PEM option, failing the module on invalid input."""
    pem = module.params.get(option)
    if pem is None:
        return None
    try:
        cns = [subject_cn(base64.b64decode("".join(block.split()))) for block in PEM_RE.findall(pem)]
    except (ValueError, IndexError, TypeError):
        cns = []
    cns = [cn for cn in cns if cn]
    if not cns:
        module.fail_json(msg="%s is not a PEM certificate with a subject common name" % option)
    return cns


def has_cn(subject, cns):
    """Whether a subject returned by the API (/C=FR/O=X/CN=name) has one of the common names."""
    parts = [p.strip() for p in re.split(r"[/,]", subject or "")]
    return any("CN=%s" % cn in parts for cn in cns)


def view(obj):
    return {k: obj[k] for k in VIEW if k in obj}


def read(client):
    return client.get(PATH) or {"default": True}


def read_after_change(client):
    time.sleep(SETTLE_SECONDS)
    for attempt in range(RETRIES):
        try:
            return read(client)
        except BastionError:
            if attempt == RETRIES - 1:
                raise
            time.sleep(SETTLE_SECONDS)


def main():
    module = BastionModule(
        argument_spec=dict(
            server_public_key=dict(type="str"),
            server_private_key=dict(type="str", no_log=True),
            ca_certificate=dict(type="str"),
            enable=dict(type="bool"),
            update_password=dict(type="str", choices=["always", "on_create"], default="on_create", no_log=False),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        required_if=[("state", "present", ("server_public_key", "server_private_key"))],
        supports_check_mode=True,
    )
    params = module.params
    client = module.client
    try:
        current = read(client)
        configured = not current.get("default")
        before = view(current)

        if params["state"] == "absent":
            after = current
            if configured:
                if not module.check_mode:
                    client.call("DELETE", PATH, expected=(200, 204, 404))
                    after = read_after_change(client)
                else:
                    after = {"default": True}
            module.exit_json(changed=configured, config_x509=view(after),
                             diff=dict(before=before, after=view(after) if configured else before))

        public_cns = certificate_cns(module, "server_public_key")
        ca_cns = certificate_cns(module, "ca_certificate")
        enable = params["enable"]
        if enable is None:
            enable = bool(current.get("enable")) if configured else False

        expected = dict(current, default=False, enable=enable)
        changes = []
        if not configured or not has_cn(current.get("server_public_key"), public_cns):
            changes.append("server_public_key")
            expected["server_public_key"] = "/CN=%s" % public_cns[0]
        if ca_cns and (not configured or not has_cn(current.get("ca_certificate"), ca_cns)):
            changes.append("ca_certificate")
            expected["ca_certificate"] = "/CN=%s" % ca_cns[0]
        enable_changed = enable != bool(current.get("enable")) if configured else params["enable"] is not None
        if enable_changed:
            changes.append("enable")
        if changes or params["update_password"] == "always":
            changes.append("server_private_key")
        changes = sorted(set(changes))

        after = current
        if changes:
            after = expected
            if not module.check_mode:
                body = dict(server_public_key=params["server_public_key"],
                            server_private_key=params["server_private_key"], enable=enable)
                if params["ca_certificate"] is not None:
                    body["ca_certificate"] = params["ca_certificate"]
                client.call("PUT" if configured else "POST", PATH, body)
                after = read_after_change(client)
        module.exit_json(changed=bool(changes), changed_fields=changes, config_x509=view(after),
                         diff=dict(before=before, after=view(after)))
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)


if __name__ == "__main__":
    main()
