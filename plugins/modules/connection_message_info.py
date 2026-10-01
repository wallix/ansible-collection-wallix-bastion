#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: connection_message_info
short_description: Get the connection messages of a WALLIX Bastion
version_added: 1.1.0
description:
  - Return one connection message by name, or every connection message of the Bastion.
  - Equivalent of the C(wallix-bastion_connection_message) Terraform data source.
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
  message_name:
    description:
      - Name of the message to return. Without it, all messages are returned.
    type: str
    choices: [login_en, login_fr, login_de, login_es, login_ru, motd_en, motd_fr, motd_de, motd_es, motd_ru]
"""

EXAMPLES = r"""
- name: Get the English login warning
  wallix.bastion.connection_message_info:
    message_name: login_en
  register: result

- name: Show it
  ansible.builtin.debug:
    msg: "{{ result.connection_messages[0].message }}"

- name: Get every connection message
  wallix.bastion.connection_message_info:
  register: all_messages
"""

RETURN = r"""
connection_messages:
  description:
    - Matching connection messages, as returned by the Bastion API.
  returned: always
  type: list
  elements: dict
  sample:
    - message_name: login_en
      message: |
        WARNING: Access to this system is restricted to duly authorized users only.
      url: https://bastion.example.com/api/v3.12/connectionmessages/login_en
"""

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule

MESSAGE_NAMES = ["login_en", "login_fr", "login_de", "login_es", "login_ru",
                 "motd_en", "motd_fr", "motd_de", "motd_es", "motd_ru"]


def main():
    module = BastionModule(
        argument_spec=dict(message_name=dict(type="str", choices=MESSAGE_NAMES)),
        supports_check_mode=True,
    )
    name = module.params["message_name"]
    try:
        if name:
            found = module.client.get("connectionmessages/%s" % name)
            messages = [found] if found else []
        else:
            messages = module.client.get("connectionmessages") or []
        module.exit_json(changed=False, connection_messages=messages)
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)


if __name__ == "__main__":
    main()
