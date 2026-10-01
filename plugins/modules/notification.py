#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: notification
short_description: Manage notifications on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete a notification on a WALLIX Bastion.
  - A notification sends an email to a list of addresses when some events happen on the Bastion.
  - Equivalent of the C(wallix-bastion_notification) Terraform resource.
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
  notification_name:
    description:
      - Name of the notification. Identifies the notification on the Bastion.
    type: str
    required: true
  description:
    description:
      - Description of the notification.
    type: str
  enabled:
    description:
      - Whether the notification is sent.
      - Required when the notification does not exist yet and O(state=present).
    type: bool
  type:
    description:
      - How the notification is sent. The Bastion only supports V(email).
      - Required when the notification does not exist yet and O(state=present).
    type: str
    choices: [email]
  destination:
    description:
      - Email addresses the notification is sent to, separated by commas.
      - Required when the notification does not exist yet and O(state=present).
    type: str
  language:
    description:
      - Language of the notification.
      - Required when the notification does not exist yet and O(state=present).
    type: str
    choices: [de, en, es, fr, ru]
  events:
    description:
      - Events that trigger the notification. Order does not matter.
      - When set, replaces all the events of the notification. Use V([]) to remove all events.
    type: list
    elements: str
    choices:
      - cx_equipment
      - daily_reporting
      - disk_space_critical
      - external_storage_full
      - filesystem_full
      - integrity_error
      - licence_notifications
      - new_fingerprint
      - password_expired
      - pattern_found
      - primary_cx_failed
      - raid_error
      - rdp_outcxn_found
      - rdp_pattern_found
      - rdp_process_found
      - secondary_cx_failed
      - sessionlog_purge
      - watchdog_notifications
      - wrong_fingerprint
  state:
    description:
      - Whether the notification should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - The notification is looked up by O(notification_name), so it cannot be renamed with this module.
"""

EXAMPLES = r"""
- name: Mail the operations team about disk and RAID problems
  wallix.bastion.notification:
    notification_name: ops-mail
    description: Mail the operations team
    enabled: true
    type: email
    destination: ops@example.com,oncall@example.com
    language: en
    events: [disk_space_critical, filesystem_full, raid_error]

- name: Pause a notification
  wallix.bastion.notification:
    notification_name: ops-mail
    enabled: false

- name: Remove a notification
  wallix.bastion.notification:
    notification_name: ops-mail
    state: absent
"""

RETURN = r"""
notification:
  description:
    - The notification as returned by the Bastion API after the change.
    - In check mode, the expected notification. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f76994902158e005056b66c8b
    notification_name: ops-mail
    description: Mail the operations team
    enabled: true
    type: email
    destination: ops@example.com,oncall@example.com
    language: en
    events: [disk_space_critical, filesystem_full, raid_error]
    url: https://bastion.example.com/api/v3.12/notifications/1a0f76994902158e005056b66c8b
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the notification already existed and O(state=present)
  type: list
  elements: str
  sample: [events]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)

EVENTS = [
    "cx_equipment", "daily_reporting", "disk_space_critical", "external_storage_full", "filesystem_full",
    "integrity_error", "licence_notifications", "new_fingerprint", "password_expired", "pattern_found",
    "primary_cx_failed", "raid_error", "rdp_outcxn_found", "rdp_pattern_found", "rdp_process_found",
    "secondary_cx_failed", "sessionlog_purge", "watchdog_notifications", "wrong_fingerprint",
]


def main():
    module = BastionModule(
        argument_spec=dict(
            notification_name=dict(type="str", required=True),
            description=dict(type="str"),
            enabled=dict(type="bool"),
            type=dict(type="str", choices=["email"]),
            destination=dict(type="str"),
            language=dict(type="str", choices=["de", "en", "es", "fr", "ru"]),
            events=dict(type="list", elements="str", choices=EVENTS),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    resource = BastionResource(
        module,
        path="notifications",
        name_field="notification_name",
        fields=("notification_name", "description", "enabled", "type", "destination", "language", "events"),
        set_fields=("events",),
        result_key="notification",
        required_on_create=("enabled", "type", "destination", "language"),
        update_query="force=true",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
