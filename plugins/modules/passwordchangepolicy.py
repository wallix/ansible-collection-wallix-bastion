#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: passwordchangepolicy
short_description: Manage password change policies on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete a credential change policy on a WALLIX Bastion.
  - A password change policy says how the Bastion generates new passwords and SSH keys for the
    accounts it manages, and when it changes them.
  - Equivalent of the C(wallix-bastion_passwordchangepolicy) Terraform resource.
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
  password_change_policy_name:
    description:
      - Name of the policy. Identifies the policy on the Bastion.
    type: str
    required: true
  description:
    description:
      - Description of the policy.
    type: str
  password_length:
    description:
      - Length of the generated passwords.
      - The Bastion requires at least password or SSH key settings when it creates a policy, and at
        least one of O(special_chars), O(lower_chars), O(upper_chars) or O(digit_chars) with a password length.
    type: int
  special_chars:
    description:
      - Minimum number of special characters in the generated passwords.
      - V(0) allows them without a minimum. A character class never set is not used at all.
    type: int
  lower_chars:
    description:
      - Minimum number of lower case letters in the generated passwords.
      - V(0) allows them without a minimum. A character class never set is not used at all.
    type: int
  upper_chars:
    description:
      - Minimum number of upper case letters in the generated passwords.
      - V(0) allows them without a minimum. A character class never set is not used at all.
    type: int
  digit_chars:
    description:
      - Minimum number of digits in the generated passwords.
      - V(0) allows them without a minimum. A character class never set is not used at all.
    type: int
  exclude_chars:
    description:
      - Characters never used in the generated passwords, for example V(Il0O).
    type: str
  ssh_key_type:
    description:
      - Type of the generated SSH keys.
      - The Bastion requires O(ssh_key_size) with it when it creates a policy.
    type: str
    choices: [RSA, DSA, ECDSA, ED25519]
  ssh_key_size:
    description:
      - Size of the generated SSH keys, in bits, for example V(4096) for RSA or V(384) for ECDSA.
    type: int
  change_period:
    description:
      - When the credentials are changed, as a cron expression, for example V(0 3 * * 1).
      - V("") disables the scheduled change.
    type: str
  state:
    description:
      - Whether the policy should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - The policy is looked up by O(password_change_policy_name), so it cannot be renamed with this module.
  - Once a character class or the SSH key type is set, this module cannot unset it again (the API
    needs V(null) for that); recreate the policy instead.
"""

EXAMPLES = r"""
- name: Change passwords and SSH keys every Monday at 3:00
  wallix.bastion.passwordchangepolicy:
    password_change_policy_name: weekly
    description: Weekly credential rotation
    password_length: 20
    lower_chars: 2
    upper_chars: 2
    digit_chars: 2
    special_chars: 0
    exclude_chars: Il0O
    ssh_key_type: ED25519
    ssh_key_size: 256
    change_period: "0 3 * * 1"

- name: Stop the scheduled change
  wallix.bastion.passwordchangepolicy:
    password_change_policy_name: weekly
    change_period: ""

- name: Remove a password change policy
  wallix.bastion.passwordchangepolicy:
    password_change_policy_name: weekly
    state: absent
"""

RETURN = r"""
passwordchangepolicy:
  description:
    - The password change policy as returned by the Bastion API after the change. Character
      classes the policy does not use are V(null).
    - In check mode, the expected policy. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f7687e96f0040005056b66c8b
    password_change_policy_name: weekly
    description: Weekly credential rotation
    password_length: 20
    special_chars: 0
    lower_chars: 2
    upper_chars: 2
    digit_chars: 2
    exclude_chars: Il0O
    ssh_key_type: ED25519
    ssh_key_size: 256
    change_period: "0 3 * * 1"
    url: https://bastion.example.com/api/v3.12/passwordchangepolicies/1a0f7687e96f0040005056b66c8b
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the policy already existed and O(state=present)
  type: list
  elements: str
  sample: [change_period]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)


def main():
    module = BastionModule(
        argument_spec=dict(
            password_change_policy_name=dict(type="str", required=True),
            description=dict(type="str"),
            password_length=dict(type="int", no_log=False),
            special_chars=dict(type="int"),
            lower_chars=dict(type="int"),
            upper_chars=dict(type="int"),
            digit_chars=dict(type="int"),
            exclude_chars=dict(type="str"),
            ssh_key_type=dict(type="str", choices=["RSA", "DSA", "ECDSA", "ED25519"]),
            ssh_key_size=dict(type="int"),
            change_period=dict(type="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    resource = BastionResource(
        module,
        path="passwordchangepolicies",
        name_field="password_change_policy_name",
        fields=("password_change_policy_name", "description", "password_length", "special_chars",
                "lower_chars", "upper_chars", "digit_chars", "exclude_chars", "ssh_key_type",
                "ssh_key_size", "change_period"),
        result_key="passwordchangepolicy",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
