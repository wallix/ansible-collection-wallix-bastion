#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: usergroup
short_description: Manage user groups on a WALLIX Bastion
version_added: 1.0.0
description:
  - Create, update or delete a user group on a WALLIX Bastion.
  - Equivalent of the C(wallix-bastion_usergroup) Terraform resource.
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
      - Name of the user group. Identifies the group on the Bastion.
    type: str
    required: true
  timeframes:
    description:
      - Names of the timeframes during which the members of the group can connect, for example V(allthetime).
        Order does not matter.
      - Required when the group does not exist yet and O(state=present).
    type: list
    elements: str
  description:
    description:
      - Description of the group.
    type: str
  profile:
    description:
      - Name of the profile given to the members of the group.
    type: str
  restrictions:
    description:
      - Session restrictions applied to the members of the group. Order does not matter.
      - When set, replaces all the restrictions of the group. Use V([]) to remove all restrictions.
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
  users:
    description:
      - Names of the users that belong to the group. Order does not matter.
      - When set, replaces all the members of the group. Use V([]) to remove every member.
      - Membership can also be managed from the user with M(wallix.bastion.user) O(wallix.bastion.user#module:groups);
        set it on one side only.
    type: list
    elements: str
  state:
    description:
      - Whether the group should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - The group is looked up by O(group_name), so it cannot be renamed with this module.
"""

EXAMPLES = r"""
- name: Ensure a group of Linux administrators exists
  wallix.bastion.usergroup:
    group_name: linux-admins
    description: Administrators of the Linux servers
    timeframes: [allthetime]
    users: [john.doe, jane.doe]
    restrictions:
      - action: kill
        rules: "rm -rf /"
        subprotocol: SSH_SHELL_SESSION

- name: Remove every member of a group
  wallix.bastion.usergroup:
    group_name: linux-admins
    users: []

- name: Remove a group
  wallix.bastion.usergroup:
    group_name: linux-admins
    state: absent
"""

RETURN = r"""
usergroup:
  description:
    - The user group as returned by the Bastion API after the change, restrictions without their ids.
    - In check mode, the expected group. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f6dae63280cc2005056b66c8b
    group_name: linux-admins
    description: Administrators of the Linux servers
    timeframes: [allthetime]
    users: [john.doe, jane.doe]
    profile: null
    language: en
    email_list: ""
    restrictions:
      - action: kill
        rules: "rm -rf /"
        subprotocol: SSH_SHELL_SESSION
    url: https://bastion.example.com/api/v3.12/usergroups/1a0f6dae63280cc2005056b66c8b
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the group already existed and O(state=present)
  type: list
  elements: str
  sample: [users]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)

RESTRICTION_FIELDS = ("action", "rules", "subprotocol")
SUBPROTOCOLS = ["SSH_SHELL_SESSION", "SSH_REMOTE_COMMAND", "SSH_SCP_UP", "SSH_SCP_DOWN",
                "SFTP_SESSION", "RLOGIN", "TELNET", "RDP"]


def normalize_usergroup(obj):
    """Drop the id and url the API gives each restriction, so restrictions compare with the options."""
    if obj is None:
        return None
    obj = dict(obj)
    if isinstance(obj.get("restrictions"), list):
        obj["restrictions"] = [{k: r.get(k) for k in RESTRICTION_FIELDS} for r in obj["restrictions"]]
    return obj


class UserGroupResource(BastionResource):

    def normalize(self, obj):
        return normalize_usergroup(obj)


def main():
    module = BastionModule(
        argument_spec=dict(
            group_name=dict(type="str", required=True),
            timeframes=dict(type="list", elements="str"),
            description=dict(type="str"),
            profile=dict(type="str"),
            restrictions=dict(
                type="list",
                elements="dict",
                options=dict(
                    action=dict(type="str", required=True, choices=["kill", "notify"]),
                    rules=dict(type="str", required=True),
                    subprotocol=dict(type="str", required=True, choices=SUBPROTOCOLS),
                ),
            ),
            users=dict(type="list", elements="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    resource = UserGroupResource(
        module,
        path="usergroups",
        name_field="group_name",
        fields=("group_name", "timeframes", "description", "profile", "restrictions", "users"),
        set_fields=("timeframes", "restrictions", "users"),
        result_key="usergroup",
        required_on_create=("timeframes",),
        update_query="force=true",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
