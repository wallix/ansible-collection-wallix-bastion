#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: encryption
short_description: Set up or change the encryption passphrase of a WALLIX Bastion
version_added: 1.1.0
description:
  - Set up the encryption of the secrets of a Bastion, protect it with a passphrase, or change that passphrase.
  - Equivalent of the C(wallix-bastion_encryption) Terraform resource.
  - The encryption is a singleton that cannot be deleted, so the module only offers O(state=present).
  - The Bastion never returns the passphrase, so the module decides from the encryption state it reports
    (RV(encryption.seal_state) and RV(encryption.encryption_mode)) and from the options given.
    The encryption is set up when the Bastion needs it. A passphrase is added when the Bastion has
    none (V(unprotected)) and O(new_passphrase) is not empty. The passphrase is changed when
    O(current_passphrase) is set and differs from O(new_passphrase). Otherwise nothing is sent.
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
  new_passphrase:
    description:
      - Passphrase to protect the encryption with. V("") sets up the encryption without a passphrase
        (not recommended).
    type: str
    required: true
  current_passphrase:
    description:
      - Current passphrase, to change it to O(new_passphrase).
      - Remove it from the task once the passphrase is changed. The Bastion refuses a later run with a
        current passphrase that is no longer valid.
    type: str
  state:
    description:
      - Only V(present) is supported. The encryption cannot be removed.
    type: str
    choices: [present]
    default: present
notes:
  - A sealed Bastion (after a reboot, with a passphrase) must be unlocked first; the module fails.
  - Losing the passphrase of a sealed Bastion makes its secrets unrecoverable. Keep it in a vault.
"""

EXAMPLES = r"""
- name: Set up the encryption of a new Bastion with a passphrase
  wallix.bastion.encryption:
    new_passphrase: "{{ vault_bastion_passphrase }}"

- name: Rotate the passphrase
  wallix.bastion.encryption:
    current_passphrase: "{{ vault_bastion_old_passphrase }}"
    new_passphrase: "{{ vault_bastion_passphrase }}"
"""

RETURN = r"""
encryption:
  description:
    - The encryption state as returned by the Bastion API after the change.
    - In check mode, the expected state.
  returned: always
  type: dict
  contains:
    seal_state:
      description: V(need_setup), V(sealed) or V(unsealed) (API v3.12).
      type: str
      returned: with API v3.12
    encryption_mode:
      description: V(need_setup), V(unprotected), V(passphrase), or V([hidden]) (API v3.12).
      type: str
      returned: with API v3.12
    encryption:
      description: Encryption state (API v3.8), V(ready) once set up.
      type: str
      returned: with API v3.8
    enabled:
      description: Whether the encryption is set up and unlocked, like the C(enabled) attribute of the Terraform data source.
      type: bool
      returned: always
  sample:
    seal_state: unsealed
    encryption_mode: passphrase
    enabled: true
action:
  description: What was (or would be) done.
  returned: always
  type: str
  choices: [none, setup, change_passphrase]
  sample: change_passphrase
"""

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule

PATH = "encryption"


def status(obj):
    obj = dict(obj or {})
    if "seal_state" in obj:
        obj["enabled"] = obj["seal_state"] == "unsealed"
    else:
        obj["enabled"] = obj.get("encryption") == "ready"
    return obj


def main():
    module = BastionModule(
        argument_spec=dict(
            new_passphrase=dict(type="str", required=True, no_log=True),
            current_passphrase=dict(type="str", no_log=True),
            state=dict(type="str", choices=["present"], default="present"),
        ),
        supports_check_mode=True,
    )
    new = module.params["new_passphrase"]
    old = module.params["current_passphrase"]
    client = module.client
    try:
        current = status(client.get(PATH))
        states = (current.get("seal_state"), current.get("encryption"), current.get("encryption_mode"))
        if "need_setup" in states:
            action, body = "setup", dict(new_passphrase=new)
        elif "sealed" in states:
            module.fail_json(msg="The Bastion encryption is sealed; unlock it with its passphrase first",
                             encryption=current)
        elif old is not None and old != new:
            action, body = "change_passphrase", dict(passphrase=old, new_passphrase=new)
        elif current.get("encryption_mode") == "unprotected" and new:
            # Like the provider's create: the passphrase of an unprotected Bastion is set without the current one.
            action, body = "change_passphrase", dict(new_passphrase=new)
        else:
            action, body = "none", None

        after = current
        if body is not None:
            if module.check_mode:
                after = dict(current, enabled=True)
                if "seal_state" in after:
                    after.update(seal_state="unsealed", encryption_mode="passphrase" if new else "unprotected")
                else:
                    after["encryption"] = "ready"
            else:
                client.call("PUT", PATH, body)
                after = status(client.get(PATH))
        module.exit_json(changed=body is not None, action=action, encryption=after,
                         diff=dict(before=current, after=after))
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)


if __name__ == "__main__":
    main()
