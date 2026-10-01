#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: externalauth_ldap
short_description: Manage LDAP external authentications on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete an LDAP or Active Directory external authentication server on a WALLIX Bastion.
  - Equivalent of the C(wallix-bastion_externalauth_ldap) Terraform resource.
  - Authentication domains that use the server are managed with their own modules.
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
      - Host name or IP address of the LDAP server.
      - Required when the external authentication does not exist yet and O(state=present).
    type: str
  port:
    description:
      - Port of the LDAP server, for example V(389), or V(636) with O(is_ssl=true).
      - Required when the external authentication does not exist yet and O(state=present).
    type: int
  timeout:
    description:
      - Timeout of the connection to the server, in seconds.
      - The C(timeout) field of the API. O(timeout) is the timeout of the requests to the Bastion.
      - Required when the external authentication does not exist yet and O(state=present).
    type: float
  ldap_base:
    description:
      - Base DN of the searches, for example V(dc=example,dc=com).
      - Required when the external authentication does not exist yet and O(state=present).
    type: str
  login_attribute:
    description:
      - LDAP attribute holding the login of the users, for example V(sAMAccountName) or V(uid).
      - Required when the external authentication does not exist yet and O(state=present).
    type: str
  cn_attribute:
    description:
      - LDAP attribute holding the display name of the users, for example V(cn).
      - Required when the external authentication does not exist yet and O(state=present).
    type: str
  description:
    description:
      - Description of the external authentication.
    type: str
  is_active_directory:
    description:
      - Whether the server is a Microsoft Active Directory.
    type: bool
  is_anonymous_access:
    description:
      - Whether the Bastion binds anonymously to the server.
      - When V(false), O(login) and O(password) must be set. When V(true), they and the client
        certificate must be empty.
    type: bool
  is_protected_user:
    description:
      - Whether the users are members of the Active Directory Protected Users group.
    type: bool
  is_ssl:
    description:
      - Whether to connect with LDAPS.
    type: bool
  is_starttls:
    description:
      - Whether to use StartTLS.
    type: bool
  use_primary_auth_domain:
    description:
      - Whether to use the primary authentication domain.
    type: bool
  login:
    description:
      - DN or login the Bastion binds with, when O(is_anonymous_access=false).
    type: str
  password:
    description:
      - Password the Bastion binds with, when O(is_anonymous_access=false). Use V("") to remove it.
      - The Bastion never returns it, so only whether it is set is compared. See O(update_password).
    type: str
  ca_certificate:
    description:
      - PEM certificate of the authority that signed the certificate of the server. Use V("") to remove it.
      - The Bastion only returns the subject of the certificate, so only whether it is set is
        compared. See O(update_password).
    type: str
  certificate:
    description:
      - PEM client certificate the Bastion authenticates with, with O(private_key). Use V("") to remove it.
      - The Bastion only returns the subject of the certificate, so only whether it is set is
        compared. See O(update_password).
    type: str
  private_key:
    description:
      - PEM private key of O(certificate). Use V("") to remove it.
      - The Bastion never returns it, so only whether it is set is compared. See O(update_password).
    type: str
  passphrase:
    description:
      - Passphrase of O(private_key). Sent each time O(private_key) is.
    type: str
  update_password:
    description:
      - V(on_create) sends O(password), O(ca_certificate), O(certificate), O(private_key) and
        O(passphrase) only when the external authentication is created, or when one of them is
        set on one side only (set here and empty on the Bastion, or V("") here and set on the Bastion).
      - V(always) sends the ones that are set on every run, which then always reports a change.
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
- name: Declare an Active Directory server
  wallix.bastion.externalauth_ldap:
    authentication_name: corp-ad
    host: dc01.corp.example.com
    port: 636
    is_ssl: true
    is_active_directory: true
    timeout: 3
    ldap_base: dc=corp,dc=example,dc=com
    login_attribute: sAMAccountName
    cn_attribute: cn
    login: CN=svc-bastion,OU=Services,DC=corp,DC=example,DC=com
    password: "{{ vault_ad_bind_password }}"
    ca_certificate: "{{ lookup('ansible.builtin.file', 'corp-ca.pem') }}"

- name: Change the bind password
  wallix.bastion.externalauth_ldap:
    authentication_name: corp-ad
    password: "{{ vault_ad_new_bind_password }}"
    update_password: always

- name: Remove the LDAP server
  wallix.bastion.externalauth_ldap:
    authentication_name: corp-ad
    state: absent
"""

RETURN = r"""
externalauth:
  description:
    - The external authentication as returned by the Bastion API after the change, without its secrets.
    - Certificates are returned as their subject.
    - In check mode, the expected external authentication. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f766ccb90205c005056b66c8b
    authentication_name: corp-ad
    type: LDAP
    description: ""
    grouping_id: ""
    host: dc01.corp.example.com
    port: 636
    timeout: 3.0
    is_active_directory: true
    is_anonymous_access: false
    is_protected_user: false
    is_ssl: true
    is_starttls: false
    use_primary_auth_domain: false
    ldap_base: dc=corp,dc=example,dc=com
    login_attribute: sAMAccountName
    cn_attribute: cn
    login: CN=svc-bastion,OU=Services,DC=corp,DC=example,DC=com
    ca_certificate: /DC=com/DC=example/CN=Corp Root CA
    certificate: ""
    url: https://bastion.example.com/api/v3.12/externalauths/1a0f766ccb90205c005056b66c8b
changed_fields:
  description:
    - Options that differed from the Bastion and were updated. Contains the secret options that
      were sent when O(update_password=always).
  returned: when the external authentication already existed and O(state=present)
  type: list
  elements: str
  sample: [description, password]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)

FIELDS = (
    "authentication_name", "host", "port", "timeout", "ldap_base", "login_attribute", "cn_attribute",
    "description", "is_active_directory", "is_anonymous_access", "is_protected_user", "is_ssl",
    "is_starttls", "use_primary_auth_domain", "login",
    "password", "ca_certificate", "certificate", "private_key", "passphrase",
)
SECRETS = ("password", "private_key", "passphrase")
# Not returned as sent: secrets come back as "********", certificates as their subject.
WRITE_ONLY = ("password", "ca_certificate", "certificate", "private_key")


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
            timeout=dict(type="float"),
            ldap_base=dict(type="str"),
            login_attribute=dict(type="str"),
            cn_attribute=dict(type="str"),
            description=dict(type="str"),
            is_active_directory=dict(type="bool"),
            is_anonymous_access=dict(type="bool"),
            is_protected_user=dict(type="bool"),
            is_ssl=dict(type="bool"),
            is_starttls=dict(type="bool"),
            use_primary_auth_domain=dict(type="bool"),
            login=dict(type="str"),
            password=dict(type="str", no_log=True),
            ca_certificate=dict(type="str"),
            certificate=dict(type="str"),
            private_key=dict(type="str", no_log=True),
            passphrase=dict(type="str", no_log=True),
            update_password=dict(type="str", choices=["always", "on_create"], default="on_create", no_log=False),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        required_by=dict(passphrase="private_key"),
        supports_check_mode=True,
    )
    resource = ExternalAuthResource(
        module,
        types=("LDAP",),
        write_only=WRITE_ONLY,
        fields=FIELDS,
        required_on_create=("host", "port", "timeout", "ldap_base", "login_attribute", "cn_attribute"),
        secret_fields=SECRETS,
        update_secrets=module.params["update_password"] == "always",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
