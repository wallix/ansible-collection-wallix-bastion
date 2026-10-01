#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: config_wsm_info
short_description: Get the Web Session Manager configuration of a WALLIX Bastion
version_added: 1.1.0
description:
  - Return the Web Session Manager configuration of the Bastion. It is a singleton, so the module takes no option.
  - Equivalent of the C(wallix-bastion_config_wsm) Terraform data source.
  - Requires API version V(v3.12) or later.
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
- name: Get the Web Session Manager configuration
  wallix.bastion.config_wsm_info:
  register: result
"""

RETURN = r"""
config_wsm:
  description:
    - The WSM configuration as returned by the Bastion API, without the private JWS key.
    - Unset values are returned as V("").
  returned: always
  type: dict
  sample:
    hostname: wsm.example.com
    jwe_public: ""
    jws_public: "-----BEGIN PUBLIC KEY-----\nMIGbMBAGByqGSM49AgEGBSuBBAAjA4GGAAQB...\n-----END PUBLIC KEY-----\n"
"""

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule


def main():
    module = BastionModule(argument_spec=dict(), supports_check_mode=True)
    if module.client.api_version == "v3.8":
        module.fail_json(msg="config_wsm_info requires API version v3.12 or later")
    try:
        config = module.client.get("config/wsm") or {}
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)
    config.pop("jws_private", None)
    for field in ("hostname", "jwe_public"):
        if config.get(field) is None:
            config[field] = ""
    module.exit_json(changed=False, config_wsm=config)


if __name__ == "__main__":
    main()
