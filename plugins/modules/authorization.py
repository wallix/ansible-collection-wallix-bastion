#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: authorization
short_description: Manage authorizations on a WALLIX Bastion
version_added: 1.0.0
description:
  - Create, update or delete an authorization on a WALLIX Bastion.
  - An authorization gives the members of a user group access to the targets of a target group
    (sessions, password retrieval, or both), optionally subject to approval.
  - Equivalent of the C(wallix-bastion_authorization) Terraform resource.
author:
  - WALLIX (@wallix)
extends_documentation_fragment:
  - wallix.bastion.connection
attributes:
  check_mode:
    description: Can run in check_mode and return changed status prediction without modifying target.
    support: full
  diff_mode:
    description: Will return details on what has changed (or possibly needs changing in check_mode), when in diff mode.
    support: full
options:
  authorization_name:
    description:
      - Name of the authorization. Identifies the authorization on the Bastion.
    type: str
    required: true
  user_group:
    description:
      - Name of the user group the authorization applies to.
      - Required when the authorization does not exist yet and O(state=present).
      - Cannot be changed once the authorization exists; delete and recreate it instead.
      - The Bastion allows one authorization per pair of user group and target group.
    type: str
  target_group:
    description:
      - Name of the target group the authorization gives access to.
      - Required when the authorization does not exist yet and O(state=present).
      - Cannot be changed once the authorization exists; delete and recreate it instead.
    type: str
  description:
    description:
      - Description of the authorization.
    type: str
  authorize_sessions:
    description:
      - Whether members can open sessions on the targets. Requires O(subprotocols).
      - The Bastion enables it when it is not set on creation.
    type: bool
  subprotocols:
    description:
      - Subprotocols allowed in sessions, for example V(SSH_SHELL_SESSION), V(SSH_SCP_UP), V(SFTP_SESSION),
        V(RDP) or V(RDP_CLIPBOARD_UP). Order does not matter.
      - When set, replaces all the subprotocols of the authorization. The Bastion requires at least one, even
        when sessions are not authorized, so it cannot be emptied once set.
    type: list
    elements: str
  authorize_password_retrieval:
    description:
      - Whether members can check out the passwords of the target group's password retrieval accounts.
      - The Bastion enables it when it is not set on creation; set it to V(false) to grant sessions only.
    type: bool
  authorize_session_sharing:
    description:
      - Whether members can invite other users to their sessions.
    type: bool
  session_sharing_mode:
    description:
      - What invited users can do in a shared session.
    type: str
    choices: [view_only, view_control]
  is_critical:
    description:
      - Whether sessions opened through this authorization are flagged as critical.
    type: bool
  is_recorded:
    description:
      - Whether sessions opened through this authorization are recorded.
    type: bool
  approval_required:
    description:
      - Whether access requires the approval of an O(approvers) member.
      - Setting it to V(false) makes the Bastion reset O(approvers), O(active_quorum) and O(inactive_quorum);
        do not set those options together with O(approval_required=false).
    type: bool
  approvers:
    description:
      - Names of the user groups whose members can approve access requests. Order does not matter.
      - When set, replaces all the approvers of the authorization.
    type: list
    elements: str
  active_quorum:
    description:
      - Number of approvals needed during the timeframes of the user group.
      - The Bastion sets it to V(-1) when approval is not required.
    type: int
  inactive_quorum:
    description:
      - Number of approvals needed outside the timeframes of the user group, same values as O(active_quorum).
    type: int
  approval_timeout:
    description:
      - Minutes an approval request stays valid. V(0) means no timeout.
    type: int
  has_comment:
    description:
      - Whether users can add a comment to their approval request.
    type: bool
  mandatory_comment:
    description:
      - Whether the comment is mandatory.
    type: bool
  has_ticket:
    description:
      - Whether users can add a ticket number to their approval request.
    type: bool
  mandatory_ticket:
    description:
      - Whether the ticket number is mandatory.
    type: bool
  single_connection:
    description:
      - Whether an approval allows a single connection only.
    type: bool
  state:
    description:
      - Whether the authorization should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - The authorization is looked up by O(authorization_name), so it cannot be renamed with this module.
"""

EXAMPLES = r"""
- name: Let Linux administrators open SSH sessions on the Linux servers
  wallix.bastion.authorization:
    authorization_name: linux-admins-on-linux-servers
    user_group: linux-admins
    target_group: linux-servers
    authorize_sessions: true
    authorize_password_retrieval: false
    subprotocols: [SSH_SHELL_SESSION, SSH_SCP_UP, SSH_SCP_DOWN]
    is_recorded: true

- name: Require the approval of a security officer
  wallix.bastion.authorization:
    authorization_name: linux-admins-on-linux-servers
    approval_required: true
    approvers: [security-officers]
    active_quorum: 1
    inactive_quorum: 1
    has_comment: true
    mandatory_comment: true

- name: Remove an authorization
  wallix.bastion.authorization:
    authorization_name: linux-admins-on-linux-servers
    state: absent
"""

RETURN = r"""
authorization:
  description:
    - The authorization as returned by the Bastion API after the change.
    - In check mode, the expected authorization. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f6ea31fcb3e15005056b66c8b
    authorization_name: linux-admins-on-linux-servers
    user_group: linux-admins
    target_group: linux-servers
    description: ""
    authorize_sessions: true
    subprotocols: [SSH_SHELL_SESSION, SSH_SCP_UP, SSH_SCP_DOWN]
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
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the authorization already existed and O(state=present)
  type: list
  elements: str
  sample: [subprotocols]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)


def main():
    module = BastionModule(
        argument_spec=dict(
            authorization_name=dict(type="str", required=True),
            user_group=dict(type="str"),
            target_group=dict(type="str"),
            description=dict(type="str"),
            authorize_sessions=dict(type="bool"),
            subprotocols=dict(type="list", elements="str"),
            authorize_password_retrieval=dict(type="bool", no_log=False),
            authorize_session_sharing=dict(type="bool"),
            session_sharing_mode=dict(type="str", choices=["view_only", "view_control"]),
            is_critical=dict(type="bool"),
            is_recorded=dict(type="bool"),
            approval_required=dict(type="bool"),
            approvers=dict(type="list", elements="str"),
            active_quorum=dict(type="int"),
            inactive_quorum=dict(type="int"),
            approval_timeout=dict(type="int"),
            has_comment=dict(type="bool"),
            mandatory_comment=dict(type="bool"),
            has_ticket=dict(type="bool"),
            mandatory_ticket=dict(type="bool"),
            single_connection=dict(type="bool"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    resource = BastionResource(
        module,
        path="authorizations",
        name_field="authorization_name",
        fields=("authorization_name", "user_group", "target_group", "description", "authorize_sessions",
                "subprotocols", "authorize_password_retrieval", "authorize_session_sharing",
                "session_sharing_mode", "is_critical", "is_recorded", "approval_required", "approvers",
                "active_quorum", "inactive_quorum", "approval_timeout", "has_comment", "mandatory_comment",
                "has_ticket", "mandatory_ticket", "single_connection"),
        set_fields=("subprotocols", "approvers"),
        result_key="authorization",
        required_on_create=("user_group", "target_group"),
        create_only_fields=("user_group", "target_group"),
        # PUT keeps the fields it does not get, rejects user_group and target_group, and
        # appends to lists (subprotocols, approvers) unless forced.
        merge_on_update=False,
        exclude_on_update=("user_group", "target_group"),
        update_query="force=true",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
