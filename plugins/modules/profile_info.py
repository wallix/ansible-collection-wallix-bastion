#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: profile_info
short_description: Get user profiles from a WALLIX Bastion
version_added: 1.1.0
description:
  - Return one user profile by name, or every profile of the Bastion, built-in ones included.
  - Equivalent of the C(wallix-bastion_profile) Terraform data source.
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
  profile_name:
    description:
      - Name of the profile to return. Without it, all profiles are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one profile
  wallix.bastion.profile_info:
    profile_name: product_administrator
  register: result

- name: Show its web interface rights
  ansible.builtin.debug:
    var: result.profiles[0].gui_features

- name: List every profile
  wallix.bastion.profile_info:
  register: all_profiles
"""

RETURN = r"""
profiles:
  description:
    - Matching profiles, as returned by the Bastion API, with the group lists of the limitations sorted.
      Rights not granted are V(null).
    - Empty when O(profile_name) matches no profile.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 19f463ca6d8d958f005056b66c8b
      profile_name: auditor
      editable: false
      description: ""
      gui_features:
        wab_audit: view
        system_audit: null
        users: null
        user_groups: null
        devices: null
        target_groups: null
        authorizations: null
        profiles: null
        wab_settings: null
        system_settings: null
        backup: null
        approval: null
        credential_recovery: null
      gui_transmission:
        system_audit: null
        users: null
        user_groups: null
        devices: null
        target_groups: null
        authorizations: null
        profiles: null
        wab_settings: null
        system_settings: null
        backup: null
        approval: null
        credential_recovery: null
      ip_limitation: ""
      target_access: false
      user_groups_limitation:
        enabled: false
      target_groups_limitation:
        enabled: false
      dashboards: [audit]
      url: https://bastion.example.com/api/v3.12/profiles/19f463ca6d8d958f005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, run_info

LIMITATIONS = dict(target_groups_limitation="target_groups", user_groups_limitation="user_groups")


def normalize_profile(obj):
    """Sort the group lists of the limitations, as wallix.bastion.profile does."""
    obj = dict(obj)
    for field, groups_key in LIMITATIONS.items():
        value = obj.get(field)
        if isinstance(value, dict):
            if value.get("enabled"):
                obj[field] = dict(value, **{groups_key: sorted(value.get(groups_key) or [])})
            else:
                obj[field] = {"enabled": False}
    return obj


def main():
    module = BastionModule(
        argument_spec=dict(profile_name=dict(type="str")),
        supports_check_mode=True,
    )
    run_info(module, path="profiles", name_field="profile_name", result_key="profiles", normalize=normalize_profile)


if __name__ == "__main__":
    main()
