#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: authdomain_azuread
short_description: Manage Microsoft Entra ID (Azure AD) authentication domains on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete an authentication domain of type C(AzureAD) on a WALLIX Bastion.
  - An authentication domain is a user directory. Users of the domain log in through its external
    authentications (Microsoft Entra ID configured as a SAML identity provider, see M(wallix.bastion.externalauth_saml)),
    and get their Bastion user groups from the mappings of the domain, see M(wallix.bastion.authdomain_mapping).
  - The Bastion signs in to Microsoft Entra ID (OAuth client credentials) as the app registration given by
    O(client_id), O(entity_id) and O(client_secret) (or O(certificate) and O(private_key)). It does so when the domain
    is created, so creation fails if these credentials are wrong or the Bastion cannot reach Microsoft Entra ID.
  - Equivalent of the C(wallix-bastion_authdomain_azuread) Terraform resource.
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
      - Name of the authentication domain. Identifies the domain on the Bastion.
      - The module fails if a domain of this name exists with another type (AD, LDAP, SAML).
    type: str
    required: true
  auth_domain_name:
    description:
      - Name of the directory domain, for example C(corp.example.com).
      - Required when the domain does not exist yet.
    type: str
  default_email_domain:
    description:
      - Email domain given to users of the domain without an email address, for example C(example.com).
      - Required when the domain does not exist yet.
    type: str
  default_language:
    description:
      - Language given to users of the domain without a language.
      - Required when the domain does not exist yet.
    type: str
    choices: [de, en, es, fr, ru]
  external_auths:
    description:
      - Names of the external authentications (Microsoft Entra ID SAML identity providers) users of the
        domain authenticate against, in the order they are tried.
      - They must exist and all be of the same type.
      - Required when the domain does not exist yet. The list replaces the current one.
    type: list
    elements: str
  secondary_auth:
    description:
      - Names of the external authentications used as a second authentication factor, in order.
      - The list replaces the current one; V([]) removes them all.
    type: list
    elements: str
  description:
    description:
      - Description of the domain.
    type: str
  is_default:
    description:
      - Whether this is the default authentication domain, used when users log in without a domain.
    type: bool
  client_id:
    description:
      - Application (client) ID of the app registration the Bastion uses to read the groups of the users.
      - Required when the domain does not exist yet.
    type: str
  entity_id:
    description:
      - Directory (tenant) ID of the Microsoft Entra ID tenant.
      - Required when the domain does not exist yet.
    type: str
  client_secret:
    description:
      - Client secret of the app registration.
      - Treated as a secret, never returned and never compared. See O(update_password).
    type: str
  certificate:
    description:
      - Certificate of the app registration, to authenticate with a certificate instead of O(client_secret).
      - Treated as a secret, never returned and never compared. See O(update_password).
    type: str
  private_key:
    description:
      - Private key of O(certificate).
      - Treated as a secret, never returned and never compared. See O(update_password).
    type: str
  passphrase:
    description:
      - Passphrase of O(private_key).
      - Treated as a secret, never returned and never compared. See O(update_password).
    type: str
  update_password:
    description:
      - V(on_create) sends O(client_secret), O(certificate), O(private_key) and O(passphrase) only when the domain
        is created.
      - V(always) sends them on every run, which then always reports a change.
    type: str
    choices: [always, on_create]
    default: on_create
  label:
    description:
      - Text of the button users click on the login page to authenticate with this domain.
      - Required when the domain does not exist yet.
    type: str
  state:
    description:
      - Whether the domain should exist.
      - The Bastion refuses to delete a domain that still has mappings; remove them first with
        M(wallix.bastion.authdomain_mapping).
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
seealso:
  - module: wallix.bastion.authdomain_azuread_info
  - module: wallix.bastion.authdomain_mapping
"""

EXAMPLES = r"""
- name: Let users log in with Microsoft Entra ID
  wallix.bastion.authdomain_azuread:
    domain_name: corp-entra
    auth_domain_name: corp.onmicrosoft.com
    default_email_domain: example.com
    default_language: en
    external_auths: [entra-saml]
    label: Sign in with Microsoft
    client_id: 87654321-4321-4321-4321-210987654321
    entity_id: 12345678-1234-1234-1234-123456789012
    client_secret: "{{ entra_client_secret }}"

- name: Rotate the client secret
  wallix.bastion.authdomain_azuread:
    domain_name: corp-entra
    client_secret: "{{ new_entra_client_secret }}"
    update_password: always

- name: Remove the domain
  wallix.bastion.authdomain_azuread:
    domain_name: corp-entra
    state: absent
"""

RETURN = r"""
authdomain:
  description:
    - The authentication domain as returned by the Bastion API after the change, without the secret options.
    - In check mode, the expected domain. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f76784f6e92be005056b66c8b
    domain_name: corp-entra
    type: AzureAD
    description: ""
    is_default: false
    auth_domain_name: corp.onmicrosoft.com
    external_auths: [entra-saml]
    secondary_auth: []
    default_language: en
    default_email_domain: example.com
    mappings: []
    label: Sign in with Microsoft
    client_id: 87654321-4321-4321-4321-210987654321
    entity_id: 12345678-1234-1234-1234-123456789012
    url: https://bastion.example.com/api/v3.12/authdomains/1a0f76784f6e92be005056b66c8b
changed_fields:
  description:
    - Options that differed from the Bastion and were updated.
    - Contains the secret options sent because of O(update_password=always).
  returned: when the domain already existed and O(state=present)
  type: list
  elements: str
  sample: [label]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)

DOMAIN_TYPE = "AzureAD"
SECRETS = ("client_secret", "certificate", "private_key", "passphrase")
MODULES = dict(AD="authdomain_ad", LDAP="authdomain_ldap", SAML="authdomain_saml", AzureAD="authdomain_azuread")
FIELDS = (
    "domain_name", "auth_domain_name", "default_email_domain", "default_language", "external_auths",
    "secondary_auth", "description", "is_default", "label", "client_id", "entity_id",
) + SECRETS


class AuthDomainResource(BastionResource):
    """One type of /authdomains. The type is sent with every write: a PUT with another type converts the domain."""

    def read(self):
        current = super(AuthDomainResource, self).read()
        if current is not None and current.get("type") != DOMAIN_TYPE:
            self.module.fail_json(msg="authentication domain %s exists with type %s, not %s; manage it with wallix.bastion.%s" % (
                self.name, current.get("type"), DOMAIN_TYPE, MODULES.get(current.get("type"), "authdomain_*")))
        return current

    def normalize(self, obj):
        # Never hand back what the API returns for the secrets (masked or in clear).
        return {k: v for k, v in obj.items() if k not in SECRETS}

    def body(self, values):
        return dict(values, type=DOMAIN_TYPE)


def main():
    module = BastionModule(
        argument_spec=dict(
            domain_name=dict(type="str", required=True),
            auth_domain_name=dict(type="str"),
            default_email_domain=dict(type="str"),
            default_language=dict(type="str", choices=["de", "en", "es", "fr", "ru"]),
            external_auths=dict(type="list", elements="str"),
            secondary_auth=dict(type="list", elements="str"),
            description=dict(type="str"),
            is_default=dict(type="bool"),
            label=dict(type="str"),
            client_id=dict(type="str"),
            entity_id=dict(type="str"),
            client_secret=dict(type="str", no_log=True),
            certificate=dict(type="str", no_log=True),
            private_key=dict(type="str", no_log=True),
            passphrase=dict(type="str", no_log=True),
            update_password=dict(type="str", choices=["always", "on_create"], default="on_create", no_log=False),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        required_by=dict(passphrase="private_key"),
        supports_check_mode=True,
    )
    resource = AuthDomainResource(
        module,
        path="authdomains",
        name_field="domain_name",
        fields=FIELDS,
        result_key="authdomain",
        required_on_create=("auth_domain_name", "default_email_domain", "default_language", "external_auths", "label",
                            "client_id", "entity_id"),
        secret_fields=SECRETS,
        update_secrets=module.params["update_password"] == "always",
        # PUT merges the fields it gets; ?force=true makes it replace lists instead of appending to them.
        merge_on_update=False,
        update_query="force=true",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
