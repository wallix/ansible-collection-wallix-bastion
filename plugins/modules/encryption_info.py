#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: encryption_info
short_description: Get the encryption state of a WALLIX Bastion
version_added: 1.1.0
description:
  - Return the encryption state of the Bastion. It is a singleton, so the module takes no option.
  - Equivalent of the C(wallix-bastion_encryption) Terraform data source.
  - The passphrase is never returned by the Bastion.
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
- name: Get the encryption state
  wallix.bastion.encryption_info:
  register: result
"""

RETURN = r"""
encryption:
  description:
    - The encryption state as returned by the Bastion API.
  returned: always
  type: dict
  contains:
    seal_state:
      description: V(need_setup), V(sealed) or V(unsealed) (API v3.12).
      type: str
      returned: with API v3.12
    encryption_mode:
      description: V(need_setup), V(unprotected), V(passphrase), or V([hidden]) (API v3.12).
      type: str
      returned: with API v3.12
    encryption:
      description: Encryption state (API v3.8), V(ready) once set up.
      type: str
      returned: with API v3.8
    enabled:
      description: Whether the encryption is set up and unlocked, like the C(enabled) attribute of the Terraform data source.
      type: bool
      returned: always
  sample:
    seal_state: unsealed
    encryption_mode: passphrase
    enabled: true
"""

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule


def status(obj):
    obj = dict(obj or {})
    if "seal_state" in obj:
        obj["enabled"] = obj["seal_state"] == "unsealed"
    else:
        obj["enabled"] = obj.get("encryption") == "ready"
    return obj


def main():
    module = BastionModule(argument_spec=dict(), supports_check_mode=True)
    try:
        module.exit_json(changed=False, encryption=status(module.client.get("encryption")))
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)


if __name__ == "__main__":
    main()
