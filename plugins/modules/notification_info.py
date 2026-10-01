#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: notification_info
short_description: Get notifications from a WALLIX Bastion
version_added: 1.1.0
description:
  - Return one notification by name, or every notification of the Bastion.
  - Equivalent of the C(wallix-bastion_notification) Terraform data source.
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
  notification_name:
    description:
      - Name of the notification to return. Without it, all notifications are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one notification
  wallix.bastion.notification_info:
    notification_name: ops-mail
  register: result

- name: List every notification
  wallix.bastion.notification_info:
  register: all_items
"""

RETURN = r"""
notifications:
  description:
    - Matching notifications, as returned by the Bastion API. Empty when O(notification_name) matches no notification.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f76994902158e005056b66c8b
      notification_name: ops-mail
      description: Mail the operations team
      enabled: true
      type: email
      destination: ops@example.com
      language: en
      events:
      - daily_reporting
      - raid_error
      url: https://bastion.example.com/api/v3.12/notifications/1a0f76994902158e005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, run_info


def main():
    module = BastionModule(
        argument_spec=dict(notification_name=dict(type="str")),
        supports_check_mode=True,
    )
    run_info(module, path="notifications", name_field="notification_name", result_key="notifications")


if __name__ == "__main__":
    main()
