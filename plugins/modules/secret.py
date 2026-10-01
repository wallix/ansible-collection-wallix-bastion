#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: secret
short_description: Check out, extend or check in an account password on a WALLIX Bastion
version_added: 1.0.0
description:
  - Retrieve the password, SSH key or SSH certificate of a target account from a WALLIX Bastion
    (C(GET /api/<version>/targetpasswords/checkout/<target>)), extend the checkout, or release it.
  - The authenticated user (O(bastion_user)) must be granted password retrieval on the account by
    an authorization (C(authorize_password_retrieval)); the Bastion answers C(NOT_AUTHORIZED) otherwise,
    also for an administrator.
  - There is no Terraform equivalent; to read secrets from a play's templates, see the
    P(wallix.bastion.secret#lookup) lookup.
author:
  - WALLIX (@wallix)
extends_documentation_fragment:
  - wallix.bastion.connection
attributes:
  check_mode:
    description: Can run in check_mode and return changed status prediction without modifying target.
    support: partial
    details:
      - In check mode nothing is checked out, extended or checked in, so no secret is returned.
        C(changed) is V(true) because the Bastion has no call telling in advance whether the action
        would succeed.
      - Set C(check_mode=false) on the task to retrieve the secret in a check mode run anyway.
  diff_mode:
    description: Will return details on what has changed (or possibly needs changing in check_mode), when in diff mode.
    support: none
options:
  account:
    description:
      - Name of the account.
    type: str
    required: true
  domain:
    description:
      - Domain of the account, that is the local domain of O(device) or O(application), or a global domain.
    type: str
    required: true
  device:
    description:
      - Device of the account, for an account of a device local domain.
      - The target is then C(<account>@<domain>@<device>).
    type: str
  application:
    description:
      - Application of the account, for an account of an application local domain.
      - The target is then C(<account>@<domain>@<application>).
      - Without O(device) and O(application), the target is C(<account>@<domain>), an account of a global domain.
    type: str
  authorization:
    description:
      - Name of the authorization to use when several give access to the account.
    type: str
  duration:
    description:
      - Requested checkout duration in seconds, within the limits of the account's checkout policy.
      - Only used with O(state=checkout).
    type: int
  key_format:
    description:
      - Format of the returned SSH private key. The Bastion refuses formats the key type does not
        support (for example V(pkcs8) for an Ed25519 key).
      - Only used with O(state=checkout).
    type: str
    choices: [openssh, pkcs1, pkcs8, putty]
  cert_format:
    description:
      - Format of the returned SSH certificate.
      - Only used with O(state=checkout).
    type: str
    choices: [openssh, ssh.com]
  key_passphrase:
    description:
      - Passphrase the Bastion encrypts the returned SSH private key with.
      - Sent in the C(X-Key-Passphrase) header, never in the URL.
      - Only used with O(state=checkout).
    type: str
  force:
    description:
      - Check in an account checked out by another user. Requires the corresponding Bastion right.
      - Only used with O(state=checkin).
    type: bool
    default: false
  comment:
    description:
      - Reason for a forced checkin. Required when O(force=true).
    type: str
  state:
    description:
      - V(checkout) retrieves the secret and, if the account's checkout policy locks accounts, locks
        it for the user.
      - V(extend) extends the current checkout of the user. It fails when the account is not checked
        out, when its checkout policy does not lock accounts, or when the maximum duration is reached.
      - V(checkin) releases the checkout. An account that is not checked out is not an error and is
        reported unchanged.
    type: str
    choices: [checkout, checkin, extend]
    default: checkout
notes:
  - O(state=checkout) and O(state=extend) always report C(changed=true) when they succeed. Each call
    creates or extends a checkout on the Bastion, which locks the account for other users when the
    checkout policy enables locking, is recorded in the Bastion audit trail, and may make the Bastion
    rotate the password at checkin.
  - The secret is part of the module result. A module cannot hide its own result, so set
    C(no_log=true) on checkout tasks, or the secret is displayed with C(-v) and sent to callbacks.
  - Check in what you check out, or let the checkout policy expire it.
"""

EXAMPLES = r"""
- name: Check out the password of root on a device
  wallix.bastion.secret:
    account: root
    domain: local
    device: srv-linux-01
  register: root_secret
  no_log: true

- name: Use it
  ansible.builtin.command: /usr/local/bin/rotate-db --login "{{ root_secret.login }}"
  environment:
    DB_PASSWORD: "{{ root_secret.password }}"
  no_log: true

- name: Get an SSH key in PuTTY format, encrypted with a passphrase
  wallix.bastion.secret:
    account: deploy
    domain: local
    device: srv-linux-01
    key_format: putty
    key_passphrase: "{{ vault_key_passphrase }}"
  register: deploy_key
  no_log: true

- name: Extend the checkout
  wallix.bastion.secret:
    account: root
    domain: local
    device: srv-linux-01
    state: extend

- name: Release the account
  wallix.bastion.secret:
    account: root
    domain: local
    device: srv-linux-01
    state: checkin

- name: Release an account another user checked out
  wallix.bastion.secret:
    account: root
    domain: local
    device: srv-linux-01
    state: checkin
    force: true
    comment: Operator left without checking in
"""

RETURN = r"""
target:
  description: The account target the call was made for.
  returned: always
  type: str
  sample: root@local@srv-linux-01
login:
  description: Login of the account.
  returned: when O(state=checkout), not in check mode
  type: str
  sample: root
password:
  description: Password of the account. Absent when the account has no password.
  returned: when O(state=checkout), not in check mode, and the account has a password
  type: str
  sample: "Sup3r-S3cret"
ssh_key:
  description:
    - SSH private key of the account, in O(key_format), encrypted with O(key_passphrase) when set.
  returned: when O(state=checkout), not in check mode, and the account has an SSH key
  type: str
  sample: "-----BEGIN OPENSSH PRIVATE KEY-----\n...\n-----END OPENSSH PRIVATE KEY-----\n"
ssh_certificate:
  description: SSH certificate of the account, in O(cert_format).
  returned: when O(state=checkout), not in check mode, and the account has a certificate
  type: str
  sample: ""
checkout:
  description:
    - What the Bastion returned about the checkout, without the secrets.
    - Empty for O(state=checkin) and in check mode.
  returned: always
  type: dict
  sample:
    locked: true
    checkin_time: "2026-10-01 11:48:03"
    remaining_time: 600
    deconnection_time: "2099-12-30 23:59:59"
    checkin_change_password: false
    ssh_key_type: ssh-ed25519
"""

from urllib.parse import quote, urlencode

from ansible_collections.wallix.bastion.plugins.module_utils.client import (
    CONNECTION_ARGUMENT_SPEC,
    BastionClient,
    BastionError,
    resolve_connection,
    validate_connection,
)
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule

SECRET_FIELDS = ("password", "ssh_key", "ssh_certificate")
ACTIONS = dict(checkout="checkout", extend="extendcheckout", checkin="checkin")


def target_name(params):
    parts = [params["account"], params["domain"]]
    if params.get("device") or params.get("application"):
        parts.append(params.get("device") or params.get("application"))
    return "@".join(parts)


def api_error(resp):
    """Readable message from an error response; the body of an error never holds a secret."""
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


def main():
    module = BastionModule(
        argument_spec=dict(
            account=dict(type="str", required=True),
            domain=dict(type="str", required=True),
            device=dict(type="str"),
            application=dict(type="str"),
            authorization=dict(type="str"),
            duration=dict(type="int"),
            key_format=dict(type="str", choices=["openssh", "pkcs1", "pkcs8", "putty"]),
            cert_format=dict(type="str", choices=["openssh", "ssh.com"]),
            key_passphrase=dict(type="str", no_log=True),
            force=dict(type="bool", default=False),
            comment=dict(type="str"),
            state=dict(type="str", choices=["checkout", "checkin", "extend"], default="checkout"),
        ),
        mutually_exclusive=[("device", "application")],
        required_if=[("force", True, ("comment",))],
        supports_check_mode=True,
    )
    params = module.params
    state = params["state"]
    target = target_name(params)
    result = dict(changed=True, target=target, checkout={})

    if module.check_mode:
        module.exit_json(**result)

    query = {}
    if params["authorization"]:
        query["authorization"] = params["authorization"]
    if state == "checkout":
        for option in ("duration", "key_format", "cert_format"):
            if params[option] is not None:
                query[option] = params[option]
    if state == "checkin" and params["force"]:
        query.update(force="true", comment=params["comment"])
    path = "targetpasswords/%s/%s" % (ACTIONS[state], quote(target, safe="@"))
    if query:
        path += "?" + urlencode(query)

    conn = resolve_connection({k: params.get(k) for k in CONNECTION_ARGUMENT_SPEC})
    error = validate_connection(conn)
    if error:
        module.fail_json(msg=error)
    client = BastionClient(**conn)
    headers = None
    if state == "checkout" and params["key_passphrase"]:
        headers = {"X-Key-Passphrase": params["key_passphrase"]}

    try:
        resp = client.request("GET", path, headers=headers)
    except BastionError as e:
        module.fail_json(msg="%s of %s failed: %s" % (state, target, e), target=target)

    if state == "checkin" and resp.status == 409:
        # NOT_CHECKED_OUT: nothing to release, the desired state is already reached.
        result["changed"] = False
        module.exit_json(**result)
    if resp.status != 200:
        module.fail_json(msg="%s of %s failed: %s" % (state, target, api_error(resp)),
                         target=target, status=resp.status)

    try:
        data = resp.json() or {}
    except BastionError:
        module.fail_json(msg="%s of %s failed: the Bastion returned invalid JSON" % (state, target),
                         target=target, status=resp.status)

    if state == "checkout":
        for field in ("login",) + SECRET_FIELDS:
            if data.get(field):
                result[field] = data[field]
    result["checkout"] = {k: v for k, v in data.items() if k not in SECRET_FIELDS + ("login",)}
    module.exit_json(**result)


if __name__ == "__main__":
    main()
