#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: domain_account_credential_info
short_description: Get credentials of a global domain account from a WALLIX Bastion
version_added: 1.0.0
description:
  - Return the credential of one type, or every credential, of an account of a global domain.
  - Equivalent of the C(wallix-bastion_domain_account_credential) Terraform data source.
  - The Bastion masks passwords, private keys and passphrases; public keys are returned.
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
      - Name of the account. The module fails if it does not exist.
    type: str
    required: true
  type:
    description:
      - Type of the credential to return. Without it, all credentials of the account are returned.
    type: str
    choices: [password, ssh_key]
"""

EXAMPLES = r"""
- name: Get the SSH key of an account
  wallix.bastion.domain_account_credential_info:
    domain_name: corp
    account_name: administrator
    type: ssh_key
  register: result

- name: Show its public key
  ansible.builtin.debug:
    msg: "{{ result.domain_account_credentials[0].public_key }}"
  when: result.domain_account_credentials | length == 1
"""

RETURN = r"""
domain_account_credentials:
  description:
    - Matching credentials, as returned by the Bastion API. Empty when the account has no credential of O(type).
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f6dc11e1ed5c9005056b66c8b
      type: password
      password: "********"
      url: https://bastion.example.com/api/v3.12/domains/1a0f6d.../accounts/1a0f6d.../credentials/1a0f6dc11e1ed5c9005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, find_parent


def main():
    module = BastionModule(
        argument_spec=dict(
            domain_name=dict(type="str", required=True),
            account_name=dict(type="str", required=True),
            type=dict(type="str", choices=["password", "ssh_key"]),
        ),
        supports_check_mode=True,
    )
    params = module.params
    domain_id = find_parent(module, "domains", "domain_name", params["domain_name"], label="domain")
    account_id = find_parent(module, "domains/%s/accounts" % domain_id, "account_name", params["account_name"],
                             label="account")
    path = "domains/%s/accounts/%s/credentials" % (domain_id, account_id)
    try:
        # The API has no q= search on credentials: filter the listing.
        found = [c for c in module.client.get(path) or [] if params["type"] in (None, c.get("type"))]
        credentials = [module.client.get("%s/%s" % (path, c["id"])) or c for c in found]
        module.exit_json(changed=False, domain_account_credentials=credentials)
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)


if __name__ == "__main__":
    main()
