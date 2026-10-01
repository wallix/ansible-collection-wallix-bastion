#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: connection_policy_info
short_description: Get connection policies from a WALLIX Bastion
version_added: 1.0.0
description:
  - Return one connection policy by name, or every connection policy of the Bastion.
  - Equivalent of the C(wallix-bastion_connection_policy) Terraform data source.
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
  connection_policy_name:
    description:
      - Name of the connection policy to return. Without it, all connection policies are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get the built-in SSH policy
  wallix.bastion.connection_policy_info:
    connection_policy_name: SSH
  register: result

- name: Show its inactivity timeout
  ansible.builtin.debug:
    msg: "{{ result.connection_policies[0].options.session.inactivity_timeout }}"

- name: List every connection policy
  wallix.bastion.connection_policy_info:
  register: all_policies
"""

RETURN = r"""
connection_policies:
  description:
    - Matching connection policies, as returned by the Bastion API, with every option section.
      Empty when O(connection_policy_name) matches no policy.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 19f463ca9a583634005056b66c8b
      connection_policy_name: SSH
      protocol: SSH
      type: SSH
      description: Default SSH connection policy
      authentication_methods: [PUBKEY_VAULT, PASSWORD_VAULT, PASSWORD_MAPPING, PASSWORD_INTERACTIVE]
      is_default: true
      options:
        session:
          inactivity_timeout: 0
          allow_multi_channels: false
      url: https://bastion.example.com/api/v3.12/connectionpolicies/19f463ca9a583634005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, run_info


def main():
    module = BastionModule(
        argument_spec=dict(connection_policy_name=dict(type="str")),
        supports_check_mode=True,
    )
    run_info(module, path="connectionpolicies", name_field="connection_policy_name",
             result_key="connection_policies")


if __name__ == "__main__":
    main()
