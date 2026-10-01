#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: authdomain_mapping_info
short_description: Get the group mappings of an authentication domain from a WALLIX Bastion
version_added: 1.1.0
description:
  - Return the mappings of the groups of an authentication domain to Bastion user groups, optionally only those of one
    user group or one directory group.
  - Equivalent of the C(wallix-bastion_authdomain_mapping) Terraform data source, which takes the id of the domain
    (C(domain_id)) and returns the mapping of one user group.
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
  domain_name:
    description:
      - Name of the authentication domain, of any type. The module fails if it does not exist.
    type: str
    required: true
  user_group:
    description:
      - Only return the mappings to this Bastion user group.
    type: str
  external_group:
    description:
      - Only return the mappings of this directory group, compared without regard to case.
    type: str
seealso:
  - module: wallix.bastion.authdomain_mapping
"""

EXAMPLES = r"""
- name: Get every mapping of a domain
  wallix.bastion.authdomain_mapping_info:
    domain_name: corp
  register: result

- name: Get the directory groups mapped to linux-admins
  wallix.bastion.authdomain_mapping_info:
    domain_name: corp
    user_group: linux-admins
  register: result

- name: Show them
  ansible.builtin.debug:
    msg: "{{ result.mappings | map(attribute='external_group') }}"
"""

RETURN = r"""
mappings:
  description:
    - Matching mappings, as returned by the Bastion API. Empty when none match.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f768a6439af09005056b66c8b
      domain: corp
      user_group: linux-admins
      external_group: CN=Linux Admins,OU=Groups,DC=corp,DC=example,DC=com
      url: https://bastion.example.com/api/v3.12/authdomains/1a0f76781900a85d005056b66c8b/mappings/1a0f768a6439af09005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, find_parent


def main():
    module = BastionModule(
        argument_spec=dict(
            domain_name=dict(type="str", required=True),
            user_group=dict(type="str"),
            external_group=dict(type="str"),
        ),
        supports_check_mode=True,
    )
    params = module.params
    domain_id = find_parent(module, "authdomains", "domain_name", params["domain_name"], label="authentication domain")
    try:
        mappings = module.client.get("authdomains/%s/mappings" % domain_id) or []
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)
    if params["user_group"] is not None:
        mappings = [m for m in mappings if m.get("user_group") == params["user_group"]]
    if params["external_group"] is not None:
        external = params["external_group"].lower()
        mappings = [m for m in mappings if str(m.get("external_group", "")).lower() == external]
    module.exit_json(changed=False, mappings=mappings)


if __name__ == "__main__":
    main()
