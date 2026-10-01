#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: device_service_info
short_description: Get the services of a device from a WALLIX Bastion
version_added: 1.0.0
description:
  - Return one service of a device by name, or every service of the device.
  - Equivalent of the C(wallix-bastion_device_service) Terraform data source.
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
  service_name:
    description:
      - Name of the service to return. Without it, all the services of the device are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get the SSH service of a device
  wallix.bastion.device_service_info:
    device_name: srv-linux-01
    service_name: SSH
  register: result

- name: List the services of a device
  wallix.bastion.device_service_info:
    device_name: srv-linux-01
  register: all_services
"""

RETURN = r"""
services:
  description:
    - Matching services, as returned by the Bastion API. Empty when O(service_name) matches no service.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f6db068020af9005056b66c8b
      service_name: SSH
      protocol: SSH
      port: 22
      connection_policy: SSH
      subprotocols: [SSH_SHELL_SESSION]
      global_domains: []
      url: /services/1a0f6db068020af9005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, find_parent, run_info


def main():
    module = BastionModule(
        argument_spec=dict(
            device_name=dict(type="str", required=True),
            service_name=dict(type="str"),
        ),
        supports_check_mode=True,
    )
    device_id = find_parent(module, "devices", "device_name", module.params["device_name"], label="device")
    run_info(module, path="devices/%s/services" % device_id, name_field="service_name", result_key="services")


if __name__ == "__main__":
    main()
