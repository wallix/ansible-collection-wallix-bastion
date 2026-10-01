#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: checkout_policy
short_description: Manage checkout policies on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete a checkout policy on a WALLIX Bastion.
  - A checkout policy says whether accounts are locked while checked out, for how long, and whether
    their credentials change at check-in.
  - Equivalent of the C(wallix-bastion_checkout_policy) Terraform resource.
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
  checkout_policy_name:
    description:
      - Name of the checkout policy. Identifies the policy on the Bastion.
    type: str
    required: true
  description:
    description:
      - Description of the policy.
    type: str
  enable_lock:
    description:
      - Lock the account while it is checked out.
      - When V(true), O(duration) and O(max_duration) are required by the Bastion.
      - Setting it to V(false) resets O(duration), O(extension), O(max_duration) and
        O(change_credentials_at_checkin) on the Bastion.
    type: bool
  change_credentials_at_checkin:
    description:
      - Change the credentials of the account when it is checked in.
      - Only possible with O(enable_lock=true).
    type: bool
  duration:
    description:
      - Default checkout duration, in seconds.
      - Only possible with O(enable_lock=true).
    type: int
  extension:
    description:
      - Duration of a checkout extension, in seconds. V(0) means no extension.
      - Only possible with O(enable_lock=true).
    type: int
  max_duration:
    description:
      - Maximum checkout duration, extensions included, in seconds.
      - Must equal O(duration) when O(extension=0).
      - Only possible with O(enable_lock=true).
    type: int
  state:
    description:
      - Whether the policy should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - The policy is looked up by O(checkout_policy_name), so it cannot be renamed with this module.
  - The Bastion ignores the lock settings (O(duration), O(extension), O(max_duration),
    O(change_credentials_at_checkin)) of a policy whose lock is disabled; the module fails instead of
    reporting a change that would never apply.
"""

EXAMPLES = r"""
- name: Lock accounts for one hour, extensible by 30 minutes up to two hours
  wallix.bastion.checkout_policy:
    checkout_policy_name: one-hour-lock
    description: Exclusive checkout of shared accounts
    enable_lock: true
    duration: 3600
    extension: 1800
    max_duration: 7200
    change_credentials_at_checkin: true

- name: Disable the lock
  wallix.bastion.checkout_policy:
    checkout_policy_name: one-hour-lock
    enable_lock: false

- name: Remove a checkout policy
  wallix.bastion.checkout_policy:
    checkout_policy_name: one-hour-lock
    state: absent
"""

RETURN = r"""
checkout_policy:
  description:
    - The checkout policy as returned by the Bastion API after the change.
    - In check mode, the expected policy. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f767fdefd88c1005056b66c8b
    checkout_policy_name: one-hour-lock
    description: Exclusive checkout of shared accounts
    enable_lock: true
    duration: 3600
    extension: 1800
    max_duration: 7200
    change_credentials_at_checkin: true
    url: https://bastion.example.com/api/v3.12/checkoutpolicies/1a0f767fdefd88c1005056b66c8b
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the policy already existed and O(state=present)
  type: list
  elements: str
  sample: [duration]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)

LOCK_FIELDS = ("change_credentials_at_checkin", "duration", "extension", "max_duration")


class CheckoutPolicyResource(BastionResource):

    def read(self):
        self._current = super(CheckoutPolicyResource, self).read()
        return self._current

    def desired(self):
        desired = super(CheckoutPolicyResource, self).desired()
        current = getattr(self, "_current", None) or {}
        lock = desired.get("enable_lock", current.get("enable_lock", False))
        if not lock:
            # Without a lock the Bastion silently resets these to 0/false.
            ignored = sorted(f for f in LOCK_FIELDS if desired.get(f))
            if ignored:
                self.module.fail_json(msg="checkout_policy %s: %s require enable_lock=true" % (
                    self.name, ", ".join(ignored)))
        return desired


def main():
    module = BastionModule(
        argument_spec=dict(
            checkout_policy_name=dict(type="str", required=True),
            description=dict(type="str"),
            enable_lock=dict(type="bool"),
            change_credentials_at_checkin=dict(type="bool"),
            duration=dict(type="int"),
            extension=dict(type="int"),
            max_duration=dict(type="int"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    resource = CheckoutPolicyResource(
        module,
        path="checkoutpolicies",
        name_field="checkout_policy_name",
        fields=("checkout_policy_name", "description", "enable_lock") + LOCK_FIELDS,
        result_key="checkout_policy",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
