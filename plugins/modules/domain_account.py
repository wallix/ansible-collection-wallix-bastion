#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: domain_account
short_description: Manage accounts of global domains on a WALLIX Bastion
version_added: 1.0.0
description:
  - Create, update or delete an account of a global domain on a WALLIX Bastion.
  - Equivalent of the C(wallix-bastion_domain_account) Terraform resource.
  - The credentials of the account are managed with M(wallix.bastion.domain_account_credential).
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
  domain_name:
    description:
      - Name of the global domain the account belongs to (see M(wallix.bastion.domain)).
      - The domain must exist, unless O(state=absent).
    type: str
    required: true
  account_name:
    description:
      - Name of the account. Identifies the account in the domain.
    type: str
    required: true
  account_login:
    description:
      - Login of the account on the targets.
      - Required when the account does not exist yet and O(state=present).
    type: str
  description:
    description:
      - Description of the account.
    type: str
  auto_change_password:
    description:
      - Whether the Bastion changes the password of the account automatically.
      - When the account is created without it, the Bastion enables it.
    type: bool
  auto_change_ssh_key:
    description:
      - Whether the Bastion changes the SSH key of the account automatically.
      - When the account is created without it, the Bastion enables it.
    type: bool
  checkout_policy:
    description:
      - Name of the checkout policy of the account.
      - When the account is created without it, V(default) is used, like the Terraform provider does.
    type: str
  certificate_validity:
    description:
      - Validity of the SSH certificates issued for the account, for example V(+2h) or V(+53w20d).
      - Needs a domain with an SSH certificate authority (O(wallix.bastion.domain#module:ca_private_key)).
    type: str
  resources:
    description:
      - Targets the account can be used on, as V(<device>:<service>) or V(<application>:APP). Order does not matter.
      - The service or application must be associated with the domain.
      - When set, replaces all the resources of the account. Use V([]) to remove them all.
    type: list
    elements: str
  state:
    description:
      - Whether the account should exist.
      - Deleting an account deletes its credentials.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
"""

EXAMPLES = r"""
- name: Declare a domain account
  wallix.bastion.domain_account:
    domain_name: corp
    account_name: administrator
    account_login: Administrator
    description: Domain administrator
    auto_change_password: false

- name: Allow the account on a device service
  wallix.bastion.domain_account:
    domain_name: corp
    account_name: administrator
    resources:
      - srv-win-01:RDP

- name: Remove the account
  wallix.bastion.domain_account:
    domain_name: corp
    account_name: administrator
    state: absent
"""

RETURN = r"""
domain_account:
  description:
    - The account as returned by the Bastion API after the change.
    - In check mode, the expected account. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f6dbf61a04925005056b66c8b
    account_name: administrator
    account_login: Administrator
    description: Domain administrator
    onboard_status: manual
    first_seen: null
    last_seen: null
    credentials:
      - id: 1a0f6dc11e1ed5c9005056b66c8b
        type: password
        password: "********"
    domain_password_change: false
    auto_change_password: false
    auto_change_ssh_key: true
    checkout_policy: default
    resources: [srv-win-01:RDP]
    certificate_validity: null
    can_edit_certificate_validity: false
    url: https://bastion.example.com/api/v3.12/domains/1a0f6dbf308b89e1005056b66c8b/accounts/1a0f6dbf61a04925005056b66c8b
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the account already existed and O(state=present)
  type: list
  elements: str
  sample: [description, resources]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
    find_parent,
)


class DomainAccountResource(BastionResource):
    def create(self, desired):
        # The API requires checkout_policy; the provider defaults it to "default".
        values = dict(desired)
        values.setdefault("checkout_policy", "default")
        return super(DomainAccountResource, self).create(values)


def main():
    module = BastionModule(
        argument_spec=dict(
            domain_name=dict(type="str", required=True),
            account_name=dict(type="str", required=True),
            account_login=dict(type="str"),
            description=dict(type="str"),
            auto_change_password=dict(type="bool", no_log=False),
            auto_change_ssh_key=dict(type="bool", no_log=False),
            checkout_policy=dict(type="str"),
            certificate_validity=dict(type="str"),
            resources=dict(type="list", elements="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    bad = [r for r in module.params["resources"] or [] if len(r.split(":")) != 2]
    if bad:
        module.fail_json(msg="resources must be <device>:<service> or <application>:APP, got %s" % ", ".join(bad))

    domain_id = find_parent(module, "domains", "domain_name", module.params["domain_name"], label="domain")
    if domain_id is None:
        module.exit_json(changed=False, domain_account=None, diff=dict(before={}, after={}))
    resource = DomainAccountResource(
        module,
        path="domains/%s/accounts" % domain_id,
        name_field="account_name",
        fields=("account_name", "account_login", "description", "auto_change_password", "auto_change_ssh_key",
                "checkout_policy", "certificate_validity", "resources"),
        set_fields=("resources",),
        result_key="domain_account",
        required_on_create=("account_login",),
        merge_on_update=False,
        update_query="force=true",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
