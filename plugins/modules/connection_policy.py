#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: connection_policy
short_description: Manage connection policies on a WALLIX Bastion
version_added: 1.0.0
description:
  - Create, update or delete a connection policy on a WALLIX Bastion.
  - A connection policy sets the authentication methods and the protocol options
    (session, recording, algorithms, ...) of the sessions that use it.
  - Equivalent of the C(wallix-bastion_connection_policy) Terraform resource.
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
  connection_policy_name:
    description:
      - Name of the connection policy. Identifies the policy on the Bastion.
    type: str
    required: true
  protocol:
    description:
      - Protocol of the policy, for example V(SSH), V(RDP), V(VNC), V(TELNET), V(RLOGIN), V(RAWTCPIP)
        or V(WEBAPP). The Bastion validates the value.
      - Required when the policy does not exist yet and O(state=present).
      - Cannot be changed after creation; the module fails if it differs.
    type: str
  type:
    description:
      - Type of the policy, a variant of O(protocol) such as V(SSH-ccn) or V(RDP-ccn)
        (the Bastion validates the value against the protocol).
      - Defaults to O(protocol) on creation with API v3.12.
      - Cannot be changed after creation; the module fails if it differs.
    type: str
  description:
    description:
      - Description of the policy.
    type: str
  authentication_methods:
    description:
      - Authentication methods allowed by the policy. Order does not matter.
      - Known values are V(PASSWORD_VAULT), V(PASSWORD_MAPPING), V(PASSWORD_INTERACTIVE),
        V(PUBKEY_VAULT), V(PUBKEY_AGENT_FORWARDING) and V(KERBEROS_FORWARDING); which ones are
        accepted depends on the protocol.
      - When set, replaces all the methods of the policy. Most protocols require at least one.
    type: list
    elements: str
  options:
    description:
      - >-
        Protocol options, as a dictionary of sections, for example
        V({"session": {"inactivity_timeout": 600}}). A JSON string is accepted too.
      - Only the sections and keys given are compared and sent; the Bastion merges them into the
        current options and fills every other key with its defaults. Key order is irrelevant.
      - Keys cannot be removed, only set to another value. Values are compared with their type,
        so use the type the Bastion returns (V("1") and V(1) are different).
    type: dict
  state:
    description:
      - Whether the connection policy should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - Do not manage the built-in policies (V(SSH), V(RDP), ...) with this module.
"""

EXAMPLES = r"""
- name: SSH policy with a 10 minute inactivity timeout
  wallix.bastion.connection_policy:
    connection_policy_name: ssh-strict
    protocol: SSH
    description: SSH with vault credentials only
    authentication_methods: [PASSWORD_VAULT, PUBKEY_VAULT]
    options:
      session:
        inactivity_timeout: 600
      trace:
        log_all_kbd: true

- name: RDP policy refusing unknown server certificates
  wallix.bastion.connection_policy:
    connection_policy_name: rdp-strict
    protocol: RDP
    authentication_methods: [PASSWORD_VAULT]
    options:
      server_cert:
        server_cert_check: "2"

- name: Remove a connection policy
  wallix.bastion.connection_policy:
    connection_policy_name: ssh-strict
    state: absent
"""

RETURN = r"""
connection_policy:
  description:
    - The connection policy as returned by the Bastion API after the change, including every
      option section with the Bastion defaults.
    - In check mode, the expected policy. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f6dbb76cf1460005056b66c8b
    connection_policy_name: ssh-strict
    protocol: SSH
    type: SSH
    description: SSH with vault credentials only
    authentication_methods: [PUBKEY_VAULT, PASSWORD_VAULT]
    is_default: false
    options:
      session:
        inactivity_timeout: 600
        allow_multi_channels: false
        force_shell_disconnection: false
        server_keepalive_type: none
        server_keepalive_interval: 0
      trace:
        log_all_kbd: true
        log_group_membership: false
    url: https://bastion.example.com/api/v3.12/connectionpolicies/1a0f6dbb76cf1460005056b66c8b
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the connection policy already existed and O(state=present)
  type: list
  elements: str
  sample: [options]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)


def options_contain(current, wanted):
    """True if every key of `wanted` is in `current` with the same value, recursively."""
    if isinstance(wanted, dict):
        return isinstance(current, dict) and all(
            k in current and options_contain(current[k], v) for k, v in wanted.items())
    if isinstance(wanted, bool) or isinstance(current, bool):
        # Python has True == 1; the Bastion does not.
        return type(wanted) is type(current) and wanted == current
    return wanted == current


def options_merge(current, wanted):
    """`current` updated with `wanted` recursively, as the Bastion merges a PUT."""
    if not isinstance(wanted, dict) or not isinstance(current, dict):
        return wanted
    merged = dict(current)
    for key, value in wanted.items():
        merged[key] = options_merge(current.get(key), value)
    return merged


class ConnectionPolicyResource(BastionResource):
    """Connection policies: options compared as a subset, protocol/type sent on creation only.

    The Bastion fills every option key it is not given with its default and merges the options
    of a PUT into the current ones, so only the keys the user set are compared and sent.
    Sending back the full options read from the API is avoided on purpose: it could write
    returned placeholders (such as proxy passwords) back.
    """

    def create(self, desired):
        if "type" not in desired and "protocol" in desired and self.client.api_version != "v3.8":
            desired = dict(desired, type=desired["protocol"])  # required by API v3.12
        return super(ConnectionPolicyResource, self).create(desired)

    def differences(self, current, desired):
        plain = dict((k, v) for k, v in desired.items() if k != "options")
        changes = super(ConnectionPolicyResource, self).differences(current, plain)
        if "options" in desired:
            if not options_contain(current.get("options"), desired["options"]):
                changes = sorted(changes + ["options"])
            # The object the Bastion will hold after the PUT, for check mode and the diff.
            desired["options"] = options_merge(current.get("options") or {}, desired["options"])
        return changes

    def update(self, current, desired):
        values = dict((f, current[f]) for f in ("connection_policy_name", "description", "authentication_methods")
                      if f in current)
        values.update((k, v) for k, v in desired.items() if k not in ("protocol", "type", "options"))
        if self.module.params.get("options") is not None:
            values["options"] = self.module.params["options"]
        self.client.call("PUT", self.object_path(current["id"]) + "?force=true", self.body(values))
        return self.normalize(self.client.get(self.object_path(current["id"])))


def main():
    module = BastionModule(
        argument_spec=dict(
            connection_policy_name=dict(type="str", required=True),
            protocol=dict(type="str"),
            type=dict(type="str"),
            description=dict(type="str"),
            authentication_methods=dict(type="list", elements="str"),
            options=dict(type="dict"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    resource = ConnectionPolicyResource(
        module,
        path="connectionpolicies",
        name_field="connection_policy_name",
        fields=("connection_policy_name", "protocol", "type", "description", "authentication_methods", "options"),
        set_fields=("authentication_methods",),
        result_key="connection_policy",
        required_on_create=("protocol",),
        create_only_fields=("protocol", "type"),
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
