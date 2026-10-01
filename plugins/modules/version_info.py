#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: version_info
short_description: Get the version of a WALLIX Bastion
version_added: 1.1.0
description:
  - Return the version of a WALLIX Bastion and of its REST API.
  - Equivalent of the C(wallix-bastion_version) Terraform data source.
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
options: {}
notes:
  - The Terraform data source returns the decimal versions as strings; this module returns them as numbers,
    as the API does.
"""

EXAMPLES = r"""
- name: Get the Bastion version
  wallix.bastion.version_info:
  register: result

- name: Require WALLIX Bastion 12.4 or later
  ansible.builtin.assert:
    that: result.version.wab_version_decimal >= 12.004
"""

RETURN = r"""
version:
  description:
    - The versions, as returned by the Bastion API.
  returned: always
  type: dict
  contains:
    version:
      description: Version of the API used by the module, see O(api_version).
      type: str
      sample: v3.12
    version_decimal:
      description: O(api_version) as a number.
      type: float
      sample: 3.012
    wab_version:
      description: Major and minor version of the Bastion.
      type: str
      sample: "12.4"
    wab_form_factor:
      description: Form factor of the Bastion, for example V(appliance).
      type: str
      sample: appliance
    wab_version_decimal:
      description: RV(version.wab_version) as a number, minor version on three digits.
      type: float
      sample: 12.004
    wab_version_hotfix:
      description: Full version of the Bastion, hotfix included.
      type: str
      sample: 12.4.1
    wab_version_hotfix_decimal:
      description: RV(version.wab_version_hotfix) as a number.
      type: float
      sample: 12.004001
    wab_complete_version:
      description: Full version with build number and date.
      type: str
      sample: 12.4.1 (build 9685.40600-master; 2026-07-08)
"""

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule


def main():
    module = BastionModule(argument_spec=dict(), supports_check_mode=True)
    try:
        module.exit_json(changed=False, version=module.client.call("GET", "version", expected=(200,)).json())
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)


if __name__ == "__main__":
    main()
