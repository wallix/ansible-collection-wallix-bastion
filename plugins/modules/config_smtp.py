#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: config_smtp
short_description: Manage the SMTP configuration of a WALLIX Bastion
version_added: 1.1.0
description:
  - Update the global SMTP server settings the Bastion uses to send its emails (notifications, alerts).
  - Equivalent of the C(wallix-bastion_config_smtp) Terraform resource.
  - The SMTP configuration is a singleton that always exists on the Bastion and has no delete endpoint,
    so the module only offers O(state=present). Removing the Terraform resource does not change the
    Bastion either.
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
  protocol:
    description:
      - Protocol used to reach the SMTP server, for example V(smtp), V(smtps) or V(starttls).
    type: str
  authentication_method:
    description:
      - Authentication method, for example V(off), V(on), V(plain), V(login), V(SCRAM-SHA-1), V(CRAM-MD5),
        V(DIGEST-MD5) or V(ntlm).
    type: str
  server:
    description:
      - Host name or IP address of the SMTP server.
    type: str
  port:
    description:
      - TCP port of the SMTP server.
    type: int
  postmaster_email:
    description:
      - Email address of the postmaster.
    type: str
  sender_name:
    description:
      - Display name of the sender of the Bastion emails.
    type: str
  sender_email:
    description:
      - Email address the Bastion emails are sent from.
    type: str
  certificate_hash:
    description:
      - Hash of the SMTP server certificate.
    type: str
  user:
    description:
      - User to authenticate to the SMTP server with.
    type: str
  password:
    description:
      - Password to authenticate to the SMTP server with.
      - The Bastion does not return it, so it cannot be compared. See O(update_password).
    type: str
  update_password:
    description:
      - V(on_create) sends O(password) only when the Bastion reports that no SMTP password is set yet
        (the configuration itself always exists, so this is the equivalent of "on creation").
      - V(always) sends O(password) on every run, which then always reports a change.
    type: str
    choices: [always, on_create]
    default: on_create
  state:
    description:
      - Only V(present) is supported. The SMTP configuration cannot be deleted.
    type: str
    choices: [present]
    default: present
notes:
  - Options left unset keep their current value on the Bastion. The module sends the current values
    of the unset options with the changed ones, because the API refuses an update that lacks one of
    O(protocol), O(authentication_method), O(server), O(postmaster_email), O(sender_name) and O(sender_email).
"""

EXAMPLES = r"""
- name: Send the Bastion emails through the corporate relay
  wallix.bastion.config_smtp:
    protocol: starttls
    authentication_method: plain
    server: smtp.example.com
    port: 587
    postmaster_email: postmaster@example.com
    sender_name: WALLIX Bastion
    sender_email: bastion@example.com
    user: smtp-user
    password: "{{ vault_smtp_password }}"

- name: Change only the sender name
  wallix.bastion.config_smtp:
    sender_name: Bastion PROD
"""

RETURN = r"""
config_smtp:
  description:
    - The SMTP configuration as returned by the Bastion API after the change, without the password.
    - In check mode, the expected configuration.
  returned: always
  type: dict
  sample:
    protocol: starttls
    authentication_method: plain
    server: smtp.example.com
    port: 587
    postmaster_email: postmaster@example.com
    sender_name: WALLIX Bastion
    sender_email: bastion@example.com
    certificate_hash: ""
    user: smtp-user
changed_fields:
  description: Options that differed from the Bastion and were updated. Contains V(password) when it was sent.
  returned: always
  type: list
  elements: str
  sample: [sender_name]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)

FIELDS = ("protocol", "authentication_method", "server", "port", "postmaster_email",
          "sender_name", "sender_email", "certificate_hash", "user", "password")
MASK = "********"


class SingletonResource(BastionResource):
    """One configuration object at a fixed path: GET <path> to read it, PUT <path> to change it."""

    def read(self):
        return self.normalize(self.client.get(self.path) or {})

    def update(self, current, desired):
        values = {f: current[f] for f in self.fields
                  if current.get(f) is not None and f not in self.secret_fields}
        values.update(desired)
        self.client.call("PUT", self.path, self.body(values))
        return self.read()


class SMTPConfig(SingletonResource):
    def read(self):
        obj = self.client.get(self.path) or {}
        password = obj.pop("password", None)
        wanted = self.module.params.get("password")
        if wanted is not None and self.module.params["update_password"] == "on_create":
            # Send the password when none is set, or when the API returns it in clear and it differs.
            # A masked password cannot be compared and is left alone.
            self.update_secrets = not password or (password != MASK and password != wanted)
        return self.normalize(obj)

    def body(self, values):
        # Like the provider (omitempty): empty optional values are not sent.
        return {k: v for k, v in values.items()
                if not (k in ("certificate_hash", "user", "password") and v == "")}


def main():
    module = BastionModule(
        argument_spec=dict(
            protocol=dict(type="str"),
            authentication_method=dict(type="str"),
            server=dict(type="str"),
            port=dict(type="int"),
            postmaster_email=dict(type="str"),
            sender_name=dict(type="str"),
            sender_email=dict(type="str"),
            certificate_hash=dict(type="str"),
            user=dict(type="str"),
            password=dict(type="str", no_log=True),
            update_password=dict(type="str", choices=["always", "on_create"], default="on_create", no_log=False),
            state=dict(type="str", choices=["present"], default="present"),
        ),
        supports_check_mode=True,
    )
    if module.params["port"] is not None and not 0 < module.params["port"] <= 65535:
        module.fail_json(msg="port must be between 1 and 65535")
    resource = SMTPConfig(
        module,
        path="config/smtp",
        name_field=None,
        fields=FIELDS,
        result_key="config_smtp",
        secret_fields=("password",),
        update_secrets=module.params["update_password"] == "always",
    )
    resource.ensure("present")


if __name__ == "__main__":
    main()
