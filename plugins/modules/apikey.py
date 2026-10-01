#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: apikey
short_description: Manage API keys on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete an API key of the WALLIX Bastion REST API.
  - Equivalent of the C(wallix-bastion_apikey) Terraform resource.
  - The Bastion generates the key value. It is returned once, when this module creates the key,
    in RV(apikey.apikey), and can never be read again. See the notes.
  - M(wallix.bastion.apikey_v2) manages the same keys with their profile and description.
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
  apikey_name:
    description:
      - Name of the API key. Identifies the key on the Bastion.
    type: str
    required: true
  ip_limitation:
    description:
      - Comma-separated list of IP addresses, without spaces, allowed to use the key, for example
        V(192.0.2.10,192.0.2.11). an empty string allows any address.
    type: str
  state:
    description:
      - Whether the API key should exist.
      - With V(absent), make sure O(apikey_name) is not the key your own automation authenticates with.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - The key value is a secret. It is only returned by the run that creates the key, not in check mode.
    Set C(no_log) to V(true) on the task and store the value right away, for example in a vault.
  - The Bastion gives the keys created by this module a default profile, visible with
    M(wallix.bastion.apikey_v2_info). Use M(wallix.bastion.apikey_v2) to choose it.
  - Keys are created with the profile the Bastion gives them by default. Use M(wallix.bastion.apikey_v2)
    to choose it.
  - To use the key, set O(bastion_token) to its value and
    O(bastion_user) to a user of the Bastion.
  - The key is looked up by O(apikey_name), so it cannot be renamed with this module.
"""

EXAMPLES = r"""
- name: Create an API key for the CI pipeline
  wallix.bastion.apikey:
    apikey_name: ci-pipeline
    ip_limitation: 192.0.2.10,192.0.2.11
  register: ci_key
  no_log: true

- name: Store the key value, only known on creation
  ansible.builtin.copy:
    content: "{{ ci_key.apikey.apikey }}"
    dest: /root/.bastion-ci-key
    mode: "0600"
  when: ci_key.apikey.apikey is defined
  no_log: true

- name: Remove an API key
  wallix.bastion.apikey:
    apikey_name: ci-pipeline
    state: absent
"""

RETURN = r"""
apikey:
  description:
    - The API key as returned by the Bastion API after the change.
    - In check mode, the expected key. V(null) when O(state=absent).
  returned: always
  type: dict
  contains:
    apikey:
      description:
        - The key value. Only returned when the key was created by this run; it can never be read again.
      returned: when the key was created, not in check mode
      type: str
      sample: EXAMPLE-api-key-returned-only-on-creation
  sample:
    id: 1a0f766d790f8b83005056b66c8b
    apikey_name: ci-pipeline
    apikey: EXAMPLE-api-key-returned-only-on-creation
    ip_limitation: 192.0.2.10,192.0.2.11
    url: https://bastion.example.com/api/v3.12/apikeys/1a0f766d790f8b83005056b66c8b
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the key already existed and O(state=present)
  type: list
  elements: str
  sample: [ip_limitation]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)


class APIKeyResource(BastionResource):
    """The Bastion returns the generated key once, in the X-Auth-Key header of the POST response.

    GET always masks it as "********", so it is dropped from every object read back.
    """

    def normalize(self, obj):
        if obj is None:
            return None
        return dict((k, v) for k, v in obj.items() if k != "apikey")

    def create(self, desired):
        resp = self.client.call("POST", self.path, self.body(desired))
        object_id = resp.header("X-Object-Id")
        created = self.normalize(self.client.get(self.object_path(object_id))) if object_id else self.read()
        if created is None:
            raise BastionError("%s %s not found after creation" % (self.result_key, self.name))
        key = resp.header("X-Auth-Key")
        if key:
            created["apikey"] = key
        return created


def main():
    module = BastionModule(
        argument_spec=dict(
            apikey_name=dict(type="str", required=True, no_log=False),
            ip_limitation=dict(type="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    resource = APIKeyResource(
        module,
        path="apikeys",
        name_field="apikey_name",
        fields=("apikey_name", "ip_limitation"),
        result_key="apikey",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
