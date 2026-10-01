#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: application_localdomain_account_credential_info
short_description: Get the credentials of an application local domain account from a WALLIX Bastion
version_added: 1.1.0
description:
  - Return the credentials of an account of a local domain of an application, without their secrets.
  - Equivalent of the C(wallix-bastion_application_localdomain_account_credential) Terraform data source.
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
      - Name of the account. The module fails if the account does not exist.
    type: str
    required: true
  type:
    description:
      - Type of the credential to return. Without it, all the credentials of the account are returned.
    type: str
    choices: [password]
"""

EXAMPLES = r"""
- name: Check that the admin account of a web application has a password
  wallix.bastion.application_localdomain_account_credential_info:
    application_name: intranet
    domain_name: local
    account_name: admin
  register: result

- name: Fail if it has none
  ansible.builtin.assert:
    that: result.credentials | length == 1
"""

RETURN = r"""
credentials:
  description:
    - Matching credentials, as returned by the Bastion API, without their secrets.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f7685fba980fa005056b66c8b
      type: password
      url: https://bastion.example.com/api/v3.12/credentials/1a0f7685fba980fa005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, find_parent

SECRETS = ("password", "private_key", "passphrase")


def main():
    module = BastionModule(
        argument_spec=dict(
            application_name=dict(type="str", required=True),
            domain_name=dict(type="str", required=True),
            account_name=dict(type="str", required=True),
            type=dict(type="str", choices=["password"]),
        ),
        supports_check_mode=True,
    )
    params = module.params
    application_id = find_parent(module, "applications", "application_name", params["application_name"],
                                 label="application")
    path = "applications/%s/localdomains" % application_id
    domain_id = find_parent(module, path, "domain_name", params["domain_name"], label="localdomain")
    path = "%s/%s/accounts" % (path, domain_id)
    account_id = find_parent(module, path, "account_name", params["account_name"], label="account")
    path = "%s/%s/credentials" % (path, account_id)
    try:
        # The collection has no q= filter on type: list and match.
        found = [c for c in module.client.get(path) or [] if not params["type"] or c.get("type") == params["type"]]
        credentials = [module.client.get("%s/%s" % (path, c["id"])) or c for c in found]
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)
    module.exit_json(changed=False, credentials=[
        {k: v for k, v in c.items() if k not in SECRETS} for c in credentials])


if __name__ == "__main__":
    main()
