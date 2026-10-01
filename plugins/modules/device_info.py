#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: device_info
short_description: Get devices from a WALLIX Bastion
version_added: 1.0.0
description:
  - Return one device by name, or every device of the Bastion.
  - Equivalent of the C(wallix-bastion_device) Terraform data source.
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
      - Name of the device to return. Without it, all devices are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one device
  wallix.bastion.device_info:
    device_name: srv-linux-01
  register: result

- name: Fail if the device is missing
  ansible.builtin.assert:
    that: result.devices | length == 1

- name: List every device
  wallix.bastion.device_info:
  register: all_devices
"""

RETURN = r"""
devices:
  description:
    - Matching devices, as returned by the Bastion API. Empty when O(device_name) matches no device.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1b3b4b8c0c1d4e5f
      device_name: srv-linux-01
      host: 10.0.0.11
      alias: ""
      description: Production web server
      tags: []
      services: []
      local_domains: []
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, run_info


def main():
    module = BastionModule(
        argument_spec=dict(device_name=dict(type="str")),
        supports_check_mode=True,
    )
    run_info(module, path="devices", name_field="device_name", result_key="devices")


if __name__ == "__main__":
    main()
