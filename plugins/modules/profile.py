#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: profile
short_description: Manage user profiles on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete a user profile on a WALLIX Bastion.
  - A profile gives its users rights on the Bastion web interface and API, and can restrict the
    IP addresses they connect from and the user and target groups they see.
  - Equivalent of the C(wallix-bastion_profile) Terraform resource.
  - The built-in profiles (V(user), V(product_administrator), ...) cannot be changed.
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
  profile_name:
    description:
      - Name of the profile. Identifies the profile on the Bastion.
    type: str
    required: true
  description:
    description:
      - Description of the profile.
    type: str
  gui_features:
    description:
      - Rights of the profile's users on each part of the web interface and API.
      - When set, replaces all the rights of the profile; a right left unset is not granted.
    type: dict
    suboptions:
      wab_audit: &view
        description: Right on this part.
        type: str
        choices: [view]
      system_audit: *view
      users: &view_modify
        description: Right on this part.
        type: str
        choices: [view, modify]
      user_groups: *view_modify
      devices: *view_modify
      target_groups: *view_modify
      authorizations: *view_modify
      profiles: &modify
        description: Right on this part.
        type: str
        choices: [modify]
      wab_settings: *view_modify
      system_settings: *modify
      backup: &execute
        description: Right on this part.
        type: str
        choices: [execute]
      approval: *view_modify
      credential_recovery: *execute
  gui_transmission:
    description:
      - Rights the profile's users can give to other profiles, at most their own O(gui_features).
      - When set, replaces all the transmission rights of the profile; a right left unset is not transmitted.
      - When the profile is created without it, the Bastion gives it the same rights as O(gui_features).
    type: dict
    suboptions:
      system_audit: *view
      users: *view_modify
      user_groups: *view_modify
      devices: *view_modify
      target_groups: *view_modify
      authorizations: *view_modify
      profiles: *modify
      wab_settings: *view_modify
      system_settings: *modify
      backup: *execute
      approval: *view_modify
      credential_recovery: *execute
  dashboards:
    description:
      - Dashboards shown to the profile's users, for example V(audit) or V(opsadmin). Order does not matter.
      - When set, replaces all the dashboards of the profile. Use V([]) to remove all dashboards.
    type: list
    elements: str
  ip_limitation:
    description:
      - IP address or network the profile's users must connect from, for example V(10.0.0.0/8).
      - V("") removes the limitation.
    type: str
  target_access:
    description:
      - Whether the profile's users can connect to targets.
    type: bool
  target_groups_limitation:
    description:
      - Restrict the profile's users to some target groups.
    type: dict
    suboptions:
      enabled:
        description:
          - Whether the limitation applies. V(false) removes it.
        type: bool
        required: true
      target_groups:
        description:
          - Names of the target groups the users are limited to. Order does not matter.
          - Required by the Bastion when O(target_groups_limitation.enabled=true).
        type: list
        elements: str
      default_target_group:
        description:
          - Target group used by default, one of O(target_groups_limitation.target_groups).
          - When unset, the Bastion picks one.
        type: str
  user_groups_limitation:
    description:
      - Restrict the profile's users to some user groups.
    type: dict
    suboptions:
      enabled:
        description:
          - Whether the limitation applies. V(false) removes it.
        type: bool
        required: true
      user_groups:
        description:
          - Names of the user groups the users are limited to. Order does not matter.
        type: list
        elements: str
  state:
    description:
      - Whether the profile should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - The profile is looked up by O(profile_name), so it cannot be renamed with this module.
  - The Bastion refuses O(gui_transmission) rights that exceed O(gui_features), and rights that exceed
    those of the API user.
"""

EXAMPLES = r"""
- name: Profile of operators who manage devices and see audit data
  wallix.bastion.profile:
    profile_name: operators
    description: Device operators
    gui_features:
      wab_audit: view
      devices: modify
      target_groups: view
    gui_transmission:
      devices: view
    dashboards: [audit]
    ip_limitation: 10.0.0.0/8
    target_access: true
    target_groups_limitation:
      enabled: true
      target_groups: [linux-servers, windows-servers]
      default_target_group: linux-servers

- name: Remove the target group limitation
  wallix.bastion.profile:
    profile_name: operators
    target_groups_limitation:
      enabled: false

- name: Remove a profile
  wallix.bastion.profile:
    profile_name: operators
    state: absent
"""

RETURN = r"""
profile:
  description:
    - The profile as returned by the Bastion API after the change. Rights not granted are V(null).
    - In check mode, the expected profile. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f76a4310471af005056b66c8b
    profile_name: operators
    editable: true
    description: Device operators
    gui_features:
      wab_audit: view
      system_audit: null
      users: null
      user_groups: null
      devices: modify
      target_groups: view
      authorizations: null
      profiles: null
      wab_settings: null
      system_settings: null
      backup: null
      approval: null
      credential_recovery: null
    gui_transmission:
      system_audit: null
      users: null
      user_groups: null
      devices: view
      target_groups: null
      authorizations: null
      profiles: null
      wab_settings: null
      system_settings: null
      backup: null
      approval: null
      credential_recovery: null
    dashboards: [audit]
    ip_limitation: 10.0.0.0/8
    target_access: true
    target_groups_limitation:
      enabled: true
      target_groups: [linux-servers, windows-servers]
      default_target_group: linux-servers
    user_groups_limitation:
      enabled: false
    url: https://bastion.example.com/api/v3.12/profiles/1a0f76a4310471af005056b66c8b
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the profile already existed and O(state=present)
  type: list
  elements: str
  sample: [gui_features, dashboards]
"""

import json

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)

VIEW = ["view"]
VIEW_MODIFY = ["view", "modify"]
MODIFY = ["modify"]
EXECUTE = ["execute"]
TRANSMISSION_RIGHTS = dict(
    system_audit=VIEW, users=VIEW_MODIFY, user_groups=VIEW_MODIFY, devices=VIEW_MODIFY,
    target_groups=VIEW_MODIFY, authorizations=VIEW_MODIFY, profiles=MODIFY, wab_settings=VIEW_MODIFY,
    system_settings=MODIFY, backup=EXECUTE, approval=VIEW_MODIFY, credential_recovery=EXECUTE,
)
FEATURE_RIGHTS = dict(TRANSMISSION_RIGHTS, wab_audit=VIEW)

# Limitation option -> its list of group names.
LIMITATIONS = dict(target_groups_limitation="target_groups", user_groups_limitation="user_groups")


def rights_spec(rights):
    return dict(type="dict", options={k: dict(type="str", choices=v) for k, v in rights.items()})


def normalize_limitation(value, groups_key):
    """Canonical limitation: {"enabled": false}, or enabled with its group list sorted.

    The API omits the group list of an enabled limitation without groups.
    """
    if not isinstance(value, dict):
        return value
    if not value.get("enabled"):
        return {"enabled": False}
    value = dict(value)
    value[groups_key] = sorted(value.get(groups_key) or [])
    return value


def normalize_profile(obj):
    if obj is None:
        return None
    obj = dict(obj)
    for field, groups_key in LIMITATIONS.items():
        if field in obj:
            obj[field] = normalize_limitation(obj[field], groups_key)
    return obj


def _same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


class ProfileResource(BastionResource):

    def normalize(self, obj):
        return normalize_profile(obj)

    def desired(self):
        desired = super(ProfileResource, self).desired()
        for field, groups_key in LIMITATIONS.items():
            if field not in desired:
                continue
            value = {k: v for k, v in desired[field].items() if v is not None}
            if not value["enabled"]:
                extra = sorted(k for k in value if k != "enabled")
                if extra:
                    self.module.fail_json(msg="profile %s: %s require %s.enabled=true" % (
                        self.name, ", ".join("%s.%s" % (field, k) for k in extra), field))
            elif groups_key in value:
                value[groups_key] = sorted(value[groups_key])
            desired[field] = value
        return desired

    def differences(self, current, desired):
        changes = set(super(ProfileResource, self).differences(current, desired))
        for field in LIMITATIONS:
            if field in desired:
                # Only compare what was requested: the Bastion picks a default target group when none is given.
                cur = current.get(field) or {}
                wanted = desired[field]
                if wanted.get("enabled") and cur.get("enabled"):
                    same = all(_same(cur.get(k), v) for k, v in wanted.items())
                else:
                    same = bool(wanted.get("enabled")) == bool(cur.get("enabled"))
                if same:
                    changes.discard(field)
                else:
                    changes.add(field)
        return sorted(changes)

    def update(self, current, desired):
        desired = dict(desired)
        for field, groups_key in LIMITATIONS.items():
            wanted = desired.get(field)
            cur = current.get(field) or {}
            if wanted and wanted.get("enabled") and cur.get("enabled"):
                merged = dict(cur, **wanted)
                if groups_key in wanted and "default_target_group" not in wanted:
                    # The old default may not be one of the new groups: let the Bastion pick one.
                    merged.pop("default_target_group", None)
                desired[field] = merged
        return super(ProfileResource, self).update(current, desired)


def main():
    module = BastionModule(
        argument_spec=dict(
            profile_name=dict(type="str", required=True),
            description=dict(type="str"),
            gui_features=rights_spec(FEATURE_RIGHTS),
            gui_transmission=rights_spec(TRANSMISSION_RIGHTS),
            dashboards=dict(type="list", elements="str"),
            ip_limitation=dict(type="str"),
            target_access=dict(type="bool"),
            target_groups_limitation=dict(
                type="dict",
                options=dict(
                    enabled=dict(type="bool", required=True),
                    target_groups=dict(type="list", elements="str"),
                    default_target_group=dict(type="str"),
                ),
            ),
            user_groups_limitation=dict(
                type="dict",
                options=dict(
                    enabled=dict(type="bool", required=True),
                    user_groups=dict(type="list", elements="str"),
                ),
            ),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    resource = ProfileResource(
        module,
        path="profiles",
        name_field="profile_name",
        fields=("profile_name", "description", "gui_features", "gui_transmission", "dashboards",
                "ip_limitation", "target_access", "target_groups_limitation", "user_groups_limitation"),
        set_fields=("dashboards",),
        result_key="profile",
        update_query="force=true",
        exclude_on_update=("profile_name",),
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
