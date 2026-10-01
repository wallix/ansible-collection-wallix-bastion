#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: application_localdomain_account_info
short_description: Get the accounts of an application local domain from a WALLIX Bastion
version_added: 1.1.0
description:
  - Return one account of a local domain of an application by name, or every account of the local domain.
  - Equivalent of the C(wallix-bastion_application_localdomain_account) Terraform data source.
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
  application_name:
    description:
      - Name of the application. The module fails if the application does not exist.
    type: str
    required: true
  domain_name:
    description:
      - Name of the local domain of the application. The module fails if the local domain does not exist.
    type: str
    required: true
  account_name:
    description:
      - Name of the account to return. Without it, all the accounts of the local domain are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get an account of an application local domain
  wallix.bastion.application_localdomain_account_info:
    application_name: intranet
    domain_name: local
    account_name: admin
  register: result

- name: Show its login
  ansible.builtin.debug:
    msg: "{{ result.accounts[0].account_login }}"
"""

RETURN = r"""
accounts:
  description:
    - Matching accounts, as returned by the Bastion API, without the secrets of their credentials.
    - Empty when O(account_name) matches no account.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f7685d01633f8005056b66c8b
      account_name: admin
      account_login: admin@intranet.example.com
      description: ""
      auto_change_password: true
      checkout_policy: default
      certificate_validity: null
      can_edit_certificate_validity: false
      domain_password_change: false
      onboard_status: manual
      first_seen: null
      last_seen: null
      credentials:
        - id: 1a0f7685fba980fa005056b66c8b
          type: password
          url: https://bastion.example.com/api/v3.12/applications/1a0f.../credentials/1a0f7685fba980fa005056b66c8b
      url: https://bastion.example.com/api/v3.12/applications/1a0f.../accounts/1a0f7685d01633f8005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, find_parent, run_info

CREDENTIAL_SECRETS = ("password", "private_key", "passphrase")


def strip_credential_secrets(account):
    """The API returns masked secrets in credentials; leave them out of the result."""
    if account and isinstance(account.get("credentials"), list):
        account = dict(account, credentials=[
            {k: v for k, v in cred.items() if k not in CREDENTIAL_SECRETS} for cred in account["credentials"]])
    return account


def main():
    module = BastionModule(
        argument_spec=dict(
            application_name=dict(type="str", required=True),
            domain_name=dict(type="str", required=True),
            account_name=dict(type="str"),
        ),
        supports_check_mode=True,
    )
    application_id = find_parent(module, "applications", "application_name", module.params["application_name"],
                                 label="application")
    domain_id = find_parent(module, "applications/%s/localdomains" % application_id, "domain_name",
                            module.params["domain_name"], label="localdomain")
    run_info(module, path="applications/%s/localdomains/%s/accounts" % (application_id, domain_id),
             name_field="account_name", result_key="accounts", normalize=strip_credential_secrets)


if __name__ == "__main__":
    main()
