#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: application_localdomain_account_credential
short_description: Manage the password of an application local domain account on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete the password of an account of a local domain of an application
    on a WALLIX Bastion.
  - Equivalent of the C(wallix-bastion_application_localdomain_account_credential) Terraform resource.
  - Application accounts only have password credentials, at most one per account.
author:
  - WALLIX (@wallix)
extends_documentation_fragment:
  - wallix.bastion.connection
attributes:
  check_mode:
    description: Can run in check_mode and return changed status prediction without modifying target.
    support: full
  diff_mode:
    description: Will return details on what has changed (or possibly needs changing in check_mode), when in diff mode.
    support: full
options:
  application_name:
    description:
      - Name of the application. The application must exist.
    type: str
    required: true
  domain_name:
    description:
      - Name of the local domain of the application. The local domain must exist.
    type: str
    required: true
  account_name:
    description:
      - Name of the account of the local domain the credential belongs to. The account must exist.
    type: str
    required: true
  type:
    description:
      - Type of the credential. Identifies the credential of the account.
      - The Bastion only supports passwords for application accounts.
    type: str
    required: true
    choices: [password]
  password:
    description:
      - The password.
      - Required when the credential does not exist yet and O(state=present).
      - The Bastion never returns it, so it cannot be compared. See O(update_password).
    type: str
  update_password:
    description:
      - V(on_create) sends O(password) only when the credential is created.
      - V(always) sends it on every run, which then always reports a change. The credential
        is replaced in place.
    type: str
    choices: [always, on_create]
    default: on_create
  state:
    description:
      - Whether the credential should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - With O(state=absent), a missing application, local domain or account is not an error.
"""

EXAMPLES = r"""
- name: Set the password of the admin account of a web application
  wallix.bastion.application_localdomain_account_credential:
    application_name: intranet
    domain_name: local
    account_name: admin
    type: password
    password: "{{ vault_intranet_admin_password }}"

- name: Rotate the password on every run
  wallix.bastion.application_localdomain_account_credential:
    application_name: intranet
    domain_name: local
    account_name: admin
    type: password
    password: "{{ vault_intranet_admin_new_password }}"
    update_password: always

- name: Remove the password
  wallix.bastion.application_localdomain_account_credential:
    application_name: intranet
    domain_name: local
    account_name: admin
    type: password
    state: absent
"""

RETURN = r"""
credential:
  description:
    - The credential as returned by the Bastion API after the change, without the password.
    - In check mode, the expected credential. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f7685fba980fa005056b66c8b
    type: password
    url: https://bastion.example.com/api/v3.12/credentials/1a0f7685fba980fa005056b66c8b
changed_fields:
  description:
    - Options that were updated. Contains V(password) when it was set with O(update_password=always).
  returned: when the credential already existed and O(state=present)
  type: list
  elements: str
  sample: [password]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
    find_parent,
)

SECRETS = ("password",)


def find_account(module):
    """Credentials path of the account; None when removing an orphan credential."""
    params = module.params
    application_id = find_parent(module, "applications", "application_name", params["application_name"],
                                 label="application")
    if application_id is None:
        return None
    path = "applications/%s/localdomains" % application_id
    domain_id = find_parent(module, path, "domain_name", params["domain_name"], label="localdomain")
    if domain_id is None:
        return None
    path = "%s/%s/accounts" % (path, domain_id)
    account_id = find_parent(module, path, "account_name", params["account_name"], label="account")
    if account_id is None:
        return None
    return "%s/%s/credentials" % (path, account_id)


def main():
    module = BastionModule(
        argument_spec=dict(
            application_name=dict(type="str", required=True),
            domain_name=dict(type="str", required=True),
            account_name=dict(type="str", required=True),
            type=dict(type="str", required=True, choices=["password"]),
            password=dict(type="str", no_log=True),
            update_password=dict(type="str", choices=["always", "on_create"], default="on_create", no_log=False),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    path = find_account(module)
    if path is None:
        module.exit_json(changed=False, credential=None, diff=dict(before={}, after={}))
    resource = BastionResource(
        module,
        path=path,
        name_field="type",
        # The collection has no q= filter on type: list and match.
        search="list",
        # The PUT requires the type next to the password.
        fields=("type",) + SECRETS,
        result_key="credential",
        required_on_create=SECRETS,
        create_only_fields=("type",),
        secret_fields=SECRETS,
        update_secrets=module.params["update_password"] == "always",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
