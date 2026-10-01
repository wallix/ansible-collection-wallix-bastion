#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: device_localdomain_info
short_description: Get the local domains of a device from a WALLIX Bastion
version_added: 1.0.0
description:
  - Return one local domain of a device by name, or every local domain of the device.
  - Equivalent of the C(wallix-bastion_device_localdomain) Terraform data source.
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
  domain_name:
    description:
      - Name of the local domain to return. Without it, all the local domains of the device are returned.
    type: str
notes:
  - The Bastion masks C(ca_private_key) as V(********) when it is set.
"""

EXAMPLES = r"""
- name: Get the public key of the SSH certificate authority of a local domain
  wallix.bastion.device_localdomain_info:
    device_name: srv-linux-01
    domain_name: local
  register: result

- name: Show it
  ansible.builtin.debug:
    msg: "{{ result.localdomains[0].ca_public_key }}"
"""

RETURN = r"""
localdomains:
  description:
    - Matching local domains, as returned by the Bastion API. Empty when O(domain_name) matches no local domain.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f6db6cad64f53005056b66c8b
      domain_name: local
      description: Local accounts of srv-linux-01
      admin_account: null
      enable_password_change: false
      password_change_policy: null
      password_change_plugin: null
      password_change_plugin_parameters: null
      ca_private_key: "********"
      ca_public_key: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIC8AUFSJcx+fgI7j0JboX1MhgxEot4gYI1sJubI9HsG3"
      url: https://bastion.example.com/api/v3.12/devices/1a0f6db040c0b839005056b66c8b/localdomains/1a0f6db6cad64f53005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, find_parent, run_info


def main():
    module = BastionModule(
        argument_spec=dict(
            device_name=dict(type="str", required=True),
            domain_name=dict(type="str"),
        ),
        supports_check_mode=True,
    )
    device_id = find_parent(module, "devices", "device_name", module.params["device_name"], label="device")
    run_info(module, path="devices/%s/localdomains" % device_id, name_field="domain_name", result_key="localdomains")


if __name__ == "__main__":
    main()
