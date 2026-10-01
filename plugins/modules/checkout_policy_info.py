#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: checkout_policy_info
short_description: Get checkout policies from a WALLIX Bastion
version_added: 1.1.0
description:
  - Return one checkout policy by name, or every checkout policy of the Bastion.
  - Equivalent of the C(wallix-bastion_checkout_policy) Terraform data source.
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
  checkout_policy_name:
    description:
      - Name of the checkout policy to return. Without it, all checkout policies are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one checkout policy
  wallix.bastion.checkout_policy_info:
    checkout_policy_name: default
  register: result

- name: List every checkout policy
  wallix.bastion.checkout_policy_info:
  register: all_items
"""

RETURN = r"""
checkout_policies:
  description:
    - Matching checkout policies, as returned by the Bastion API. Empty when O(checkout_policy_name) matches no checkout policy.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 19f463ca941f0ca9005056b66c8b
      checkout_policy_name: default
      description: ''
      enable_lock: false
      duration: 0
      extension: 0
      max_duration: 0
      change_credentials_at_checkin: false
      url: https://bastion.example.com/api/v3.12/checkoutpolicies/19f463ca941f0ca9005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, run_info


def main():
    module = BastionModule(
        argument_spec=dict(checkout_policy_name=dict(type="str")),
        supports_check_mode=True,
    )
    run_info(module, path="checkoutpolicies", name_field="checkout_policy_name", result_key="checkout_policies")


if __name__ == "__main__":
    main()
