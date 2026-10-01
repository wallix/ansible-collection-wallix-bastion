#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: domain
short_description: Manage global domains on a WALLIX Bastion
version_added: 1.0.0
description:
  - Create, update or delete a global domain on a WALLIX Bastion.
  - Equivalent of the C(wallix-bastion_domain) Terraform resource.
  - Accounts of the domain and their credentials are managed with M(wallix.bastion.domain_account)
    and M(wallix.bastion.domain_account_credential).
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
      - Name of the domain. Identifies the domain on the Bastion.
    type: str
    required: true
  domain_real_name:
    description:
      - Real name of the domain, as used to connect to targets (for example C(corp.example.com)).
    type: str
  description:
    description:
      - Description of the domain.
    type: str
  admin_account:
    description:
      - Name of the account of this domain used to change passwords.
      - The account must already exist (see M(wallix.bastion.domain_account)), so it cannot be set
        when the domain is created. Set it in a later task.
      - Only kept by the Bastion while O(enable_password_change=true).
    type: str
  enable_password_change:
    description:
      - Whether the Bastion changes the passwords of the accounts of this domain.
      - V(true) needs O(password_change_policy) and O(password_change_plugin), on the Bastion or in the task.
      - V(false) makes the Bastion clear O(admin_account), O(password_change_policy),
        O(password_change_plugin) and O(password_change_plugin_parameters).
    type: bool
  password_change_policy:
    description:
      - Name of the password change policy, for example V(default).
    type: str
  password_change_plugin:
    description:
      - Name of the password change plugin, for example V(Unix).
    type: str
  password_change_plugin_parameters:
    description:
      - Parameters of the password change plugin, as a dictionary (a JSON string is accepted).
      - Treated as a secret. Sent when the domain is created, when the Bastion has no parameters yet,
        and on every run with O(update_password=always).
    type: dict
  ca_private_key:
    description:
      - Private key of the SSH certificate authority of the domain, or V(generate:<TYPE>) to let the Bastion
        generate one, for example V(generate:RSA_4096) or V(generate:ED25519).
      - The Bastion never returns it, so it cannot be compared. It is sent when the domain is created, when the
        domain has no CA key yet, and on every run with O(update_password=always), except that a V(generate:)
        value is never sent to a domain that already has a key.
      - Mutually exclusive with O(vault_plugin).
    type: str
  passphrase:
    description:
      - Passphrase protecting O(ca_private_key). Sent along with O(ca_private_key).
    type: str
  vault_plugin:
    description:
      - Name of the external vault plugin managing the accounts of the domain.
      - Can only be set when the domain is created; changing it fails. Delete and recreate the domain instead.
      - Mutually exclusive with O(enable_password_change=true) and O(ca_private_key).
    type: str
  vault_plugin_parameters:
    description:
      - Parameters of O(vault_plugin), as a dictionary (a JSON string is accepted).
      - Treated as a secret, like O(password_change_plugin_parameters).
    type: dict
  update_password:
    description:
      - V(on_create) sends the secret options (O(ca_private_key), O(passphrase), O(password_change_plugin_parameters),
        O(vault_plugin_parameters)) only when the domain is created or when the Bastion has no value for them yet.
      - V(always) sends them on every run, which then always reports a change.
    type: str
    choices: [always, on_create]
    default: on_create
  state:
    description:
      - Whether the domain should exist.
      - Deleting a domain deletes its accounts and their credentials.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
"""

EXAMPLES = r"""
- name: Declare an Active Directory domain
  wallix.bastion.domain:
    domain_name: corp
    domain_real_name: corp.example.com
    description: Corporate domain

- name: Give the domain an SSH certificate authority generated by the Bastion
  wallix.bastion.domain:
    domain_name: corp
    ca_private_key: generate:RSA_4096

- name: Create the account used to change passwords
  wallix.bastion.domain_account:
    domain_name: corp
    account_name: svc-pwchange
    account_login: svc-pwchange

- name: Enable password change with that account
  wallix.bastion.domain:
    domain_name: corp
    admin_account: svc-pwchange
    enable_password_change: true
    password_change_policy: default
    password_change_plugin: Unix
    password_change_plugin_parameters:
      host: 192.0.2.1

- name: Remove a domain and all its accounts
  wallix.bastion.domain:
    domain_name: corp
    state: absent
"""

RETURN = r"""
domain:
  description:
    - The domain as returned by the Bastion API after the change, without the secret options.
    - In check mode, the expected domain. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f6dbf308b89e1005056b66c8b
    domain_name: corp
    domain_real_name: corp.example.com
    description: Corporate domain
    admin_account: null
    kerberos: null
    enable_password_change: false
    password_change_policy: null
    password_change_plugin: null
    ca_public_key: "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCZ/4s9OBge... \"\"\n"
    vault_plugin: null
    is_editable: true
    url: https://bastion.example.com/api/v3.12/domains/1a0f6dbf308b89e1005056b66c8b
changed_fields:
  description:
    - Options that differed from the Bastion and were updated.
    - Contains the secret options sent because of O(update_password=always) or because the Bastion had no value for them.
  returned: when the domain already existed and O(state=present)
  type: list
  elements: str
  sample: [description]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)

FIELDS = (
    "domain_name", "domain_real_name", "description", "admin_account", "enable_password_change",
    "password_change_policy", "password_change_plugin", "password_change_plugin_parameters",
    "ca_private_key", "passphrase", "vault_plugin", "vault_plugin_parameters",
)
SECRETS = ("ca_private_key", "passphrase", "password_change_plugin_parameters", "vault_plugin_parameters")


class DomainResource(BastionResource):
    """Global domain. PUT merges the fields it gets, so only the requested ones are sent."""

    def _unset_secrets(self, current, desired):
        """Secret options the Bastion has no value for yet: set them whatever update_password says."""
        unset = set()
        if not current.get("ca_public_key") and current.get("ca_private_key") in (None, ""):
            unset.update(f for f in ("ca_private_key", "passphrase") if f in desired)
        for f in ("password_change_plugin_parameters", "vault_plugin_parameters"):
            if f in desired and not current.get(f):
                unset.add(f)
        return unset

    def _secrets_to_send(self, current, desired):
        sent = set(f for f in SECRETS if f in desired) if self.update_secrets else self._unset_secrets(current, desired)
        if "ca_private_key" in sent and current.get("ca_public_key") \
                and str(desired["ca_private_key"]).startswith("generate:"):
            # Re-sending generate: would replace the existing CA key on every run.
            sent.discard("ca_private_key")
        if "ca_private_key" not in sent:
            sent.discard("passphrase")
        return sent

    def read(self):
        self._current = super(DomainResource, self).read()
        return self._current

    def desired(self):
        desired = super(DomainResource, self).desired()
        if getattr(self, "_current", True) is None and "admin_account" in desired:
            self.module.fail_json(msg="domain %s does not exist; admin_account can only be set once the domain "
                                      "and that account exist (the API refuses it on creation)" % self.name)
        return desired

    def differences(self, current, desired):
        changes = super(DomainResource, self).differences(current, desired)
        return sorted(set(changes) | self._secrets_to_send(current, desired))

    def update(self, current, desired):
        # ensure() drops secrets from desired unless update_password=always; re-add the unset ones.
        requested = self.desired()
        sent = self._secrets_to_send(current, requested)
        values = {f: v for f, v in requested.items() if f not in SECRETS or f in sent}
        self.client.call("PUT", self.object_path(current["id"]), self.body(values))
        return self.normalize(self.client.get(self.object_path(current["id"])))


def main():
    module = BastionModule(
        argument_spec=dict(
            domain_name=dict(type="str", required=True),
            domain_real_name=dict(type="str"),
            description=dict(type="str"),
            admin_account=dict(type="str"),
            enable_password_change=dict(type="bool"),
            password_change_policy=dict(type="str", no_log=False),
            password_change_plugin=dict(type="str", no_log=False),
            password_change_plugin_parameters=dict(type="dict", no_log=True),
            ca_private_key=dict(type="str", no_log=True),
            passphrase=dict(type="str", no_log=True),
            vault_plugin=dict(type="str"),
            vault_plugin_parameters=dict(type="dict", no_log=True),
            update_password=dict(type="str", choices=["always", "on_create"], default="on_create", no_log=False),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        mutually_exclusive=[("vault_plugin", "ca_private_key")],
        required_by=dict(passphrase="ca_private_key", vault_plugin_parameters="vault_plugin"),
        supports_check_mode=True,
    )
    if module.params["vault_plugin"] and module.params["enable_password_change"]:
        module.fail_json(msg="vault_plugin and enable_password_change=true are mutually exclusive")
    resource = DomainResource(
        module,
        path="domains",
        name_field="domain_name",
        fields=FIELDS,
        result_key="domain",
        create_only_fields=("vault_plugin",),
        secret_fields=SECRETS,
        update_secrets=module.params["update_password"] == "always",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
