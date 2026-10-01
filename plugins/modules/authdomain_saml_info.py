#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: authdomain_saml_info
short_description: Get SAML authentication domains from a WALLIX Bastion
version_added: 1.1.0
description:
  - Return one authentication domain of type C(SAML) by name, or every authentication domain of type C(SAML).
  - Equivalent of the C(wallix-bastion_authdomain_saml) Terraform data source.
author:
  - WALLIX (@wallix)
extends_documentation_fragment:
  - wallix.bastion.connection
attributes:
  check_mode:
    description: Can run in check_mode and return changed status prediction without modifying target.
    support: full
    details: This module never changes anything.
  diff_mode:
    description: Will return details on what has changed (or possibly needs changing in check_mode), when in diff mode.
    support: none
options:
  domain_name:
    description:
      - Name of the authentication domain to return. Without it, all domains of type C(SAML) are returned.
    type: str
seealso:
  - module: wallix.bastion.authdomain_saml
"""

EXAMPLES = r"""
- name: Get one SAML domain
  wallix.bastion.authdomain_saml_info:
    domain_name: corp-sso
  register: result

- name: Show the IdP-initiated login URL
  ansible.builtin.debug:
    var: result.authdomains[0].idp_initiated_url
"""

RETURN = r"""
authdomains:
  description:
    - Matching authentication domains of type C(SAML), as returned by the Bastion API.
    - Empty when O(domain_name) matches no domain, or a domain of another type.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f76784f6e92be005056b66c8b
      domain_name: corp-sso
      type: SAML
      description: ""
      is_default: false
      auth_domain_name: sso.example.com
      external_auths: [corp-idp]
      secondary_auth: []
      default_language: en
      default_email_domain: example.com
      mappings:
        - id: 1a0f768a6439af09005056b66c8b
          domain: corp-sso
          user_group: linux-admins
          external_group: linux-admins
          url: https://bastion.example.com/api/v3.12/authdomains/1a0f76784f6e92be005056b66c8b/mappings/1a0f768a6439af09005056b66c8b
      label: Sign in with Corp SSO
      idp_initiated_url: https://bastion.example.com/api/v3.12/saml?domain=corp-sso&redirect=true
      force_authn: false
      url: https://bastion.example.com/api/v3.12/authdomains/1a0f76784f6e92be005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule

DOMAIN_TYPE = "SAML"


def main():
    module = BastionModule(
        argument_spec=dict(domain_name=dict(type="str")),
        supports_check_mode=True,
    )
    try:
        name = module.params["domain_name"]
        if name:
            found = module.client.find("authdomains", "domain_name", name)
            objects = [module.client.get("authdomains/%s" % found["id"]) or found] if found else []
        else:
            objects = module.client.get("authdomains") or []
        module.exit_json(changed=False, authdomains=[o for o in objects if o.get("type") == DOMAIN_TYPE])
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)


if __name__ == "__main__":
    main()
