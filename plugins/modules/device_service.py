#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: device_service
short_description: Manage services of a device on a WALLIX Bastion
version_added: 1.0.0
description:
  - Create, update or delete a service (SSH, RDP, ...) of a device on a WALLIX Bastion.
  - Equivalent of the C(wallix-bastion_device_service) Terraform resource.
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
      - Name of the device the service belongs to. The device must exist.
    type: str
    required: true
  service_name:
    description:
      - Name of the service. Identifies the service on the device.
    type: str
    required: true
  connection_policy:
    description:
      - Name of the connection policy of the service, for example V(SSH) or V(RDP).
      - Required when the service does not exist yet and O(state=present).
    type: str
  port:
    description:
      - TCP port of the service on the device.
      - Required when the service does not exist yet and O(state=present).
    type: int
  protocol:
    description:
      - Protocol of the service.
      - Required when the service does not exist yet and O(state=present).
      - Cannot be changed once the service exists; delete and recreate the service instead.
    type: str
    choices: [SSH, RAWTCPIP, RDP, RLOGIN, TELNET, VNC]
  global_domains:
    description:
      - Names of the global domains whose accounts can be used on this service. Order does not matter.
      - When set, replaces all the global domains of the service. Use V([]) to remove them all.
    type: list
    elements: str
  subprotocols:
    description:
      - Sub-protocols allowed on the service. Order does not matter.
      - Only for O(protocol=SSH) (V(SSH_SHELL_SESSION), V(SSH_SCP_UP), ...) and
        O(protocol=RDP) (V(RDP_CLIPBOARD_UP), V(RDP_DRIVE), ...).
      - The Bastion requires at least one when creating an SSH or RDP service.
    type: list
    elements: str
  state:
    description:
      - Whether the service should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - With O(state=absent), a missing device is not an error.
"""

EXAMPLES = r"""
- name: Declare the SSH service of a Linux server
  wallix.bastion.device_service:
    device_name: srv-linux-01
    service_name: SSH
    connection_policy: SSH
    protocol: SSH
    port: 22
    subprotocols:
      - SSH_SHELL_SESSION
      - SSH_SCP_UP
      - SSH_SCP_DOWN

- name: Move the service to another port
  wallix.bastion.device_service:
    device_name: srv-linux-01
    service_name: SSH
    port: 2222

- name: Remove a service
  wallix.bastion.device_service:
    device_name: srv-linux-01
    service_name: SSH
    state: absent
"""

RETURN = r"""
service:
  description:
    - The service as returned by the Bastion API after the change.
    - In check mode, the expected service. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f6db068020af9005056b66c8b
    service_name: SSH
    protocol: SSH
    port: 22
    connection_policy: SSH
    subprotocols: [SSH_SHELL_SESSION, SSH_SCP_UP, SSH_SCP_DOWN]
    global_domains: []
    url: /services/1a0f6db068020af9005056b66c8b
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the service already existed and O(state=present)
  type: list
  elements: str
  sample: [port]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
    find_parent,
)

# The API rejects these in a PUT ("Additional properties are not allowed").


def main():
    module = BastionModule(
        argument_spec=dict(
            device_name=dict(type="str", required=True),
            service_name=dict(type="str", required=True),
            connection_policy=dict(type="str"),
            port=dict(type="int"),
            protocol=dict(type="str", choices=["SSH", "RAWTCPIP", "RDP", "RLOGIN", "TELNET", "VNC"]),
            global_domains=dict(type="list", elements="str"),
            subprotocols=dict(type="list", elements="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    device_id = find_parent(module, "devices", "device_name", module.params["device_name"], label="device")
    if device_id is None:
        module.exit_json(changed=False, service=None, diff=dict(before={}, after={}))
    resource = BastionResource(
        module,
        path="devices/%s/services" % device_id,
        name_field="service_name",
        fields=("service_name", "connection_policy", "port", "protocol", "global_domains", "subprotocols"),
        set_fields=("global_domains", "subprotocols"),
        result_key="service",
        required_on_create=("connection_policy", "port", "protocol"),
        create_only_fields=("protocol",),
        exclude_on_update=("service_name", "protocol"),
        update_query="force=true",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
