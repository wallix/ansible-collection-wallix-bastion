#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: passwordchangepolicy_info
short_description: Get password change policies from a WALLIX Bastion
version_added: 1.1.0
description:
  - Return one password change policy by name, or every password change policy of the Bastion.
  - Equivalent of the C(wallix-bastion_passwordchangepolicy) Terraform data source.
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
  password_change_policy_name:
    description:
      - Name of the password change policy to return. Without it, all password change policies are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one password change policy
  wallix.bastion.passwordchangepolicy_info:
    password_change_policy_name: default
  register: result

- name: List every password change policy
  wallix.bastion.passwordchangepolicy_info:
  register: all_items
"""

RETURN = r"""
passwordchangepolicies:
  description:
    - Matching password change policies, as returned by the Bastion API. Empty when O(password_change_policy_name) matches no password change policy.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 19f463ca94af4841005056b66c8b
      password_change_policy_name: default
      description: Default credential change policy
      password_length: 16
      special_chars: 1
      lower_chars: 1
      upper_chars: 1
      digit_chars: 1
      exclude_chars: null
      ssh_key_type: RSA
      ssh_key_size: 4096
      change_period: ''
      url: https://bastion.example.com/api/v3.12/passwordchangepolicies/19f463ca94af4841005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, run_info


def main():
    module = BastionModule(
        argument_spec=dict(password_change_policy_name=dict(type="str")),
        supports_check_mode=True,
    )
    run_info(module, path="passwordchangepolicies", name_field="password_change_policy_name", result_key="passwordchangepolicies")


if __name__ == "__main__":
    main()
