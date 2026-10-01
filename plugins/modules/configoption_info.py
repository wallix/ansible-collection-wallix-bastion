#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: configoption_info
short_description: Get configuration options from a WALLIX Bastion
version_added: 1.1.0
description:
  - Return the options of one configuration of a WALLIX Bastion, for example the RDP proxy (C(rdpproxy))
    or its session manager (C(sesman)), or every configuration.
  - Equivalent of the C(wallix-bastion_configoption) Terraform data source.
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
  config_id:
    description:
      - Configuration to return, by name (RV(configoptions[].config_name), for example V(rdpproxy))
        or by RV(configoptions[].id).
      - Without it, every configuration is returned.
    type: str
  options_list:
    description:
      - Sections of the configuration to return, for example V(globals). Without it, all sections are returned.
      - A section that does not exist is silently left out.
      - Only used with O(config_id).
    type: list
    elements: str
notes:
  - The Terraform data source returns each section as a JSON string; this module returns them as data.
"""

EXAMPLES = r"""
- name: Get the global settings of the RDP proxy
  wallix.bastion.configoption_info:
    config_id: rdpproxy
    options_list: [globals]
  register: result

- name: Show the RDP port
  ansible.builtin.debug:
    msg: "{{ (result.configoptions[0].options[0].options | selectattr('name', '==', 'port') | first).value }}"

- name: List every configuration
  wallix.bastion.configoption_info:
  register: all_configs
"""

RETURN = r"""
configoptions:
  description:
    - Matching configurations, as returned by the Bastion API. Empty when O(config_id) matches no configuration.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: Identifier of the configuration.
      type: str
      sample: e83581f9d308901ee740404a1d2a09f13838bc08040f650b83a7325cb6f3f144
    config_name:
      description: Name of the configuration.
      type: str
      sample: rdpproxy
    name:
      description: Display name of the configuration.
      type: str
      sample: RDP proxy
    date:
      description: Last change of the configuration.
      type: str
      sample: "2026-07-09 11:37:32"
    options:
      description: Sections of the configuration, each with its C(name) and its C(options), a list of C(name)/C(value) pairs.
      type: list
      elements: dict
      sample:
        - name: globals
          options:
            - name: port
              value: 3389
            - name: handshake_timeout
              value: 10
"""

from urllib.parse import quote

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule


def main():
    module = BastionModule(
        argument_spec=dict(
            config_id=dict(type="str"),
            options_list=dict(type="list", elements="str"),
        ),
        required_by=dict(options_list="config_id"),
        supports_check_mode=True,
    )
    config_id = module.params["config_id"]
    sections = module.params["options_list"]
    try:
        if config_id:
            path = "configoptions/%s" % quote(config_id, safe="")
            if sections:
                path += "?options=" + ",".join(quote(s, safe="") for s in sections)
            found = module.client.get(path)
            configs = [found] if found else []
        else:
            configs = module.client.get("configoptions") or []
        module.exit_json(changed=False, configoptions=configs)
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)


if __name__ == "__main__":
    main()
