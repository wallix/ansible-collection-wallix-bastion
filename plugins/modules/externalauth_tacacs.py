#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: externalauth_tacacs
short_description: Manage TACACS+ external authentications on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete a TACACS+ external authentication server on a WALLIX Bastion.
  - Equivalent of the C(wallix-bastion_externalauth_tacacs) Terraform resource.
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
  authentication_name:
    description:
      - Name of the external authentication. Identifies it on the Bastion.
      - External authentications of every type share the same names. The module fails if an
        external authentication of another type already has this name.
    type: str
    required: true
  host:
    description:
      - Host name or IP address of the TACACS+ server.
      - Required when the external authentication does not exist yet and O(state=present).
    type: str
  port:
    description:
      - Port of the TACACS+ server, usually V(49).
      - Required when the external authentication does not exist yet and O(state=present).
    type: int
  secret:
    description:
      - Secret shared with the TACACS+ server.
      - Required when the external authentication does not exist yet and O(state=present).
      - The Bastion never returns it, so it cannot be compared. See O(update_password).
    type: str
  description:
    description:
      - Description of the external authentication.
    type: str
  use_primary_auth_domain:
    description:
      - Whether to use the primary authentication domain.
    type: bool
  update_password:
    description:
      - V(on_create) sends O(secret) only when the external authentication is created.
      - V(always) sends it on every run, which then always reports a change.
    type: str
    choices: [always, on_create]
    default: on_create
  state:
    description:
      - Whether the external authentication should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - The Bastion refuses to delete an external authentication that an authentication domain uses.
"""

EXAMPLES = r"""
- name: Declare a TACACS+ server
  wallix.bastion.externalauth_tacacs:
    authentication_name: corp-tacacs
    host: tacacs.corp.example.com
    port: 49
    secret: "{{ vault_tacacs_secret }}"

- name: Rotate the shared secret
  wallix.bastion.externalauth_tacacs:
    authentication_name: corp-tacacs
    secret: "{{ vault_tacacs_new_secret }}"
    update_password: always

- name: Remove the TACACS+ server
  wallix.bastion.externalauth_tacacs:
    authentication_name: corp-tacacs
    state: absent
"""

RETURN = r"""
externalauth:
  description:
    - The external authentication as returned by the Bastion API after the change, without its secret.
    - In check mode, the expected external authentication. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f766c6d46c74e005056b66c8b
    authentication_name: corp-tacacs
    type: TACACS+
    description: ""
    grouping_id: ""
    host: tacacs.corp.example.com
    port: 49
    use_primary_auth_domain: false
    url: https://bastion.example.com/api/v3.12/externalauths/1a0f766c6d46c74e005056b66c8b
changed_fields:
  description:
    - Options that differed from the Bastion and were updated. Contains O(secret) when it was
      sent because O(update_password=always).
  returned: when the external authentication already existed and O(state=present)
  type: list
  elements: str
  sample: [description]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)

FIELDS = ("authentication_name", "host", "port", "secret", "description", "use_primary_auth_domain")
SECRETS = ("secret",)


def _is_set(value):
    return value not in (None, "")


class ExternalAuthResource(BastionResource):
    """One type of external authentication in the /externalauths collection shared by all types.

    The type is only sent on creation. PUT merges the fields it gets, so only the requested ones
    are sent. Write-only fields are only compared by "set or empty".
    """

    def __init__(self, module, types, write_only, **kwargs):
        self.types = tuple(types)
        self.write_only = frozenset(write_only)
        super(ExternalAuthResource, self).__init__(
            module, path="externalauths", name_field="authentication_name", result_key="externalauth",
            merge_on_update=False, **kwargs)

    def create_type(self, desired):
        return self.types[0]

    def read(self):
        current = super(ExternalAuthResource, self).read()
        if current is not None and current.get("type") not in self.types:
            self.module.fail_json(msg="external authentication %s already exists with type %s, not %s" % (
                self.name, current.get("type"), " or ".join(self.types)))
        return current

    def _write_only_to_send(self, current, desired):
        sent = set(f for f in self.write_only if f in desired and (
            self.update_secrets or _is_set(desired[f]) != _is_set(current.get(f))))
        if "passphrase" in desired and "private_key" in sent:
            sent.add("passphrase")
        return sent

    def differences(self, current, desired):
        changes = super(ExternalAuthResource, self).differences(current, desired)
        changes = set(f for f in changes if f not in self.write_only)
        return sorted(changes | self._write_only_to_send(current, desired))

    def create(self, desired):
        return super(ExternalAuthResource, self).create(dict(desired, type=self.create_type(desired)))

    def update(self, current, desired):
        # ensure() drops secrets from desired unless update_password=always; re-add the ones to send.
        requested = self.desired()
        sent = self._write_only_to_send(current, requested)
        values = dict((f, v) for f, v in requested.items()
                      if f not in self.write_only and f != "passphrase" or f in sent)
        for field in self.exclude_on_update:
            values.pop(field, None)
        path = self.object_path(current["id"])
        self.client.call("PUT", path, self.body(values))
        return self.normalize(self.client.get(path))


def main():
    module = BastionModule(
        argument_spec=dict(
            authentication_name=dict(type="str", required=True),
            host=dict(type="str"),
            port=dict(type="int"),
            secret=dict(type="str", no_log=True),
            description=dict(type="str"),
            use_primary_auth_domain=dict(type="bool"),
            update_password=dict(type="str", choices=["always", "on_create"], default="on_create", no_log=False),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    resource = ExternalAuthResource(
        module,
        types=("TACACS+",),
        write_only=SECRETS,
        fields=FIELDS,
        required_on_create=("host", "port", "secret"),
        secret_fields=SECRETS,
        update_secrets=module.params["update_password"] == "always",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
