#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: domain_account_info
short_description: Get accounts of a global domain from a WALLIX Bastion
version_added: 1.0.0
description:
  - Return one account of a global domain by name, or every account of the domain.
  - Equivalent of the C(wallix-bastion_domain_account) Terraform data source.
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
  domain_name:
    description:
      - Name of the global domain. The module fails if it does not exist.
    type: str
    required: true
  account_name:
    description:
      - Name of the account to return. Without it, all accounts of the domain are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one domain account
  wallix.bastion.domain_account_info:
    domain_name: corp
    account_name: administrator
  register: result

- name: List the accounts of a domain
  wallix.bastion.domain_account_info:
    domain_name: corp
  register: all_accounts
"""

RETURN = r"""
domain_accounts:
  description:
    - Matching accounts, as returned by the Bastion API. Empty when O(account_name) matches no account.
    - Secrets in C(credentials) are masked by the Bastion.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f6dbf61a04925005056b66c8b
      account_name: administrator
      account_login: Administrator
      description: Domain administrator
      onboard_status: manual
      first_seen: null
      last_seen: null
      credentials: []
      domain_password_change: false
      auto_change_password: true
      auto_change_ssh_key: true
      checkout_policy: default
      resources: []
      certificate_validity: null
      can_edit_certificate_validity: false
      url: https://bastion.example.com/api/v3.12/domains/1a0f6dbf308b89e1005056b66c8b/accounts/1a0f6dbf61a04925005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, find_parent, run_info


def main():
    module = BastionModule(
        argument_spec=dict(
            domain_name=dict(type="str", required=True),
            account_name=dict(type="str"),
        ),
        supports_check_mode=True,
    )
    domain_id = find_parent(module, "domains", "domain_name", module.params["domain_name"], label="domain")
    run_info(module, path="domains/%s/accounts" % domain_id, name_field="account_name", result_key="domain_accounts")


if __name__ == "__main__":
    main()
