#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: certificate_authority_info
short_description: Get certificate authorities from a WALLIX Bastion
version_added: 1.1.0
description:
  - Return one certificate authority by name, or every certificate authority of the Bastion.
  - Equivalent of the C(wallix-bastion_certificate_authority) Terraform data source.
  - Requires API version v3.12 or later.
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
  certificate_authority_name:
    description:
      - Name of the certificate authority to return. Without it, all certificate authorities are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one certificate authority
  wallix.bastion.certificate_authority_info:
    certificate_authority_name: corp-x509-ca
  register: result

- name: Save its certificate
  ansible.builtin.copy:
    content: "{{ result.certificate_authorities[0].ca_certificate }}"
    dest: /tmp/corp-ca.pem
    mode: "0644"

- name: List every certificate authority
  wallix.bastion.certificate_authority_info:
  register: all_cas
"""

RETURN = r"""
certificate_authorities:
  description:
    - Matching certificate authorities, as returned by the Bastion API. Empty when
      O(certificate_authority_name) matches none.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f76858e670b54005056b66c8b
      certificate_authority_name: corp-ssh-ca
      ca_type: SSH
      ca_certificate: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIC8AUFSJcx+fgI7j0JboX1MhgxEot4gYI1sJubI9HsG3 corp-ssh-ca\n"
      description: ""
      url: https://bastion.example.com/api/v3.12/certificate_authorities/1a0f76858e670b54005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, run_info


def main():
    module = BastionModule(
        argument_spec=dict(certificate_authority_name=dict(type="str")),
        supports_check_mode=True,
    )
    run_info(module, path="certificate_authorities", name_field="certificate_authority_name",
             result_key="certificate_authorities")


if __name__ == "__main__":
    main()
