#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: config_x509_info
short_description: Get the X.509 configuration of a WALLIX Bastion
version_added: 1.1.0
description:
  - Return the X.509 configuration of the Bastion. It is a singleton, so the module takes no option.
  - Equivalent of the C(wallix-bastion_config_x509) Terraform data source.
  - Certificates are returned as their subject, as the API returns them. The private key is not returned.
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
- name: Get the X.509 configuration
  wallix.bastion.config_x509_info:
  register: result
"""

RETURN = r"""
config_x509:
  description:
    - The X.509 configuration as returned by the Bastion API, without the private key.
  returned: always
  type: dict
  contains:
    ca_certificate:
      description: Subject of the CA certificate for X.509 authentication of users.
      type: str
      returned: always
    server_public_key:
      description: Subject of the certificate the GUI and the API serve.
      type: str
      returned: always
    enable:
      description: Whether X.509 authentication of users is enabled.
      type: bool
      returned: always
    default:
      description: Whether the Bastion uses its default configuration.
      type: bool
      returned: always
  sample:
    ca_certificate: /C=FR/O=WALLIX/CN=Users CA
    server_public_key: /C=FR/O=WALLIX/CN=bastion.example.com
    enable: false
    default: false
"""

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule


def main():
    module = BastionModule(argument_spec=dict(), supports_check_mode=True)
    try:
        config = module.client.get("config/x509") or {"default": True}
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)
    config.pop("server_private_key", None)
    module.exit_json(changed=False, config_x509=config)


if __name__ == "__main__":
    main()
