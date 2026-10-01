#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: local_password_policy_info
short_description: Get local password policies from a WALLIX Bastion
version_added: 1.1.0
description:
  - Return one local password policy by name, or every local password policy of the Bastion.
  - Local password policies set the rules for the passwords of local Bastion users. This collection only reads them.
  - Equivalent of the C(wallix-bastion_local_password_policy) Terraform data source.
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
  password_policy_name:
    description:
      - Name of the local password policy to return. Without it, all local password policies are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one local password policy
  wallix.bastion.local_password_policy_info:
    password_policy_name: default
  register: result

- name: List every local password policy
  wallix.bastion.local_password_policy_info:
  register: all_items
"""

RETURN = r"""
local_password_policies:
  description:
    - Matching local password policies, as returned by the Bastion API. Empty when O(password_policy_name) matches no local password policy.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 19f463ca92f2cd9e005056b66c8b
      password_policy_name: default
      password_expiration: 365
      password_warning_days: 20
      password_min_length: 12
      password_min_lower_chars: 1
      password_min_upper_chars: 1
      password_min_digit_chars: 1
      password_min_special_chars: 1
      last_passwords_to_reject: 4
      allow_same_user_and_password: false
      forbidden_passwords: [password, admin, '123456']
      max_auth_failures: 5
      ssh_rsa_min_length: 4096
      ssh_key_algos_allowed: [ecdsa-sha2-nistp256, ssh-ed25519, ssh-rsa]
      url: https://bastion.example.com/api/v3.12/localpasswordpolicies/19f463ca92f2cd9e005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, run_info


def main():
    module = BastionModule(
        argument_spec=dict(password_policy_name=dict(type="str")),
        supports_check_mode=True,
    )
    run_info(module, path="localpasswordpolicies", name_field="password_policy_name", result_key="local_password_policies")


if __name__ == "__main__":
    main()
