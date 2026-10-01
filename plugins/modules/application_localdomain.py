#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: application_localdomain
short_description: Manage local domains of an application on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete a local domain of an application on a WALLIX Bastion.
  - Equivalent of the C(wallix-bastion_application_localdomain) Terraform resource.
  - Accounts of the local domain are managed with M(wallix.bastion.application_localdomain_account).
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
      - Name of the application the local domain belongs to. The application must exist.
    type: str
    required: true
  domain_name:
    description:
      - Name of the local domain. Identifies the local domain in the application.
    type: str
    required: true
  description:
    description:
      - Description of the local domain.
    type: str
  admin_account:
    description:
      - Name of the account of this local domain used to change the passwords of the other accounts.
      - The Bastion only accepts it on an existing local domain whose account already exists, so it
        cannot be set when the local domain is created. Set it in a later task.
    type: str
  enable_password_change:
    description:
      - Whether the Bastion changes the passwords of the accounts of this local domain.
      - Requires O(password_change_policy) and O(password_change_plugin).
    type: bool
  password_change_policy:
    description:
      - Name of the password change policy, for example V(default).
    type: str
  password_change_plugin:
    description:
      - Name of the password change plugin.
    type: str
  password_change_plugin_parameters:
    description:
      - Parameters of the password change plugin.
      - Treated as a secret, see O(update_password).
    type: dict
  update_password:
    description:
      - V(on_create) sends O(password_change_plugin_parameters) only when the local domain is created.
      - V(always) sends it on every run, which then always reports a change.
    type: str
    choices: [always, on_create]
    default: on_create
  state:
    description:
      - Whether the local domain should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - With O(state=absent), a missing application is not an error.
"""

EXAMPLES = r"""
- name: Declare a local domain for the accounts of a web application
  wallix.bastion.application_localdomain:
    application_name: intranet
    domain_name: local
    description: Local accounts of the intranet

- name: Use the admin account of the local domain to rotate the passwords
  wallix.bastion.application_localdomain:
    application_name: intranet
    domain_name: local
    admin_account: admin

- name: Remove a local domain
  wallix.bastion.application_localdomain:
    application_name: intranet
    domain_name: local
    state: absent
"""

RETURN = r"""
localdomain:
  description:
    - The local domain as returned by the Bastion API after the change, without the secret options.
    - In check mode, the expected local domain. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f7675bcc1a98d005056b66c8b
    domain_name: local
    description: Local accounts of the intranet
    admin_account: null
    enable_password_change: false
    password_change_policy: null
    password_change_plugin: null
    ca_private_key: ""
    ca_public_key: ""
    url: https://bastion.example.com/api/v3.12/applications/1a0f7672f874efd5005056b66c8b/localdomains/1a0f7675bcc1a98d005056b66c8b
changed_fields:
  description:
    - Options that differed from the Bastion and were updated.
    - Contains O(password_change_plugin_parameters) when it was set with O(update_password=always).
  returned: when the local domain already existed and O(state=present)
  type: list
  elements: str
  sample: [description]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
    find_parent,
)

SECRETS = ("password_change_plugin_parameters",)


class ApplicationLocalDomainResource(BastionResource):
    def read(self):
        current = super(ApplicationLocalDomainResource, self).read()
        params = self.module.params
        # The API rejects admin_account in a POST; fail before writing anything, in check mode too.
        if current is None and params["state"] == "present" and params.get("admin_account") is not None:
            self.module.fail_json(msg="localdomain %s does not exist; admin_account cannot be set when "
                                      "creating it, set it once the account exists" % self.name)
        return current


def main():
    module = BastionModule(
        argument_spec=dict(
            application_name=dict(type="str", required=True),
            domain_name=dict(type="str", required=True),
            description=dict(type="str"),
            admin_account=dict(type="str"),
            enable_password_change=dict(type="bool", no_log=False),
            password_change_policy=dict(type="str", no_log=False),
            password_change_plugin=dict(type="str", no_log=False),
            password_change_plugin_parameters=dict(type="dict", no_log=True),
            update_password=dict(type="str", choices=["always", "on_create"], default="on_create", no_log=False),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    application_id = find_parent(module, "applications", "application_name", module.params["application_name"],
                                 label="application")
    if application_id is None:
        module.exit_json(changed=False, localdomain=None, diff=dict(before={}, after={}))
    resource = ApplicationLocalDomainResource(
        module,
        path="applications/%s/localdomains" % application_id,
        name_field="domain_name",
        fields=("domain_name", "description", "admin_account", "enable_password_change",
                "password_change_policy", "password_change_plugin") + SECRETS,
        result_key="localdomain",
        # The PUT keeps omitted fields, and refuses admin_account or password change settings sent with
        # enable_password_change=false: send only the requested fields.
        merge_on_update=False,
        secret_fields=SECRETS,
        update_secrets=module.params["update_password"] == "always",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
