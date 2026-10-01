#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: user_info
short_description: Get users from a WALLIX Bastion
version_added: 1.0.0
description:
  - Return one user by name, or every user of the Bastion.
  - Equivalent of the C(wallix-bastion_user) Terraform data source.
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
  user_name:
    description:
      - Name of the user to return, compared case-insensitively by the Bastion. Without it, all users are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one user
  wallix.bastion.user_info:
    user_name: john.doe
  register: result

- name: Fail if the user is missing
  ansible.builtin.assert:
    that: result.users | length == 1

- name: List every user
  wallix.bastion.user_info:
  register: all_users
"""

RETURN = r"""
users:
  description:
    - Matching users, as returned by the Bastion API, without the password field.
    - Empty when O(user_name) matches no user.
  returned: always
  type: list
  elements: dict
  sample:
    - user_name: john.doe
      display_name: John Doe
      email: john.doe@example.com
      preferred_language: en
      ip_source: ""
      profile: user
      groups: [linux-admins]
      force_change_pwd: false
      ssh_public_key: ""
      certificate_dn: ""
      last_connection: null
      user_auths: [local_password]
      is_locked: false
      expiration_date: ""
      is_disabled: false
      gpg_public_key: ""
      last_password_change: "2026-10-01 11:45:18"
      url: https://bastion.example.com/api/v3.12/users/john.doe
"""

from urllib.parse import quote

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule


def _clean(user):
    # The API returns a masked password ("********"); it carries no information.
    return {k: v for k, v in user.items() if k != "password"}


def main():
    module = BastionModule(
        argument_spec=dict(user_name=dict(type="str")),
        supports_check_mode=True,
    )
    # Users have no id: the API addresses them by name, so run_info() does not apply.
    try:
        name = module.params.get("user_name")
        if name:
            found = module.client.get("users/%s" % quote(name, safe=""))
            users = [found] if found else []
        else:
            users = module.client.get("users") or []
        module.exit_json(changed=False, users=[_clean(u) for u in users])
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)


if __name__ == "__main__":
    main()
