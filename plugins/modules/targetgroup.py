#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: targetgroup
short_description: Manage target groups on a WALLIX Bastion
version_added: 1.0.0
description:
  - Create, update or delete a target group on a WALLIX Bastion.
  - A target group lists the accounts, devices and services that sessions and password
    retrieval can use; an authorization (M(wallix.bastion.authorization)) grants a user group access to it.
  - Equivalent of the C(wallix-bastion_targetgroup) Terraform resource.
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
  group_name:
    description:
      - Name of the target group. Identifies the group on the Bastion.
    type: str
    required: true
  description:
    description:
      - Description of the target group.
    type: str
  password_retrieval_accounts:
    description:
      - Accounts whose password or key members of authorized groups can check out. Order does not matter.
      - When set, replaces all the password retrieval accounts of the group. Use V([]) to remove them all.
      - With O(password_retrieval_accounts[].domain_type=global), leave O(password_retrieval_accounts[].device)
        and O(password_retrieval_accounts[].application) unset. With V(local), set one of them.
    type: list
    elements: dict
    suboptions:
      account:
        description: Name of the account.
        type: str
        required: true
      domain:
        description: Name of the domain of the account.
        type: str
        required: true
      domain_type:
        description: Whether O(password_retrieval_accounts[].domain) is a global domain or a local domain of a device or application.
        type: str
        required: true
        choices: [local, global]
      device:
        description: Device of the local domain.
        type: str
      application:
        description: Application of the local domain.
        type: str
  restrictions:
    description:
      - Session restrictions applied on the targets of the group. Order does not matter.
      - When set, replaces all the restrictions of the group. Use V([]) to remove them all.
    type: list
    elements: dict
    suboptions:
      action:
        description: What to do when the rule matches.
        type: str
        required: true
        choices: [kill, notify]
      rules:
        description: Regular expression matched against the session traffic.
        type: str
        required: true
      subprotocol:
        description: Subprotocol the rule applies to.
        type: str
        required: true
        choices: [SSH_SHELL_SESSION, SSH_REMOTE_COMMAND, SSH_SCP_UP, SSH_SCP_DOWN, SFTP_SESSION, RLOGIN, TELNET, RDP]
  session_accounts:
    description:
      - Accounts that sessions can be opened with, on a device service or an application. Order does not matter.
      - When set, replaces all the session accounts of the group. Use V([]) to remove them all.
      - Set either both O(session_accounts[].device) and O(session_accounts[].service), or O(session_accounts[].application).
    type: list
    elements: dict
    suboptions:
      account:
        description: Name of the account.
        type: str
        required: true
      domain:
        description: Name of the domain of the account.
        type: str
        required: true
      domain_type:
        description: Whether O(session_accounts[].domain) is a global domain or a local domain.
        type: str
        required: true
        choices: [local, global]
      device:
        description: Name of the device.
        type: str
      service:
        description: Name of the service of the device.
        type: str
      application:
        description: Name of the application.
        type: str
  session_account_mappings:
    description:
      - Device services or applications users connect to with their own account (account mapping). Order does not matter.
      - When set, replaces all the account mappings of the group. Use V([]) to remove them all.
    type: list
    elements: dict
    suboptions:
      device:
        description: Name of the device. Requires O(session_account_mappings[].service).
        type: str
      service:
        description: Name of the service of the device. Requires O(session_account_mappings[].device).
        type: str
      application:
        description: Name of the application. Mutually exclusive with the device and service.
        type: str
  session_interactive_logins:
    description:
      - Device services or applications users connect to by typing an account at login (interactive login).
        Order does not matter.
      - When set, replaces all the interactive logins of the group. Use V([]) to remove them all.
    type: list
    elements: dict
    suboptions:
      device:
        description: Name of the device. Requires O(session_interactive_logins[].service).
        type: str
      service:
        description: Name of the service of the device. Requires O(session_interactive_logins[].device).
        type: str
      application:
        description: Name of the application. Mutually exclusive with the device and service.
        type: str
  session_scenario_accounts:
    description:
      - Accounts that session scenarios (connection scripts) can use. Order does not matter.
      - When set, replaces all the scenario accounts of the group. Use V([]) to remove them all.
      - With O(session_scenario_accounts[].domain_type=global), leave O(session_scenario_accounts[].device)
        and O(session_scenario_accounts[].application) unset. With V(local), set one of them.
    type: list
    elements: dict
    suboptions:
      account:
        description: Name of the account.
        type: str
        required: true
      domain:
        description: Name of the domain of the account.
        type: str
        required: true
      domain_type:
        description: Whether O(session_scenario_accounts[].domain) is a global domain or a local domain.
        type: str
        required: true
        choices: [local, global]
      device:
        description: Device of the local domain.
        type: str
      application:
        description: Application of the local domain.
        type: str
  state:
    description:
      - Whether the target group should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - The group is looked up by O(group_name), so it cannot be renamed with this module.
  - The accounts, devices, services and domains referenced must exist; the Bastion rejects the change otherwise.
"""

EXAMPLES = r"""
- name: Give access to the SSH service of a Linux server with a local and a global account
  wallix.bastion.targetgroup:
    group_name: linux-servers
    description: Linux servers
    session_accounts:
      - account: root
        domain: local
        domain_type: local
        device: srv-linux-01
        service: SSH
      - account: admin
        domain: corp.example.com
        domain_type: global
        device: srv-linux-01
        service: SSH
    session_interactive_logins:
      - device: srv-linux-01
        service: SSH
    password_retrieval_accounts:
      - account: root
        domain: local
        domain_type: local
        device: srv-linux-01
    restrictions:
      - action: kill
        rules: "rm -rf /"
        subprotocol: SSH_SHELL_SESSION

- name: Remove every interactive login of the group, keep the rest
  wallix.bastion.targetgroup:
    group_name: linux-servers
    session_interactive_logins: []

- name: Remove a target group
  wallix.bastion.targetgroup:
    group_name: linux-servers
    state: absent
"""

RETURN = r"""
targetgroup:
  description:
    - The target group after the change, with the session and password retrieval lists flattened as in the
      module options and their items reduced to the fields that are set.
    - In check mode, the expected group. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f6e96bbce3423005056b66c8b
    group_name: linux-servers
    description: Linux servers
    password_retrieval_accounts:
      - account: root
        domain: local
        domain_type: local
        device: srv-linux-01
    restrictions:
      - action: kill
        rules: "rm -rf /"
        subprotocol: SSH_SHELL_SESSION
    session_accounts:
      - account: root
        domain: local
        domain_type: local
        device: srv-linux-01
        service: SSH
    session_account_mappings: []
    session_interactive_logins:
      - device: srv-linux-01
        service: SSH
    session_scenario_accounts: []
    url: https://bastion.example.com/api/v3.12/targetgroups/1a0f6e96bbce3423005056b66c8b
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the group already existed and O(state=present)
  type: list
  elements: str
  sample: [session_accounts]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)

SUBPROTOCOLS = ["SSH_SHELL_SESSION", "SSH_REMOTE_COMMAND", "SSH_SCP_UP", "SSH_SCP_DOWN",
                "SFTP_SESSION", "RLOGIN", "TELNET", "RDP"]

# Module option -> (API object, API list, item fields). The API nests these lists, the module
# flattens them as the provider does.
LISTS = {
    "password_retrieval_accounts": ("password_retrieval", "accounts",
                                    ("account", "domain", "domain_type", "device", "application")),
    "restrictions": (None, "restrictions", ("action", "rules", "subprotocol")),
    "session_accounts": ("session", "accounts",
                         ("account", "domain", "domain_type", "device", "service", "application")),
    "session_account_mappings": ("session", "account_mappings", ("device", "service", "application")),
    "session_interactive_logins": ("session", "interactive_logins", ("device", "service", "application")),
    "session_scenario_accounts": ("session", "scenario_accounts",
                                  ("account", "domain", "domain_type", "device", "application")),
}


def clean_items(items, keys):
    """Keep the item fields the module knows and that are set: the API adds ids, urls,
    service_protocol and nulls, the options leave unset fields as None."""
    return [{k: item[k] for k in keys if item.get(k) not in (None, "")} for item in items]


def normalize_targetgroup(obj):
    """Flatten an API target group into the shape of the module options."""
    if obj is None:
        return None
    result = {k: obj.get(k) for k in ("id", "group_name", "description", "url") if k in obj}
    for option, (parent, key, keys) in LISTS.items():
        container = (obj.get(parent) or {}) if parent else obj
        result[option] = clean_items(container.get(key) or [], keys)
    return result


def check_item(option, item):
    """The provider's consistency checks, so a bad item fails before any API call."""
    def has(key):
        return bool(item.get(key))

    domain_type = item.get("domain_type")
    if option in ("password_retrieval_accounts", "session_scenario_accounts"):
        if domain_type == "global" and (has("device") or has("application")):
            return "device and application must be unset with domain_type=global"
        if domain_type == "local" and not (has("device") or has("application")):
            return "device or application must be set with domain_type=local"
        if has("device") and has("application"):
            return "device and application are mutually exclusive"
        return None
    if option == "session_accounts" and not ((has("device") and has("service")) or has("application")):
        return "device and service, or application, must be set"
    if has("application") and (has("device") or has("service")):
        return "application is mutually exclusive with device and service"
    if has("device") != has("service"):
        return "device and service must be set together"
    return None


class TargetGroupResource(BastionResource):

    def desired(self):
        values = super(TargetGroupResource, self).desired()
        for option in LISTS:
            if option in values:
                values[option] = clean_items(values[option], LISTS[option][2])
        return values

    def normalize(self, obj):
        return normalize_targetgroup(obj)

    def body(self, values):
        body = {}
        for field, value in values.items():
            if field not in LISTS:
                body[field] = value
                continue
            parent, key = LISTS[field][:2]
            if parent:
                body.setdefault(parent, {})[key] = value
            else:
                body[key] = value
        return body


def item_spec(keys, required=("account", "domain", "domain_type")):
    spec = {}
    for key in keys:
        spec[key] = dict(type="str", required=key in required)
        if key == "domain_type":
            spec[key]["choices"] = ["local", "global"]
    return spec


def main():
    module = BastionModule(
        argument_spec=dict(
            group_name=dict(type="str", required=True),
            description=dict(type="str"),
            password_retrieval_accounts=dict(
                type="list", elements="dict", no_log=False,
                options=item_spec(LISTS["password_retrieval_accounts"][2])),
            restrictions=dict(
                type="list",
                elements="dict",
                options=dict(
                    action=dict(type="str", required=True, choices=["kill", "notify"]),
                    rules=dict(type="str", required=True),
                    subprotocol=dict(type="str", required=True, choices=SUBPROTOCOLS),
                ),
            ),
            session_accounts=dict(type="list", elements="dict", options=item_spec(LISTS["session_accounts"][2])),
            session_account_mappings=dict(
                type="list", elements="dict", options=item_spec(LISTS["session_account_mappings"][2])),
            session_interactive_logins=dict(
                type="list", elements="dict", options=item_spec(LISTS["session_interactive_logins"][2])),
            session_scenario_accounts=dict(
                type="list", elements="dict", options=item_spec(LISTS["session_scenario_accounts"][2])),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    for option in LISTS:
        for item in module.params[option] or []:
            error = check_item(option, item)
            if error:
                module.fail_json(msg="bad %s item %s: %s" % (
                    option, dict((k, v) for k, v in item.items() if v is not None), error))

    resource = TargetGroupResource(
        module,
        path="targetgroups",
        name_field="group_name",
        fields=("group_name", "description") + tuple(LISTS),
        set_fields=tuple(LISTS),
        result_key="targetgroup",
        # With force=true the API replaces the lists it gets (even with []) and keeps the
        # fields, and the session sub-lists, it does not get; without it, it appends.
        merge_on_update=False,
        update_query="force=true",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
