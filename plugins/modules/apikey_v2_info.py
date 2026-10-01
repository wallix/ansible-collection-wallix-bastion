#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: apikey_v2_info
short_description: Get API keys from a WALLIX Bastion, with their profile
version_added: 1.1.0
description:
  - Return one API key by name, or every API key of the Bastion, with their profile.
  - Equivalent of the C(wallix-bastion_apikey_v2) Terraform data source.
  - The key values are never returned; the Bastion only gives them once, at creation.
  - Requires API version v3.12 or later.
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
  apikey_name:
    description:
      - Name of the API key to return. Without it, all API keys are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one API key
  wallix.bastion.apikey_v2_info:
    apikey_name: monitoring
  register: result

- name: Fail if the key is missing
  ansible.builtin.assert:
    that: result.apikeys | length == 1

- name: List every API key
  wallix.bastion.apikey_v2_info:
  register: all_keys
"""

RETURN = r"""
apikeys:
  description:
    - Matching API keys, as returned by the Bastion API, without their value. Empty when O(apikey_name) matches no key.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f766d790f8b83005056b66c8b
      apikey_name: monitoring
      profile: auditor
      description: Used by the monitoring to read the Bastion
      ip_limitation: 192.0.2.10,192.0.2.11
      url: https://bastion.example.com/api/v3.12/apikeys-v2/1a0f766d790f8b83005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, run_info


def without_key(obj):
    """The API masks the key value as "********"; drop it."""
    return dict((k, v) for k, v in obj.items() if k != "apikey")


def main():
    module = BastionModule(
        argument_spec=dict(apikey_name=dict(type="str", no_log=False)),
        supports_check_mode=True,
    )
    run_info(module, path="apikeys-v2", name_field="apikey_name", result_key="apikeys", normalize=without_key)


if __name__ == "__main__":
    main()
