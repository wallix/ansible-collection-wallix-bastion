#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: authorization_info
short_description: Get authorizations from a WALLIX Bastion
version_added: 1.0.0
description:
  - Return one authorization by name, or every authorization of the Bastion.
  - Equivalent of the C(wallix-bastion_authorization) Terraform data source.
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
  authorization_name:
    description:
      - Name of the authorization to return. Without it, all authorizations are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one authorization
  wallix.bastion.authorization_info:
    authorization_name: linux-admins-on-linux-servers
  register: result

- name: Show its subprotocols
  ansible.builtin.debug:
    var: result.authorizations[0].subprotocols

- name: List every authorization
  wallix.bastion.authorization_info:
  register: all_authorizations

- name: Keep those of linux-admins
  ansible.builtin.debug:
    msg: "{{ all_authorizations.authorizations | selectattr('user_group', 'equalto', 'linux-admins') | list }}"
"""

RETURN = r"""
authorizations:
  description:
    - Matching authorizations, as returned by the Bastion API.
    - Empty when O(authorization_name) matches no authorization.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f6ea31fcb3e15005056b66c8b
      authorization_name: linux-admins-on-linux-servers
      user_group: linux-admins
      target_group: linux-servers
      description: ""
      authorize_sessions: true
      subprotocols: [SSH_SHELL_SESSION]
      authorize_password_retrieval: false
      authorize_session_sharing: false
      session_sharing_mode: null
      is_critical: false
      is_recorded: true
      approval_required: false
      approvers: []
      active_quorum: -1
      inactive_quorum: -1
      approval_timeout: 0
      has_comment: false
      mandatory_comment: false
      has_ticket: false
      mandatory_ticket: false
      single_connection: false
      url: https://bastion.example.com/api/v3.12/authorizations/1a0f6ea31fcb3e15005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, run_info


def main():
    module = BastionModule(
        argument_spec=dict(authorization_name=dict(type="str")),
        supports_check_mode=True,
    )
    run_info(module, path="authorizations", name_field="authorization_name", result_key="authorizations")


if __name__ == "__main__":
    main()
