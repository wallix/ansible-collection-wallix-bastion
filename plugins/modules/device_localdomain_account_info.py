#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: device_localdomain_account_info
short_description: Get the accounts of a device local domain from a WALLIX Bastion
version_added: 1.0.0
description:
  - Return one account of a local domain of a device by name, or every account of the local domain.
  - Equivalent of the C(wallix-bastion_device_localdomain_account) Terraform data source.
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
  device_name:
    description:
      - Name of the device. The module fails if the device does not exist.
    type: str
    required: true
  domain_name:
    description:
      - Name of the local domain of the device. The module fails if the local domain does not exist.
    type: str
    required: true
  account_name:
    description:
      - Name of the account to return. Without it, all the accounts of the local domain are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one account
  wallix.bastion.device_localdomain_account_info:
    device_name: srv-linux-01
    domain_name: local
    account_name: root
  register: result

- name: List the accounts of a local domain
  wallix.bastion.device_localdomain_account_info:
    device_name: srv-linux-01
    domain_name: local
  register: all_accounts
"""

RETURN = r"""
accounts:
  description:
    - Matching accounts, as returned by the Bastion API. Secrets of their credentials are left out.
    - Empty when O(account_name) matches no account.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f6dbca5e15d2b005056b66c8b
      account_name: root
      account_login: root
      description: ""
      auto_change_password: true
      auto_change_ssh_key: true
      checkout_policy: default
      certificate_validity: null
      domain_password_change: false
      services: [SSH]
      credentials:
        - id: 1a0f6dbcf31a3cdb005056b66c8b
          type: password
      url: https://bastion.example.com/api/v3.12/devices/1a0f.../accounts/1a0f6dbca5e15d2b005056b66c8b
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
            device_name=dict(type="str", required=True),
            domain_name=dict(type="str", required=True),
            account_name=dict(type="str"),
        ),
        supports_check_mode=True,
    )
    device_id = find_parent(module, "devices", "device_name", module.params["device_name"], label="device")
    domain_id = find_parent(module, "devices/%s/localdomains" % device_id, "domain_name",
                            module.params["domain_name"], label="localdomain")
    run_info(module, path="devices/%s/localdomains/%s/accounts" % (device_id, domain_id),
             name_field="account_name", result_key="accounts", normalize=strip_credential_secrets)


if __name__ == "__main__":
    main()
