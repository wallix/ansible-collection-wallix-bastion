#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: application_info
short_description: Get applications from a WALLIX Bastion
version_added: 1.1.0
description:
  - Return one application by name, or every application of the Bastion.
  - Equivalent of the C(wallix-bastion_application) Terraform data source.
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
      - Name of the application to return. Without it, all applications are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one application
  wallix.bastion.application_info:
    application_name: erp-client
  register: result

- name: Show its jump server cluster
  ansible.builtin.debug:
    msg: "{{ result.applications[0].target }}"

- name: List every application
  wallix.bastion.application_info:
  register: all_applications
"""

RETURN = r"""
applications:
  description:
    - Matching applications, as returned by the Bastion API. Empty when O(application_name) matches no application.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f7683227aa4b3005056b66c8b
      application_name: intranet
      category: web_application
      connection_policy: WEBAPP
      description: ""
      application_url: https://intranet.example.com/login
      login_button_selector: null
      login_form_url: null
      allow_non_post_form: false
      global_domains: []
      local_domains: []
      tags: [{key: env, value: prod}]
      last_connection: null
      url: https://bastion.example.com/api/v3.12/applications/1a0f7683227aa4b3005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, run_info


def main():
    module = BastionModule(
        argument_spec=dict(application_name=dict(type="str")),
        supports_check_mode=True,
    )
    run_info(module, path="applications", name_field="application_name", result_key="applications")


if __name__ == "__main__":
    main()
