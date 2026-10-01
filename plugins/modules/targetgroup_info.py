#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: targetgroup_info
short_description: Get target groups from a WALLIX Bastion
version_added: 1.0.0
description:
  - Return one target group by name, or every target group of the Bastion.
  - Equivalent of the C(wallix-bastion_targetgroup) Terraform data source.
author:
  - WALLIX (@wallix)
extends_documentation_fragment:
  - wallix.bastion.connection
attributes:
  check_mode:
    description: Can run in check_mode and return changed status prediction without modifying target.
    support: full
    details: This module never changes anything.
  diff_mode:
    description: Will return details on what has changed (or possibly needs changing in check_mode), when in diff mode.
    support: none
options:
  group_name:
    description:
      - Name of the target group to return. Without it, all target groups are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one target group
  wallix.bastion.targetgroup_info:
    group_name: linux-servers
  register: result

- name: Show its session accounts
  ansible.builtin.debug:
    var: result.targetgroups[0].session_accounts

- name: List every target group
  wallix.bastion.targetgroup_info:
  register: all_groups
"""

RETURN = r"""
targetgroups:
  description:
    - Matching target groups, in the shape of the M(wallix.bastion.targetgroup) options, with the session and password
      retrieval lists flattened and items reduced to the fields that are set.
    - Empty when O(group_name) matches no group.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f6e96bbce3423005056b66c8b
      group_name: linux-servers
      description: Linux servers
      password_retrieval_accounts: []
      restrictions: []
      session_accounts:
        - account: root
          domain: local
          domain_type: local
          device: srv-linux-01
          service: SSH
      session_account_mappings: []
      session_interactive_logins: []
      session_scenario_accounts: []
      url: https://bastion.example.com/api/v3.12/targetgroups/1a0f6e96bbce3423005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, run_info

# Same flattening as wallix.bastion.targetgroup.
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


def normalize_targetgroup(obj):
    result = {k: obj.get(k) for k in ("id", "group_name", "description", "url") if k in obj}
    for option, (parent, key, keys) in LISTS.items():
        container = (obj.get(parent) or {}) if parent else obj
        result[option] = [{k: item[k] for k in keys if item.get(k) not in (None, "")}
                          for item in container.get(key) or []]
    return result


def main():
    module = BastionModule(
        argument_spec=dict(group_name=dict(type="str")),
        supports_check_mode=True,
    )
    run_info(module, path="targetgroups", name_field="group_name", result_key="targetgroups",
             normalize=normalize_targetgroup)


if __name__ == "__main__":
    main()
