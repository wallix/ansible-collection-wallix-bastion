# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
name: secret
short_description: Check out account secrets from a WALLIX Bastion
version_added: 1.0.0
description:
  - Check out the password (or another secret) of each target account from a WALLIX Bastion,
    with C(GET /api/<version>/targetpasswords/checkout/<target>).
  - The authenticated user (O(bastion_user)) must be granted password retrieval on the account by
    an authorization; the Bastion answers C(NOT_AUTHORIZED) otherwise, also for an administrator.
  - Use the M(wallix.bastion.secret) module to extend or check in a checkout explicitly.
author:
  - WALLIX (@wallix)
options:
  _terms:
    description:
      - Account targets, in the Bastion format C(<account>@<domain>@<device>),
        C(<account>@<domain>@<application>) or C(<account>@<domain>) for a global domain account.
    type: list
    elements: str
    required: true
  field:
    description:
      - What to return for each target.
      - V(all) returns the whole checkout response as a dictionary.
      - The lookup fails when the account has no such secret.
    type: str
    choices: [password, ssh_key, ssh_certificate, login, all]
    default: password
  checkin:
    description:
      - Check the account in again right after reading the secret, so it is not left locked
        for the duration of the checkout policy.
    type: bool
    default: false
  authorization:
    description:
      - Name of the authorization to use when several give access to the account.
    type: str
  duration:
    description:
      - Requested checkout duration in seconds, within the limits of the account's checkout policy.
    type: int
  key_format:
    description:
      - Format of the returned SSH private key.
    type: str
    choices: [openssh, pkcs1, pkcs8, putty]
  cert_format:
    description:
      - Format of the returned SSH certificate.
    type: str
    choices: [openssh, ssh.com]
  key_passphrase:
    description:
      - Passphrase the Bastion encrypts the returned SSH private key with, sent in the
        C(X-Key-Passphrase) header.
    type: str
  bastion_host:
    description:
      - Hostname or IP address of the WALLIX Bastion.
    type: str
    env:
      - name: WALLIX_BASTION_HOST
    vars:
      - name: wallix_bastion_host
  bastion_port:
    description:
      - HTTPS port of the WALLIX Bastion API. V(443) when not set.
    type: int
    env:
      - name: WALLIX_BASTION_PORT
    vars:
      - name: wallix_bastion_port
  bastion_user:
    description:
      - User to authenticate with. With O(bastion_token), the user the API key belongs to.
    type: str
    env:
      - name: WALLIX_BASTION_USER
    vars:
      - name: wallix_bastion_user
  bastion_password:
    description:
      - Password of O(bastion_user). One of O(bastion_password) or O(bastion_token) is required.
    type: str
    env:
      - name: WALLIX_BASTION_PASSWORD
    vars:
      - name: wallix_bastion_password
  bastion_token:
    description:
      - API key of O(bastion_user). Takes precedence over O(bastion_password).
    type: str
    env:
      - name: WALLIX_BASTION_TOKEN
    vars:
      - name: wallix_bastion_token
  api_version:
    description:
      - Version of the Bastion REST API to use, V(v3.8) or V(v3.12). V(v3.12) when not set.
    type: str
    env:
      - name: WALLIX_BASTION_API_VERSION
    vars:
      - name: wallix_bastion_api_version
  validate_certs:
    description:
      - Whether to validate the Bastion's TLS certificate.
      - When not set, the inverse of E(WALLIX_INSECURE_SKIP_VERIFY) is used, then V(true).
    type: bool
    env:
      - name: WALLIX_BASTION_VALIDATE_CERTS
    vars:
      - name: wallix_bastion_validate_certs
  csrf_enabled:
    description:
      - Send the CSRF token the Bastion issues at login. V(true) when not set.
    type: bool
    env:
      - name: WALLIX_CSRF_ENABLED
    vars:
      - name: wallix_bastion_csrf_enabled
  bastion_timeout:
    description:
      - Timeout in seconds of each HTTP request to the Bastion API.
    type: int
    default: 30
    vars:
      - name: wallix_bastion_timeout
notes:
  - Each lookup call is a checkout. It is recorded in the Bastion audit trail and, when the
    account's checkout policy locks accounts, locks the account for other users until it is checked
    in or the checkout expires. Lookups are evaluated every time the expression is templated, also
    in check mode; store the result with C(ansible.builtin.set_fact) to check out only once.
  - The lookup runs on the controller and connects to the Bastion from there.
  - The returned secrets are marked unsafe, so they are never templated. Set C(no_log=true) on
    tasks that use them.
  - The connection environment variables are the ones of the C(wallix/wallix-bastion) Terraform
    provider and of the modules of this collection.
"""

EXAMPLES = r"""
- name: Use a database password
  ansible.builtin.command: /usr/local/bin/db-maintenance
  environment:
    DB_PASSWORD: "{{ lookup('wallix.bastion.secret', 'dbadmin@local@db-01', checkin=true) }}"
  no_log: true

- name: Get an SSH key in PuTTY format
  ansible.builtin.copy:
    content: "{{ lookup('wallix.bastion.secret', 'deploy@local@srv-linux-01', field='ssh_key', key_format='putty') }}"
    dest: /secure/deploy.ppk
    mode: "0600"
  no_log: true

- name: Get the whole checkout response, with explicit connection options
  ansible.builtin.set_fact:
    root_checkout: >-
      {{ lookup('wallix.bastion.secret', 'root@local@srv-linux-01', field='all',
                bastion_host='bastion.example.com', bastion_user='automation',
                bastion_token=vault_bastion_api_key) }}
  no_log: true
"""

RETURN = r"""
_raw:
  description:
    - One element per target. The secret selected by O(field), or with O(field=all) a dictionary
      with C(login), C(password), C(ssh_key), C(ssh_certificate), C(locked), C(checkin_time) and the
      other fields the Bastion returns.
  type: list
  elements: raw
"""

from urllib.parse import quote, urlencode

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from ansible.utils.unsafe_proxy import wrap_var

from ansible_collections.wallix.bastion.plugins.module_utils.client import (
    CONNECTION_ARGUMENT_SPEC,
    BastionClient,
    BastionError,
    resolve_connection,
    validate_connection,
)


def _error(resp):
    try:
        data = resp.json() or {}
    except BastionError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    text = ": ".join(str(data[k]) for k in ("error", "description") if data.get(k)) or resp.body.strip()
    if data.get("reason"):
        text += " (%s)" % data["reason"]
    return "HTTP %d: %s" % (resp.status, text)


class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):
        self.set_options(var_options=variables, direct=kwargs)

        conn = resolve_connection({k: self.get_option(k) for k in CONNECTION_ARGUMENT_SPEC})
        error = validate_connection(conn)
        if error:
            raise AnsibleError("wallix.bastion.secret: %s" % error)
        client = BastionClient(**conn)
        headers = None
        if self.get_option("key_passphrase"):
            headers = {"X-Key-Passphrase": self.get_option("key_passphrase")}

        query = {}
        for option in ("authorization", "duration", "key_format", "cert_format"):
            if self.get_option(option) is not None:
                query[option] = self.get_option(option)
        suffix = "?" + urlencode(query) if query else ""
        field = self.get_option("field")

        results = []
        for target in terms:
            quoted = quote(target, safe="@")
            try:
                resp = client.request("GET", "targetpasswords/checkout/%s%s" % (quoted, suffix), headers=headers)
                if resp.status != 200:
                    raise AnsibleError("wallix.bastion.secret: checkout of %s failed: %s" % (target, _error(resp)))
                data = resp.json() or {}
                if self.get_option("checkin"):
                    checkin = "targetpasswords/checkin/%s" % quoted
                    if self.get_option("authorization"):
                        checkin += "?" + urlencode(dict(authorization=self.get_option("authorization")))
                    resp = client.request("GET", checkin)
                    if resp.status not in (200, 409):
                        raise AnsibleError("wallix.bastion.secret: checkin of %s failed: %s" % (target, _error(resp)))
            except BastionError as e:
                raise AnsibleError("wallix.bastion.secret: checkout of %s failed: %s" % (target, e))

            if field == "all":
                results.append(data)
            elif data.get(field):
                results.append(data[field])
            else:
                available = sorted(k for k in ("password", "ssh_key", "ssh_certificate") if data.get(k))
                raise AnsibleError("wallix.bastion.secret: account %s has no %s (available: %s)" % (
                    target, field, ", ".join(available) or "none"))
        return [wrap_var(r) for r in results]
