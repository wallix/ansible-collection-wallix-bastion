#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: application_localdomain_info
short_description: Get the local domains of an application from a WALLIX Bastion
version_added: 1.1.0
description:
  - Return one local domain of an application by name, or every local domain of the application.
  - Equivalent of the C(wallix-bastion_application_localdomain) Terraform data source.
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
  application_name:
    description:
      - Name of the application. The module fails if the application does not exist.
    type: str
    required: true
  domain_name:
    description:
      - Name of the local domain to return. Without it, all the local domains of the application are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get a local domain of an application
  wallix.bastion.application_localdomain_info:
    application_name: intranet
    domain_name: local
  register: result

- name: Show its admin account
  ansible.builtin.debug:
    msg: "{{ result.localdomains[0].admin_account }}"
"""

RETURN = r"""
localdomains:
  description:
    - Matching local domains, as returned by the Bastion API. Empty when O(domain_name) matches no local domain.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f7675bcc1a98d005056b66c8b
      domain_name: local
      description: Local accounts of the intranet
      admin_account: admin
      enable_password_change: false
      password_change_policy: null
      password_change_plugin: null
      password_change_plugin_parameters: null
      ca_private_key: ""
      ca_public_key: ""
      url: https://bastion.example.com/api/v3.12/applications/1a0f7672f874efd5005056b66c8b/localdomains/1a0f7675bcc1a98d005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, find_parent, run_info


def main():
    module = BastionModule(
        argument_spec=dict(
            application_name=dict(type="str", required=True),
            domain_name=dict(type="str"),
        ),
        supports_check_mode=True,
    )
    application_id = find_parent(module, "applications", "application_name", module.params["application_name"],
                                 label="application")
    run_info(module, path="applications/%s/localdomains" % application_id, name_field="domain_name",
             result_key="localdomains")


if __name__ == "__main__":
    main()
