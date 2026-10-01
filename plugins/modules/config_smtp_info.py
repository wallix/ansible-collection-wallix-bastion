#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: config_smtp_info
short_description: Get the SMTP configuration of a WALLIX Bastion
version_added: 1.1.0
description:
  - Return the SMTP configuration of the Bastion. It is a singleton, so the module takes no option.
  - Equivalent of the C(wallix-bastion_config_smtp) Terraform data source.
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
"""

EXAMPLES = r"""
- name: Get the SMTP configuration
  wallix.bastion.config_smtp_info:
  register: result
"""

RETURN = r"""
config_smtp:
  description:
    - The SMTP configuration as returned by the Bastion API, without the password.
  returned: always
  type: dict
  sample:
    protocol: starttls
    authentication_method: plain
    server: smtp.example.com
    port: 587
    postmaster_email: postmaster@example.com
    sender_name: WALLIX Bastion
    sender_email: bastion@example.com
    certificate_hash: ""
    user: smtp-user
"""

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule


def main():
    module = BastionModule(argument_spec=dict(), supports_check_mode=True)
    try:
        config = module.client.get("config/smtp") or {}
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)
    config.pop("password", None)
    module.exit_json(changed=False, config_smtp=config)


if __name__ == "__main__":
    main()
