#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: domain_info
short_description: Get global domains from a WALLIX Bastion
version_added: 1.0.0
description:
  - Return one global domain by name, or every global domain of the Bastion.
  - Equivalent of the C(wallix-bastion_domain) Terraform data source.
  - Like the data source, the secret fields (C(ca_private_key), C(password_change_plugin_parameters),
    C(vault_plugin_parameters)) are not returned.
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
      - Name of the domain to return. Without it, all global domains are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one domain
  wallix.bastion.domain_info:
    domain_name: corp
  register: result

- name: Show the public key of its SSH certificate authority
  ansible.builtin.debug:
    msg: "{{ result.domains[0].ca_public_key }}"
  when: result.domains | length == 1

- name: List every global domain
  wallix.bastion.domain_info:
  register: all_domains
"""

RETURN = r"""
domains:
  description:
    - Matching domains, as returned by the Bastion API without the secret fields.
      Empty when O(domain_name) matches no domain.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f6dbf308b89e1005056b66c8b
      domain_name: corp
      domain_real_name: corp.example.com
      description: Corporate domain
      admin_account: svc-pwchange
      kerberos: null
      enable_password_change: true
      password_change_policy: default
      password_change_plugin: Unix
      ca_public_key: ""
      vault_plugin: null
      is_editable: true
      url: https://bastion.example.com/api/v3.12/domains/1a0f6dbf308b89e1005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, run_info

SECRETS = ("ca_private_key", "password_change_plugin_parameters", "vault_plugin_parameters")


def main():
    module = BastionModule(
        argument_spec=dict(domain_name=dict(type="str")),
        supports_check_mode=True,
    )
    run_info(module, path="domains", name_field="domain_name", result_key="domains",
             normalize=lambda obj: {k: v for k, v in obj.items() if k not in SECRETS})


if __name__ == "__main__":
    main()
