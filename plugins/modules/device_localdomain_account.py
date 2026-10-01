#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: device_localdomain_account
short_description: Manage accounts of a device local domain on a WALLIX Bastion
version_added: 1.0.0
description:
  - Create, update or delete an account of a local domain of a device on a WALLIX Bastion.
  - Equivalent of the C(wallix-bastion_device_localdomain_account) Terraform resource.
  - Passwords and SSH keys of the account are managed with
    M(wallix.bastion.device_localdomain_account_credential).
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
  device_name:
    description:
      - Name of the device. The device must exist.
    type: str
    required: true
  domain_name:
    description:
      - Name of the local domain of the device the account belongs to. The local domain must exist.
    type: str
    required: true
  account_name:
    description:
      - Name of the account. Identifies the account in the local domain.
    type: str
    required: true
  account_login:
    description:
      - Login of the account on the device.
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
  auto_change_ssh_key:
    description:
      - Whether the Bastion changes the SSH key of the account automatically.
      - The Bastion enables it when the account is created and this option is not set.
    type: bool
  checkout_policy:
    description:
      - Name of the checkout policy of the account.
      - The Bastion requires one, so V(default) is used when the account is created and
        this option is not set, as the Terraform provider does.
    type: str
  certificate_validity:
    description:
      - Validity of the SSH certificates generated for the account, for example V(+1w2d).
    type: str
  services:
    description:
      - Names of the services of the device this account can be used on. Order does not matter.
      - When set, replaces all the services of the account. Use V([]) to remove them all.
    type: list
    elements: str
  state:
    description:
      - Whether the account should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - With O(state=absent), a missing device or local domain is not an error.
"""

EXAMPLES = r"""
- name: Declare the root account of a server
  wallix.bastion.device_localdomain_account:
    device_name: srv-linux-01
    domain_name: local
    account_name: root
    account_login: root
    services: [SSH]

- name: Stop rotating its password
  wallix.bastion.device_localdomain_account:
    device_name: srv-linux-01
    domain_name: local
    account_name: root
    auto_change_password: false

- name: Remove an account
  wallix.bastion.device_localdomain_account:
    device_name: srv-linux-01
    domain_name: local
    account_name: root
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
    id: 1a0f6dbca5e15d2b005056b66c8b
    account_name: root
    account_login: root
    description: ""
    auto_change_password: true
    auto_change_ssh_key: true
    checkout_policy: default
    certificate_validity: null
    can_edit_certificate_validity: true
    domain_password_change: false
    onboard_status: manual
    services: [SSH]
    credentials:
      - id: 1a0f6dbcf31a3cdb005056b66c8b
        type: password
        url: https://bastion.example.com/api/v3.12/devices/1a0f.../credentials/1a0f6dbcf31a3cdb005056b66c8b
    url: https://bastion.example.com/api/v3.12/devices/1a0f.../accounts/1a0f6dbca5e15d2b005056b66c8b
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


class DeviceLocalDomainAccountResource(BastionResource):
    def normalize(self, obj):
        return strip_credential_secrets(obj)

    def body(self, values):
        # The API rejects null values (certificate_validity is null until set).
        return {k: v for k, v in values.items() if v is not None}

    def create(self, desired):
        if "checkout_policy" not in desired:
            desired = dict(desired, checkout_policy="default")
        return super(DeviceLocalDomainAccountResource, self).create(desired)


def find_localdomain(module):
    """Id of the device and of its local domain; (None, None) when removing an orphan account."""
    device_id = find_parent(module, "devices", "device_name", module.params["device_name"], label="device")
    if device_id is None:
        return None, None
    domain_id = find_parent(module, "devices/%s/localdomains" % device_id, "domain_name",
                            module.params["domain_name"], label="localdomain")
    return device_id, domain_id


def main():
    module = BastionModule(
        argument_spec=dict(
            device_name=dict(type="str", required=True),
            domain_name=dict(type="str", required=True),
            account_name=dict(type="str", required=True),
            account_login=dict(type="str"),
            description=dict(type="str"),
            auto_change_password=dict(type="bool", no_log=False),
            auto_change_ssh_key=dict(type="bool", no_log=False),
            checkout_policy=dict(type="str"),
            certificate_validity=dict(type="str"),
            services=dict(type="list", elements="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    device_id, domain_id = find_localdomain(module)
    if domain_id is None:
        module.exit_json(changed=False, account=None, diff=dict(before={}, after={}))
    resource = DeviceLocalDomainAccountResource(
        module,
        path="devices/%s/localdomains/%s/accounts" % (device_id, domain_id),
        name_field="account_name",
        fields=("account_name", "account_login", "description", "auto_change_password", "auto_change_ssh_key",
                "checkout_policy", "certificate_validity", "services"),
        set_fields=("services",),
        result_key="account",
        required_on_create=("account_login",),
        update_query="force=true",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
