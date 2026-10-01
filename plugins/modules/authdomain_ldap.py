#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: authdomain_ldap
short_description: Manage LDAP authentication domains on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete an authentication domain of type C(LDAP) on a WALLIX Bastion.
  - An authentication domain is a user directory. Users of the domain log in through its external
    authentications (usually LDAP servers), and get their Bastion user groups from
    the mappings of the domain, see M(wallix.bastion.authdomain_mapping).
  - Equivalent of the C(wallix-bastion_authdomain_ldap) Terraform resource.
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
      - The module fails if a domain of this name exists with another type (AD, SAML, AzureAD).
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
      - Names of the external authentications (usually LDAP servers) users of the
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
  check_x509_san_email:
    description:
      - Whether to check the email of the Subject Alternative Name of X.509 certificates.
    type: bool
  display_name_attribute:
    description:
      - Directory attribute holding the display name of the users.
    type: str
  email_attribute:
    description:
      - Directory attribute holding the email address of the users.
    type: str
  group_attribute:
    description:
      - Directory attribute holding the groups of the users, for example C(memberOf).
    type: str
  language_attribute:
    description:
      - Directory attribute holding the language of the users.
    type: str
  pubkey_attribute:
    description:
      - Directory attribute holding the SSH public keys of the users.
    type: str
  san_domain_name:
    description:
      - Domain name of the Subject Alternative Name of X.509 certificates.
    type: str
  x509_condition:
    description:
      - Condition X.509 certificates must match.
    type: str
  x509_search_filter:
    description:
      - Directory search filter used to find the user of an X.509 certificate.
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
  - module: wallix.bastion.authdomain_ldap_info
  - module: wallix.bastion.authdomain_mapping
"""

EXAMPLES = r"""
- name: Declare the corporate LDAP directory
  wallix.bastion.authdomain_ldap:
    domain_name: corp
    auth_domain_name: corp.example.com
    default_email_domain: example.com
    default_language: en
    external_auths: [ldap01, ldap02]
    group_attribute: memberOf
    description: Corporate LDAP directory

- name: Use a single LDAP server
  wallix.bastion.authdomain_ldap:
    domain_name: corp
    external_auths: [ldap01]

- name: Remove the domain
  wallix.bastion.authdomain_ldap:
    domain_name: corp
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
    id: 1a0f76781900a85d005056b66c8b
    domain_name: corp
    type: LDAP
    description: Corporate LDAP directory
    is_default: false
    auth_domain_name: corp.example.com
    external_auths: [ldap01, ldap02]
    secondary_auth: []
    default_language: en
    default_email_domain: example.com
    mappings: []
    certificate_authority: ""
    enable_ca: false
    check_x509_san_email: false
    san_domain_name: ""
    x509_condition: ""
    x509_search_filter: ""
    group_attribute: memberOf
    display_name_attribute: ""
    pubkey_attribute: ""
    email_attribute: ""
    language_attribute: ""
    url: https://bastion.example.com/api/v3.12/authdomains/1a0f76781900a85d005056b66c8b
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the domain already existed and O(state=present)
  type: list
  elements: str
  sample: [external_auths]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)

DOMAIN_TYPE = "LDAP"
MODULES = dict(AD="authdomain_ad", LDAP="authdomain_ldap", SAML="authdomain_saml", AzureAD="authdomain_azuread")
FIELDS = (
    "domain_name", "auth_domain_name", "default_email_domain", "default_language", "external_auths",
    "secondary_auth", "description", "is_default", "check_x509_san_email", "display_name_attribute",
    "email_attribute", "group_attribute", "language_attribute", "pubkey_attribute", "san_domain_name",
    "x509_condition", "x509_search_filter",
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
            check_x509_san_email=dict(type="bool"),
            display_name_attribute=dict(type="str"),
            email_attribute=dict(type="str"),
            group_attribute=dict(type="str"),
            language_attribute=dict(type="str"),
            pubkey_attribute=dict(type="str", no_log=False),
            san_domain_name=dict(type="str"),
            x509_condition=dict(type="str"),
            x509_search_filter=dict(type="str"),
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
        required_on_create=("auth_domain_name", "default_email_domain", "default_language", "external_auths"),
        # PUT merges the fields it gets; ?force=true makes it replace lists instead of appending to them.
        merge_on_update=False,
        update_query="force=true",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
