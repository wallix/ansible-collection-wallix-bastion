#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: certificate_authority
short_description: Manage certificate authorities on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete a certificate authority on a WALLIX Bastion.
  - The Bastion uses certificate authorities to validate the certificates presented by devices or users,
    as an X.509 CA certificate or an SSH CA public key.
  - Equivalent of the C(wallix-bastion_certificate_authority) Terraform resource.
  - Requires API version v3.12 or later.
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
  certificate_authority_name:
    description:
      - Name of the certificate authority. Identifies it on the Bastion.
    type: str
    required: true
  ca_type:
    description:
      - Type of the certificate authority.
      - Required when the certificate authority does not exist yet and O(state=present).
    type: str
    choices: [SSH, X509]
  ca_certificate:
    description:
      - The CA certificate in PEM format for O(ca_type=X509), or the SSH CA public key in OpenSSH
        format for O(ca_type=SSH).
      - Leading and trailing white space and line endings are ignored when comparing with the Bastion.
      - Required when the certificate authority does not exist yet and O(state=present).
    type: str
  description:
    description:
      - Description of the certificate authority.
    type: str
  state:
    description:
      - Whether the certificate authority should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - O(ca_type) and O(ca_certificate) can be changed in place; change both together.
  - The certificate authority is looked up by O(certificate_authority_name), so it cannot be renamed with this module.
"""

EXAMPLES = r"""
- name: Declare the corporate X.509 certificate authority
  wallix.bastion.certificate_authority:
    certificate_authority_name: corp-x509-ca
    ca_type: X509
    ca_certificate: "{{ lookup('ansible.builtin.file', 'certs/corp-ca.pem') }}"
    description: Corporate X.509 certificate authority

- name: Declare an SSH certificate authority
  wallix.bastion.certificate_authority:
    certificate_authority_name: corp-ssh-ca
    ca_type: SSH
    ca_certificate: "{{ lookup('ansible.builtin.file', 'certs/corp-ssh-ca.pub') }}"

- name: Remove a certificate authority
  wallix.bastion.certificate_authority:
    certificate_authority_name: corp-ssh-ca
    state: absent
"""

RETURN = r"""
certificate_authority:
  description:
    - The certificate authority as returned by the Bastion API after the change.
    - In check mode, the expected certificate authority. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f76858e670b54005056b66c8b
    certificate_authority_name: corp-ssh-ca
    ca_type: SSH
    ca_certificate: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIC8AUFSJcx+fgI7j0JboX1MhgxEot4gYI1sJubI9HsG3 corp-ssh-ca\n"
    description: ""
    url: https://bastion.example.com/api/v3.12/certificate_authorities/1a0f76858e670b54005056b66c8b
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the certificate authority already existed and O(state=present)
  type: list
  elements: str
  sample: [ca_certificate]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)


def canonical_certificate(value):
    """The Bastion keeps the certificate as sent; ignore line endings and surrounding blanks."""
    if not isinstance(value, str):
        return value
    return "\n".join(line.rstrip() for line in value.strip().splitlines())


class CertificateAuthorityResource(BastionResource):

    def differences(self, current, desired):
        current = dict(current, ca_certificate=canonical_certificate(current.get("ca_certificate")))
        if "ca_certificate" in desired:
            desired = dict(desired, ca_certificate=canonical_certificate(desired["ca_certificate"]))
        return super(CertificateAuthorityResource, self).differences(current, desired)


def main():
    module = BastionModule(
        argument_spec=dict(
            certificate_authority_name=dict(type="str", required=True),
            ca_type=dict(type="str", choices=["SSH", "X509"]),
            ca_certificate=dict(type="str"),
            description=dict(type="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    resource = CertificateAuthorityResource(
        module,
        path="certificate_authorities",
        name_field="certificate_authority_name",
        fields=("certificate_authority_name", "ca_type", "ca_certificate", "description"),
        result_key="certificate_authority",
        required_on_create=("ca_type", "ca_certificate"),
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
