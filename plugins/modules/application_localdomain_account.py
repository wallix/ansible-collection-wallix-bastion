#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: application_localdomain_account
short_description: Manage accounts of an application local domain on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete an account of a local domain of an application on a WALLIX Bastion.
  - Equivalent of the C(wallix-bastion_application_localdomain_account) Terraform resource.
  - The password of the account is managed with M(wallix.bastion.application_localdomain_account_credential),
    unlike the Terraform resource which also takes it as its C(password) attribute.
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
      - Name of the local domain of the application the account belongs to. The local domain must exist.
    type: str
    required: true
  account_name:
    description:
      - Name of the account. Identifies the account in the local domain.
    type: str
    required: true
  account_login:
    description:
      - Login of the account on the application.
      - Required when the account does not exist yet and O(state=present).
    type: str
  description:
    description:
      - Description of the account.
    type: str
  auto_change_password:
    description:
      - Whether the Bastion changes the password of the account automatically.
      - The Bastion enables it when the account is created and this option is not set.
    type: bool
  checkout_policy:
    description:
      - Name of the checkout policy of the account.
      - The Bastion requires one, so V(default) is used when the account is created and
        this option is not set, as the Terraform provider does.
    type: str
  state:
    description:
      - Whether the account should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - With O(state=absent), a missing application or local domain is not an error.
"""

EXAMPLES = r"""
- name: Declare the admin account of a web application
  wallix.bastion.application_localdomain_account:
    application_name: intranet
    domain_name: local
    account_name: admin
    account_login: admin@intranet.example.com

- name: Stop rotating its password
  wallix.bastion.application_localdomain_account:
    application_name: intranet
    domain_name: local
    account_name: admin
    auto_change_password: false

- name: Remove an account
  wallix.bastion.application_localdomain_account:
    application_name: intranet
    domain_name: local
    account_name: admin
    state: absent
"""

RETURN = r"""
account:
  description:
    - The account as returned by the Bastion API after the change. Secrets of its credentials are left out.
    - In check mode, the expected account. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f7685d01633f8005056b66c8b
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
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the account already existed and O(state=present)
  type: list
  elements: str
  sample: [auto_change_password]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
    find_parent,
)

CREDENTIAL_SECRETS = ("password", "private_key", "passphrase")


def strip_credential_secrets(account):
    """The API returns masked secrets in credentials; leave them out of the result."""
    if account and isinstance(account.get("credentials"), list):
        account = dict(account, credentials=[
            {k: v for k, v in cred.items() if k not in CREDENTIAL_SECRETS} for cred in account["credentials"]])
    return account


class ApplicationLocalDomainAccountResource(BastionResource):
    def normalize(self, obj):
        return strip_credential_secrets(obj)

    def create(self, desired):
        if "checkout_policy" not in desired:
            desired = dict(desired, checkout_policy="default")
        return super(ApplicationLocalDomainAccountResource, self).create(desired)


def find_localdomain(module):
    """Id of the application and of its local domain; (None, None) when removing an orphan account."""
    application_id = find_parent(module, "applications", "application_name", module.params["application_name"],
                                 label="application")
    if application_id is None:
        return None, None
    domain_id = find_parent(module, "applications/%s/localdomains" % application_id, "domain_name",
                            module.params["domain_name"], label="localdomain")
    return application_id, domain_id


def main():
    module = BastionModule(
        argument_spec=dict(
            application_name=dict(type="str", required=True),
            domain_name=dict(type="str", required=True),
            account_name=dict(type="str", required=True),
            account_login=dict(type="str"),
            description=dict(type="str"),
            auto_change_password=dict(type="bool", no_log=False),
            checkout_policy=dict(type="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    application_id, domain_id = find_localdomain(module)
    if domain_id is None:
        module.exit_json(changed=False, account=None, diff=dict(before={}, after={}))
    resource = ApplicationLocalDomainAccountResource(
        module,
        path="applications/%s/localdomains/%s/accounts" % (application_id, domain_id),
        name_field="account_name",
        fields=("account_name", "account_login", "description", "auto_change_password", "checkout_policy"),
        result_key="account",
        required_on_create=("account_login",),
        update_query="force=true",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
