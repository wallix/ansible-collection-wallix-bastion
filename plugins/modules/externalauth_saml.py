#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: externalauth_saml
short_description: Manage SAML external authentications on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete a SAML identity provider used as external authentication on a WALLIX Bastion.
  - Equivalent of the C(wallix-bastion_externalauth_saml) Terraform resource.
  - The service provider details of the Bastion (C(sp_metadata), C(sp_entity_id), ...) to declare
    on the identity provider are returned in RV(externalauth).
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
  idp_metadata:
    description:
      - XML metadata of the identity provider. It must contain the signing certificate of the
        identity provider and a single sign-on service.
      - Required when the external authentication does not exist yet and O(state=present).
    type: str
  timeout:
    description:
      - Timeout of the authentication, in seconds, between V(1) and V(900).
      - The C(timeout) field of the API. O(timeout) is the timeout of the requests to the Bastion.
      - Required when the external authentication does not exist yet and O(state=present).
    type: float
  claim_customization:
    description:
      - Names of the SAML attributes holding the user properties.
      - Required when the external authentication does not exist yet and O(state=present).
      - When set, replaces the whole mapping, suboptions left unset are removed.
    type: dict
    suboptions:
      username:
        description: Attribute holding the user name.
        type: str
        required: true
      displayname:
        description: Attribute holding the display name.
        type: str
      email:
        description: Attribute holding the email address.
        type: str
      language:
        description: Attribute holding the preferred language.
        type: str
      group:
        description: Attribute holding the groups.
        type: str
  description:
    description:
      - Description of the external authentication.
    type: str
  certificate:
    description:
      - PEM certificate the Bastion signs its SAML requests with, with O(private_key). Use V("") to remove it.
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
      - V(on_create) sends O(certificate), O(private_key) and O(passphrase) only when the external
        authentication is created, or when one of them is set on one side only (set here and empty
        on the Bastion, or V("") here and set on the Bastion).
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
- name: Declare a SAML identity provider
  wallix.bastion.externalauth_saml:
    authentication_name: corp-idp
    idp_metadata: "{{ lookup('ansible.builtin.url', 'https://idp.example.com/metadata.xml', split_lines=false) }}"
    timeout: 30
    claim_customization:
      username: uid
      email: mail
      group: memberOf
  register: idp

- name: Show the metadata to declare the Bastion on the identity provider
  ansible.builtin.debug:
    msg: "{{ idp.externalauth.sp_metadata }}"

- name: Remove the SAML identity provider
  wallix.bastion.externalauth_saml:
    authentication_name: corp-idp
    state: absent
"""

RETURN = r"""
externalauth:
  description:
    - The external authentication as returned by the Bastion API after the change, without its private key.
    - Certificates are returned as their subject.
    - In check mode, the expected external authentication. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f767d044e6138005056b66c8b
    authentication_name: corp-idp
    type: SAML
    description: ""
    grouping_id: ""
    timeout: 30.0
    certificate: ""
    idp_metadata: "<?xml version=\"1.0\"?><md:EntityDescriptor ...>...</md:EntityDescriptor>"
    idp_entity_id: https://idp.example.com/saml
    saml_request_url: https://idp.example.com/saml/sso
    saml_request_method: HTTP-Redirect
    claim_customization: {username: uid, email: mail, group: memberOf}
    sp_metadata: "<?xml version=\"1.0\"?><md:EntityDescriptor ...>...</md:EntityDescriptor>"
    sp_entity_id: https://bastion.example.com/api/saml/metadata
    sp_assertion_consumer_service: https://bastion.example.com/api/saml
    sp_single_logout_service: https://bastion.example.com/api/saml/logout
    url: https://bastion.example.com/api/v3.12/externalauths/1a0f767d044e6138005056b66c8b
changed_fields:
  description:
    - Options that differed from the Bastion and were updated. Contains the secret options that
      were sent when O(update_password=always).
  returned: when the external authentication already existed and O(state=present)
  type: list
  elements: str
  sample: [claim_customization]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)

FIELDS = ("authentication_name", "idp_metadata", "timeout", "claim_customization", "description",
          "certificate", "private_key", "passphrase")
SECRETS = ("private_key", "passphrase")
# Not returned as sent: the private key comes back as "********", the certificate as its subject.
WRITE_ONLY = ("certificate", "private_key")


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


class SamlResource(ExternalAuthResource):
    def desired(self):
        desired = super(SamlResource, self).desired()
        if "claim_customization" in desired:
            # The API refuses null claims: unset suboptions are left out, which removes them.
            desired["claim_customization"] = dict(
                (k, v) for k, v in desired["claim_customization"].items() if v is not None)
        return desired


def main():
    module = BastionModule(
        argument_spec=dict(
            authentication_name=dict(type="str", required=True),
            idp_metadata=dict(type="str"),
            timeout=dict(type="float"),
            claim_customization=dict(
                type="dict",
                options=dict(
                    username=dict(type="str", required=True),
                    displayname=dict(type="str"),
                    email=dict(type="str"),
                    language=dict(type="str"),
                    group=dict(type="str"),
                ),
            ),
            description=dict(type="str"),
            certificate=dict(type="str"),
            private_key=dict(type="str", no_log=True),
            passphrase=dict(type="str", no_log=True),
            update_password=dict(type="str", choices=["always", "on_create"], default="on_create", no_log=False),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        required_by=dict(passphrase="private_key"),
        supports_check_mode=True,
    )
    timeout = module.params["timeout"]
    if timeout is not None and not 1 <= timeout <= 900:
        module.fail_json(msg="timeout must be between 1 and 900 seconds")
    resource = SamlResource(
        module,
        types=("SAML",),
        write_only=WRITE_ONLY,
        fields=FIELDS,
        required_on_create=("idp_metadata", "timeout", "claim_customization"),
        secret_fields=SECRETS,
        update_secrets=module.params["update_password"] == "always",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
