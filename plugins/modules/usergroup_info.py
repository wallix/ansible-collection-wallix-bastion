#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: usergroup_info
short_description: Get user groups from a WALLIX Bastion
version_added: 1.0.0
description:
  - Return one user group by name, or every user group of the Bastion.
  - Equivalent of the C(wallix-bastion_usergroup) Terraform data source.
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
      - Name of the user group to return. Without it, all user groups are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one user group
  wallix.bastion.usergroup_info:
    group_name: linux-admins
  register: result

- name: Show its members
  ansible.builtin.debug:
    var: result.usergroups[0].users

- name: List every user group
  wallix.bastion.usergroup_info:
  register: all_groups
"""

RETURN = r"""
usergroups:
  description:
    - Matching user groups, as returned by the Bastion API, restrictions without their ids.
    - Empty when O(group_name) matches no group.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f6dae63280cc2005056b66c8b
      group_name: linux-admins
      description: Administrators of the Linux servers
      timeframes: [allthetime]
      users: [john.doe]
      profile: null
      language: en
      email_list: ""
      restrictions: []
      url: https://bastion.example.com/api/v3.12/usergroups/1a0f6dae63280cc2005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, run_info


def normalize_usergroup(obj):
    """Drop the id and url the API gives each restriction, as wallix.bastion.usergroup does."""
    obj = dict(obj)
    if isinstance(obj.get("restrictions"), list):
        obj["restrictions"] = [{k: r.get(k) for k in ("action", "rules", "subprotocol")} for r in obj["restrictions"]]
    return obj


def main():
    module = BastionModule(
        argument_spec=dict(group_name=dict(type="str")),
        supports_check_mode=True,
    )
    run_info(module, path="usergroups", name_field="group_name", result_key="usergroups",
             normalize=normalize_usergroup)


if __name__ == "__main__":
    main()
