#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: connection_message
short_description: Set the connection messages of a WALLIX Bastion
version_added: 1.1.0
description:
  - Set the text of a connection message of a WALLIX Bastion, the warning shown before login
    (C(login_*)) or the message of the day shown after it (C(motd_*)), in one language.
  - The Bastion always has every message, so they can only be changed, not created or deleted.
  - Equivalent of the C(wallix-bastion_connection_message) Terraform resource.
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
  message_name:
    description:
      - Which message to set, C(login) or C(motd) followed by the language.
    type: str
    required: true
    choices: [login_en, login_fr, login_de, login_es, login_ru, motd_en, motd_fr, motd_de, motd_es, motd_ru]
  message_text:
    description:
      - Text of the message, the C(message) field of the API. It is compared exactly, trailing new line included.
      - Not named C(message) like the API field and the Terraform attribute because Ansible reserves that option name.
    type: str
    required: true
  state:
    description:
      - Only V(present) is supported, since connection messages cannot be deleted.
    type: str
    choices: [present]
    default: present
"""

EXAMPLES = r"""
- name: Set the English login warning
  wallix.bastion.connection_message:
    message_name: login_en
    message_text: |
      WARNING: this system is restricted to authorized users of Example Corp.
"""

RETURN = r"""
connection_message:
  description:
    - The message as returned by the Bastion API after the change. In check mode, the expected message.
  returned: always
  type: dict
  sample:
    message_name: login_en
    message: |
      WARNING: this system is restricted to authorized users of Example Corp.
    url: https://bastion.example.com/api/v3.12/connectionmessages/login_en
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: always
  type: list
  elements: str
  sample: [message_text]
"""

from urllib.parse import quote

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule

MESSAGE_NAMES = ["login_en", "login_fr", "login_de", "login_es", "login_ru",
                 "motd_en", "motd_fr", "motd_de", "motd_es", "motd_ru"]


def main():
    module = BastionModule(
        argument_spec=dict(
            message_name=dict(type="str", required=True, choices=MESSAGE_NAMES),
            message_text=dict(type="str", required=True),
            state=dict(type="str", choices=["present"], default="present"),
        ),
        supports_check_mode=True,
    )
    name = module.params["message_name"]
    message = module.params["message_text"]
    path = "connectionmessages/%s" % quote(name, safe="")
    try:
        current = module.client.get(path)
        if current is None:
            module.fail_json(msg="connection message %s does not exist on this Bastion" % name)
        changed = current.get("message") != message
        after = current
        if changed:
            if module.check_mode:
                after = dict(current, message=message)
            else:
                # PUT only takes the text: the name is in the path.
                module.client.call("PUT", path, dict(message=message))
                after = module.client.get(path) or dict(current, message=message)
        module.exit_json(
            changed=changed,
            changed_fields=["message_text"] if changed else [],
            connection_message=after,
            diff=dict(before=dict(message=current.get("message")), after=dict(message=after.get("message"))),
        )
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)


if __name__ == "__main__":
    main()
