#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: externalauth_saml_info
short_description: Get SAML external authentications from a WALLIX Bastion
version_added: 1.1.0
description:
  - Return one SAML external authentication by name, or every SAML external authentication of the Bastion.
  - Equivalent of the C(wallix-bastion_externalauth_saml) Terraform data source.
  - External authentications of other types are not returned.
  - Like the data source, the secret fields (C(private_key), C(passphrase)) are not returned.
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
  authentication_name:
    description:
      - Name of the external authentication to return. Without it, all SAML external authentications are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one SAML external authentication
  wallix.bastion.externalauth_saml_info:
    authentication_name: corp-idp
  register: result

- name: Fail if it is missing
  ansible.builtin.assert:
    that: result.externalauths | length == 1

- name: List every SAML external authentication
  wallix.bastion.externalauth_saml_info:
  register: all_saml
"""

RETURN = r"""
externalauths:
  description:
    - Matching external authentications, as returned by the Bastion API without the secret fields.
      Empty when O(authentication_name) matches no SAML external authentication.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f767d044e6138005056b66c8b
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
"""

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule

TYPES = ("SAML",)
SECRETS = ("private_key", "passphrase")


def main():
    module = BastionModule(
        argument_spec=dict(authentication_name=dict(type="str")),
        supports_check_mode=True,
    )
    name = module.params["authentication_name"]
    try:
        # Every type of external authentication lives in the same collection: keep this one.
        if name:
            found = module.client.find("externalauths", "authentication_name", name)
            found = [found] if found else []
        else:
            found = module.client.get("externalauths") or []
        objects = [module.client.get("externalauths/%s" % o["id"]) or o if name else o
                   for o in found if o.get("type") in TYPES]
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)
    module.exit_json(changed=False, externalauths=[
        dict((k, v) for k, v in o.items() if k not in SECRETS) for o in objects])


if __name__ == "__main__":
    main()
