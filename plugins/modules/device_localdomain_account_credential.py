#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: device_localdomain_account_credential
short_description: Manage credentials of a device local domain account on a WALLIX Bastion
version_added: 1.0.0
description:
  - Create, update or delete the password or the SSH key of an account of a device local domain
    on a WALLIX Bastion.
  - Equivalent of the C(wallix-bastion_device_localdomain_account_credential) Terraform resource.
  - An account has at most one credential of each O(type), so O(type) identifies the credential.
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
      - Name of the local domain of the device. The local domain must exist.
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
    type: str
    required: true
    choices: [password, ssh_key]
  password:
    description:
      - The password, for O(type=password).
      - Required when the credential does not exist yet and O(type=password).
      - The Bastion never returns it, so it cannot be compared. See O(update_password).
    type: str
  private_key:
    description:
      - The SSH private key, for O(type=ssh_key), or V(generate:<type>) to have the Bastion
        generate one, for example V(generate:ED25519) or V(generate:RSA_4096).
      - Required when the credential does not exist yet and O(type=ssh_key).
      - The Bastion never returns it, so it cannot be compared. See O(update_password).
    type: str
  passphrase:
    description:
      - Passphrase of O(private_key).
      - The Bastion never returns it, so it cannot be compared. See O(update_password).
    type: str
  update_password:
    description:
      - V(on_create) sends O(password), O(private_key) and O(passphrase) only when the credential is created.
      - V(always) sends them on every run, which then always reports a change. The credential
        is replaced in place. With O(private_key=generate:<type>), this generates a new key on every run.
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
  - With O(state=absent), a missing device, local domain or account is not an error.
"""

EXAMPLES = r"""
- name: Set the password of the root account
  wallix.bastion.device_localdomain_account_credential:
    device_name: srv-linux-01
    domain_name: local
    account_name: root
    type: password
    password: "{{ vault_root_password }}"

- name: Have the Bastion generate an SSH key for the account
  wallix.bastion.device_localdomain_account_credential:
    device_name: srv-linux-01
    domain_name: local
    account_name: root
    type: ssh_key
    private_key: generate:ED25519
  register: key

- name: Show the public key to install on the server
  ansible.builtin.debug:
    msg: "{{ key.credential.public_key }}"

- name: Rotate the password on every run
  wallix.bastion.device_localdomain_account_credential:
    device_name: srv-linux-01
    domain_name: local
    account_name: root
    type: password
    password: "{{ vault_root_new_password }}"
    update_password: always

- name: Remove the SSH key
  wallix.bastion.device_localdomain_account_credential:
    device_name: srv-linux-01
    domain_name: local
    account_name: root
    type: ssh_key
    state: absent
"""

RETURN = r"""
credential:
  description:
    - The credential as returned by the Bastion API after the change, without its secrets.
    - In check mode, the expected credential. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f6dbd1f68d4e8005056b66c8b
    type: ssh_key
    key_id: f9a17c67bd374e81bd9d4222e305f3b9
    public_key: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIC8AUFSJcx+fgI7j0JboX1MhgxEot4gYI1sJubI9HsG3"
    url: https://bastion.example.com/api/v3.12/devices/1a0f.../credentials/1a0f6dbd1f68d4e8005056b66c8b
changed_fields:
  description:
    - Options that were updated. Contains the secret options that were set when O(update_password=always).
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

SECRETS = ("password", "private_key", "passphrase")


def find_account(module):
    """Ids of the device, local domain and account; None when removing an orphan credential."""
    params = module.params
    device_id = find_parent(module, "devices", "device_name", params["device_name"], label="device")
    if device_id is None:
        return None
    path = "devices/%s/localdomains" % device_id
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
            device_name=dict(type="str", required=True),
            domain_name=dict(type="str", required=True),
            account_name=dict(type="str", required=True),
            type=dict(type="str", required=True, choices=["password", "ssh_key"]),
            password=dict(type="str", no_log=True),
            private_key=dict(type="str", no_log=True),
            passphrase=dict(type="str", no_log=True),
            update_password=dict(type="str", choices=["always", "on_create"], default="on_create", no_log=False),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        required_by=dict(passphrase="private_key"),
        supports_check_mode=True,
    )
    cred_type = module.params["type"]
    wrong = ("private_key", "passphrase") if cred_type == "password" else ("password",)
    wrong = [f for f in wrong if module.params.get(f) is not None]
    if wrong:
        module.fail_json(msg="%s cannot be set for a credential of type %s" % (", ".join(wrong), cred_type))

    path = find_account(module)
    if path is None:
        module.exit_json(changed=False, credential=None, diff=dict(before={}, after={}))
    resource = BastionResource(
        module,
        path=path,
        name_field="type",
        search="list",
        fields=("type",) + SECRETS,
        result_key="credential",
        required_on_create=("password",) if cred_type == "password" else ("private_key",),
        create_only_fields=("type",),
        secret_fields=SECRETS,
        update_secrets=module.params["update_password"] == "always",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
