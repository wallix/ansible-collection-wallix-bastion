#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: device_localdomain_account_credential_info
short_description: Get the credentials of a device local domain account from a WALLIX Bastion
version_added: 1.0.0
description:
  - Return the credential of one type of an account of a device local domain, or every credential of the account.
  - Equivalent of the C(wallix-bastion_device_localdomain_account_credential) Terraform data source.
  - Secrets (password, private key, passphrase) are never returned.
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
      - Name of the account of the local domain. The module fails if the account does not exist.
    type: str
    required: true
  type:
    description:
      - Type of the credential to return. Without it, all the credentials of the account are returned.
    type: str
    choices: [password, ssh_key]
"""

EXAMPLES = r"""
- name: Get the public key of the SSH key of an account
  wallix.bastion.device_localdomain_account_credential_info:
    device_name: srv-linux-01
    domain_name: local
    account_name: root
    type: ssh_key
  register: result

- name: Show it
  ansible.builtin.debug:
    msg: "{{ result.credentials[0].public_key }}"
"""

RETURN = r"""
credentials:
  description:
    - Matching credentials, as returned by the Bastion API, without their secrets.
    - Empty when the account has no credential of type O(type).
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f6dbd1f68d4e8005056b66c8b
      type: ssh_key
      key_id: f9a17c67bd374e81bd9d4222e305f3b9
      public_key: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIC8AUFSJcx+fgI7j0JboX1MhgxEot4gYI1sJubI9HsG3"
      url: https://bastion.example.com/api/v3.12/devices/1a0f.../credentials/1a0f6dbd1f68d4e8005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, find_parent

SECRETS = ("password", "private_key", "passphrase")


def main():
    module = BastionModule(
        argument_spec=dict(
            device_name=dict(type="str", required=True),
            domain_name=dict(type="str", required=True),
            account_name=dict(type="str", required=True),
            type=dict(type="str", choices=["password", "ssh_key"]),
        ),
        supports_check_mode=True,
    )
    params = module.params
    device_id = find_parent(module, "devices", "device_name", params["device_name"], label="device")
    path = "devices/%s/localdomains" % device_id
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
