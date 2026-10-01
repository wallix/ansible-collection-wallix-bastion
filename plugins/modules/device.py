#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: device
short_description: Manage devices on a WALLIX Bastion
version_added: 1.0.0
description:
  - Create, update or delete a device on a WALLIX Bastion.
  - Equivalent of the C(wallix-bastion_device) Terraform resource.
  - Services and local domains are managed with their own modules.
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
  device_name:
    description:
      - Name of the device. Identifies the device on the Bastion.
    type: str
    required: true
  host:
    description:
      - Host name or IP address of the device.
      - Required when the device does not exist yet and O(state=present).
    type: str
  alias:
    description:
      - Alias of the device.
    type: str
  description:
    description:
      - Description of the device.
    type: str
  tags:
    description:
      - Tags of the device. Order does not matter.
      - When set, replaces all the tags of the device. Use V([]) to remove all tags.
    type: list
    elements: dict
    suboptions:
      key:
        description: Tag key.
        type: str
        required: true
      value:
        description: Tag value.
        type: str
        required: true
  state:
    description:
      - Whether the device should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
"""

EXAMPLES = r"""
- name: Ensure a Linux server is declared
  wallix.bastion.device:
    device_name: srv-linux-01
    host: 10.0.0.11
    description: Production web server
    tags:
      - key: env
        value: prod

- name: Set the connection once for several tasks
  module_defaults:
    group/wallix.bastion.bastion:
      bastion_host: bastion.example.com
      bastion_user: admin
      bastion_token: "{{ vault_bastion_api_key }}"
  block:
    - name: Declare device
      wallix.bastion.device:
        device_name: srv-linux-02
        host: 10.0.0.12

- name: Remove a device
  wallix.bastion.device:
    device_name: srv-linux-01
    state: absent
"""

RETURN = r"""
device:
  description:
    - The device as returned by the Bastion API after the change.
    - In check mode, the expected device. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1b3b4b8c0c1d4e5f
    device_name: srv-linux-01
    host: 10.0.0.11
    alias: ""
    description: Production web server
    tags: [{key: env, value: prod}]
    services: []
    local_domains: []
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the device already existed and O(state=present)
  type: list
  elements: str
  sample: [description, tags]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)


def main():
    module = BastionModule(
        argument_spec=dict(
            device_name=dict(type="str", required=True),
            host=dict(type="str"),
            alias=dict(type="str"),
            description=dict(type="str"),
            tags=dict(
                type="list",
                elements="dict",
                options=dict(
                    key=dict(type="str", required=True, no_log=False),
                    value=dict(type="str", required=True),
                ),
            ),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    resource = BastionResource(
        module,
        path="devices",
        name_field="device_name",
        fields=("device_name", "host", "alias", "description", "tags"),
        set_fields=("tags",),
        result_key="device",
        required_on_create=("host",),
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
