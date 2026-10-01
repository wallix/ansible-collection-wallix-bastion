#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: authdomain_saml
short_description: Manage SAML authentication domains on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete an authentication domain of type C(SAML) on a WALLIX Bastion.
  - An authentication domain is a user directory. Users of the domain log in through its external
    authentications (SAML identity providers, see M(wallix.bastion.externalauth_saml)), and get their Bastion
    user groups from the mappings of the domain, see M(wallix.bastion.authdomain_mapping).
  - Equivalent of the C(wallix-bastion_authdomain_saml) Terraform resource.
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
      - The module fails if a domain of this name exists with another type (AD, LDAP, AzureAD).
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
      - Names of the external authentications (SAML identity providers) users of the
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
  label:
    description:
      - Text of the button users click on the login page to authenticate with this domain.
      - Required when the domain does not exist yet.
    type: str
  force_authn:
    description:
      - Whether the identity provider must authenticate users again even if they have a session (SAML C(ForceAuthn)).
    type: bool
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
  - module: wallix.bastion.authdomain_saml_info
  - module: wallix.bastion.authdomain_mapping
"""

EXAMPLES = r"""
- name: Declare a SAML identity provider
  wallix.bastion.externalauth_saml:
    authentication_name: corp-idp
    idp_metadata: "{{ lookup('ansible.builtin.file', 'idp-metadata.xml') }}"
    timeout: 10

- name: Let users log in with it
  wallix.bastion.authdomain_saml:
    domain_name: corp-sso
    auth_domain_name: sso.example.com
    default_email_domain: example.com
    default_language: en
    external_auths: [corp-idp]
    label: Sign in with Corp SSO

- name: Ask the identity provider to authenticate users every time
  wallix.bastion.authdomain_saml:
    domain_name: corp-sso
    force_authn: true

- name: Remove the domain
  wallix.bastion.authdomain_saml:
    domain_name: corp-sso
    state: absent
"""

RETURN = r"""
authdomain:
  description:
    - The authentication domain as returned by the Bastion API after the change.
    - In check mode, the expected domain. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f76784f6e92be005056b66c8b
    domain_name: corp-sso
    type: SAML
    description: ""
    is_default: false
    auth_domain_name: sso.example.com
    external_auths: [corp-idp]
    secondary_auth: []
    default_language: en
    default_email_domain: example.com
    mappings: []
    label: Sign in with Corp SSO
    idp_initiated_url: https://bastion.example.com/api/v3.12/saml?domain=corp-sso&redirect=true
    force_authn: false
    url: https://bastion.example.com/api/v3.12/authdomains/1a0f76784f6e92be005056b66c8b
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the domain already existed and O(state=present)
  type: list
  elements: str
  sample: [label]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)

DOMAIN_TYPE = "SAML"
MODULES = dict(AD="authdomain_ad", LDAP="authdomain_ldap", SAML="authdomain_saml", AzureAD="authdomain_azuread")
FIELDS = (
    "domain_name", "auth_domain_name", "default_email_domain", "default_language", "external_auths",
    "secondary_auth", "description", "is_default", "label", "force_authn",
)


class AuthDomainResource(BastionResource):
    """One type of /authdomains. The type is sent with every write: a PUT with another type converts the domain."""

    def read(self):
        current = super(AuthDomainResource, self).read()
        if current is not None and current.get("type") != DOMAIN_TYPE:
            self.module.fail_json(msg="authentication domain %s exists with type %s, not %s; manage it with wallix.bastion.%s" % (
                self.name, current.get("type"), DOMAIN_TYPE, MODULES.get(current.get("type"), "authdomain_*")))
        return current

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
            force_authn=dict(type="bool"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    resource = AuthDomainResource(
        module,
        path="authdomains",
        name_field="domain_name",
        fields=FIELDS,
        result_key="authdomain",
        required_on_create=("auth_domain_name", "default_email_domain", "default_language", "external_auths", "label"),
        # PUT merges the fields it gets; ?force=true makes it replace lists instead of appending to them.
        merge_on_update=False,
        update_query="force=true",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
