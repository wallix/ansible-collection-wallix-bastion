#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: authdomain_mapping
short_description: Map directory groups to user groups on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create or delete the mapping of a group of an authentication domain (a directory) to a Bastion user group.
    Members of the directory group get the user group, and its profile, when they log in.
  - Works with every type of authentication domain (M(wallix.bastion.authdomain_ad), M(wallix.bastion.authdomain_ldap),
    M(wallix.bastion.authdomain_saml), M(wallix.bastion.authdomain_azuread)).
  - Equivalent of the C(wallix-bastion_authdomain_mapping) Terraform resource.
  - A mapping is identified by the domain, O(user_group) and O(external_group) together, since the Bastion allows
    several mappings per user group and per directory group. There is nothing else to update. To map a user group to
    another directory group, add the new mapping and remove the old one.
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
  domain_name:
    description:
      - Name of the authentication domain, which must exist.
      - The Terraform resource takes the id of the domain instead (C(domain_id)).
    type: str
    required: true
  user_group:
    description:
      - Name of the Bastion user group. It must exist and have a profile (see M(wallix.bastion.usergroup)).
    type: str
    required: true
  external_group:
    description:
      - The group as the directory names it, for example the distinguished name of an LDAP or Active Directory group
        (C(CN=Linux Admins,OU=Groups,DC=corp,DC=example,DC=com)), or the group claim value for SAML.
      - Compared without regard to case, like the Bastion does.
    type: str
    required: true
  state:
    description:
      - Whether the mapping should exist.
    type: str
    choices: [present, absent]
    default: present
seealso:
  - module: wallix.bastion.authdomain_mapping_info
"""

EXAMPLES = r"""
- name: Give the Linux administrators of the directory the linux-admins user group
  wallix.bastion.authdomain_mapping:
    domain_name: corp
    user_group: linux-admins
    external_group: CN=Linux Admins,OU=Groups,DC=corp,DC=example,DC=com

- name: Remove the mapping
  wallix.bastion.authdomain_mapping:
    domain_name: corp
    user_group: linux-admins
    external_group: CN=Linux Admins,OU=Groups,DC=corp,DC=example,DC=com
    state: absent
"""

RETURN = r"""
mapping:
  description:
    - The mapping as returned by the Bastion API.
    - In check mode, the expected mapping. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f768a6439af09005056b66c8b
    domain: corp
    user_group: linux-admins
    external_group: CN=Linux Admins,OU=Groups,DC=corp,DC=example,DC=com
    url: https://bastion.example.com/api/v3.12/authdomains/1a0f76781900a85d005056b66c8b/mappings/1a0f768a6439af09005056b66c8b
changed_fields:
  description: Always empty, a mapping has nothing to update.
  returned: when the mapping already existed and O(state=present)
  type: list
  elements: str
  sample: []
"""

from urllib.parse import quote

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
    find_parent,
)


class MappingResource(BastionResource):
    """A mapping is the pair (user_group, external_group) inside one domain; the API refuses duplicates."""

    def read(self):
        external = self.module.params["external_group"].lower()
        results = self.client.get("%s?q=user_group=%s" % (self.path, quote(self.name, safe=""))) or []
        for found in results:
            if found.get("user_group") == self.name and str(found.get("external_group", "")).lower() == external:
                return self.client.get(self.object_path(found["id"])) or found
        return None

    def differences(self, current, desired):
        return []


def main():
    module = BastionModule(
        argument_spec=dict(
            domain_name=dict(type="str", required=True),
            user_group=dict(type="str", required=True),
            external_group=dict(type="str", required=True),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    domain_id = find_parent(module, "authdomains", "domain_name", module.params["domain_name"],
                            label="authentication domain")
    if domain_id is None:
        module.exit_json(changed=False, mapping=None, diff=dict(before={}, after={}))
    resource = MappingResource(
        module,
        path="authdomains/%s/mappings" % domain_id,
        name_field="user_group",
        fields=("user_group", "external_group"),
        result_key="mapping",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
