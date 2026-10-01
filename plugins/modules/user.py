#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: user
short_description: Manage users on a WALLIX Bastion
version_added: 1.0.0
description:
  - Create, update or delete a user account on a WALLIX Bastion.
  - Equivalent of the C(wallix-bastion_user) Terraform resource.
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
  user_name:
    description:
      - Login of the user. Identifies the user on the Bastion.
      - The Bastion compares user names case-insensitively; a user that exists with a different
        case is managed as the same user and keeps its name.
      - Cannot be changed after creation.
    type: str
    required: true
  email:
    description:
      - Email address of the user.
      - Required when the user does not exist yet and O(state=present).
    type: str
  profile:
    description:
      - Name of the profile of the user, for example V(user) or V(product_administrator).
      - Required when the user does not exist yet and O(state=present).
    type: str
  user_auths:
    description:
      - Authentication methods of the user, for example V(local_password) or V(local_sshkey). Order does not matter.
      - Required when the user does not exist yet and O(state=present).
    type: list
    elements: str
  certificate_dn:
    description:
      - Distinguished name of the X.509 certificate of the user.
    type: str
  display_name:
    description:
      - Display name of the user.
    type: str
  expiration_date:
    description:
      - Expiration date of the account, in the format C(YYYY-MM-DD HH:MM). Use V("") for no expiration.
    type: str
  force_change_pwd:
    description:
      - Whether the user must change the password at the next login.
      - The Bastion resets it to V(false) once the user has changed the password.
    type: bool
  groups:
    description:
      - Names of the user groups the user belongs to. Order does not matter.
      - When set, replaces all the group memberships of the user. Use V([]) to remove the user from every group.
      - Group membership can also be managed from the group with M(wallix.bastion.usergroup) O(wallix.bastion.usergroup#module:users);
        set it on one side only.
    type: list
    elements: str
  ip_source:
    description:
      - IP addresses or networks the user may connect from, comma separated. Use V("") for no restriction.
    type: str
  is_disabled:
    description:
      - Whether the account is disabled.
    type: bool
  password:
    description:
      - Password of the user. Required by the Bastion when O(user_auths) contains V(local_password)
        and the user is created.
      - The Bastion never returns it, so it cannot be compared. See O(update_password).
    type: str
  update_password:
    description:
      - V(on_create) sets O(password) only when the user is created.
      - V(always) sends O(password) on every run, which then always reports a change.
    type: str
    choices: [always, on_create]
    default: on_create
  preferred_language:
    description:
      - Language of the user interface for this user.
    type: str
    choices: [de, en, es, fr, ru]
  ssh_public_key:
    description:
      - SSH public key of the user, used with the V(local_sshkey) authentication method.
      - Several keys are given as one string with one key per line.
      - Compared as is with what the Bastion returns, including any trailing newline. Use V("") to remove the keys.
    type: str
  state:
    description:
      - Whether the user should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
"""

EXAMPLES = r"""
- name: Ensure a local user with a password and an SSH key exists
  wallix.bastion.user:
    user_name: john.doe
    email: john.doe@example.com
    profile: user
    user_auths: [local_password, local_sshkey]
    display_name: John Doe
    password: "{{ vault_john_password }}"
    force_change_pwd: true
    ssh_public_key: "{{ lookup('ansible.builtin.file', 'files/john.pub') }}"
    groups: [linux-admins]

- name: Reset the password of an existing user
  wallix.bastion.user:
    user_name: john.doe
    password: "{{ vault_john_new_password }}"
    update_password: always

- name: Disable a user
  wallix.bastion.user:
    user_name: john.doe
    is_disabled: true

- name: Remove a user
  wallix.bastion.user:
    user_name: john.doe
    state: absent
"""

RETURN = r"""
user:
  description:
    - The user as returned by the Bastion API after the change, without the password.
    - In check mode, the expected user. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    user_name: john.doe
    display_name: John Doe
    email: john.doe@example.com
    preferred_language: en
    ip_source: ""
    profile: user
    groups: [linux-admins]
    force_change_pwd: true
    ssh_public_key: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG51Jr8d9zidRxHe6udWCu1DmkRg6l9VxU4YcR8jE6J9 john@laptop
    certificate_dn: ""
    last_connection: null
    user_auths: [local_password, local_sshkey]
    is_locked: false
    expiration_date: ""
    is_disabled: false
    gpg_public_key: ""
    last_password_change: "2026-10-01 11:45:18"
    url: https://bastion.example.com/api/v3.12/users/john.doe
changed_fields:
  description: Options that differed from the Bastion and were updated. Contains V(password) when O(update_password=always).
  returned: when the user already existed and O(state=present)
  type: list
  elements: str
  sample: [display_name, groups]
"""

from urllib.parse import quote

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)


class UserResource(BastionResource):
    """Users have no id: the API addresses them by user_name (case-insensitively)."""

    def object_path(self, object_id=None):
        return "%s/%s" % (self.path, quote(self.name, safe=""))

    def read(self):
        return self.client.get(self.object_path())

    def differences(self, current, desired):
        # user_name is the lookup key; it only differs from the Bastion by case.
        desired = {f: v for f, v in desired.items() if f != self.name_field}
        return super(UserResource, self).differences(current, desired)

    def create(self, desired):
        # POST /users returns no X-Object-Id: read the user back by name.
        self.client.call("POST", self.path, self.body(desired))
        created = self.read()
        if created is None:
            raise BastionError("user %s not found after creation" % self.name)
        return created

    def update(self, current, desired):
        values = {f: current[f] for f in self.fields if f in current and f not in self.secret_fields}
        values.update({f: v for f, v in desired.items() if f != self.name_field})
        # Without force=true the API appends to list fields (groups) instead of replacing them.
        self.client.call("PUT", self.object_path() + "?force=true", self.body(values))
        return self.read()

    def delete(self, current):
        self.client.call("DELETE", self.object_path(), expected=(200, 204, 404))


def main():
    module = BastionModule(
        argument_spec=dict(
            user_name=dict(type="str", required=True),
            email=dict(type="str"),
            profile=dict(type="str"),
            user_auths=dict(type="list", elements="str"),
            certificate_dn=dict(type="str"),
            display_name=dict(type="str"),
            expiration_date=dict(type="str"),
            force_change_pwd=dict(type="bool"),
            groups=dict(type="list", elements="str"),
            ip_source=dict(type="str"),
            is_disabled=dict(type="bool"),
            password=dict(type="str", no_log=True),
            update_password=dict(type="str", choices=["always", "on_create"], default="on_create", no_log=False),
            preferred_language=dict(type="str", choices=["de", "en", "es", "fr", "ru"]),
            ssh_public_key=dict(type="str", no_log=False),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    resource = UserResource(
        module,
        path="users",
        name_field="user_name",
        fields=("user_name", "email", "profile", "user_auths", "certificate_dn", "display_name",
                "expiration_date", "force_change_pwd", "groups", "ip_source", "is_disabled",
                "password", "preferred_language", "ssh_public_key"),
        set_fields=("user_auths", "groups"),
        result_key="user",
        required_on_create=("email", "profile", "user_auths"),
        secret_fields=("password",),
        update_secrets=module.params["update_password"] == "always",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
