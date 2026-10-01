# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class ModuleDocFragment(object):

    DOCUMENTATION = r"""
options:
  bastion_host:
    description:
      - Hostname or IP address of the WALLIX Bastion.
      - If not set, the value of the E(WALLIX_BASTION_HOST) environment variable is used.
    type: str
  bastion_port:
    description:
      - HTTPS port of the WALLIX Bastion API.
      - If not set, the value of the E(WALLIX_BASTION_PORT) environment variable is used, then V(443).
    type: int
  bastion_user:
    description:
      - User to authenticate with. With O(bastion_token), the user the API key belongs to.
      - If not set, the value of the E(WALLIX_BASTION_USER) environment variable is used.
    type: str
  bastion_password:
    description:
      - Password of O(bastion_user).
      - If not set, the value of the E(WALLIX_BASTION_PASSWORD) environment variable is used.
      - One of O(bastion_password) or O(bastion_token) is required.
    type: str
  bastion_token:
    description:
      - API key of O(bastion_user). Takes precedence over O(bastion_password).
      - If not set, the value of the E(WALLIX_BASTION_TOKEN) environment variable is used.
    type: str
  api_version:
    description:
      - Version of the Bastion REST API to use, V(v3.8) or V(v3.12).
      - If not set, the value of the E(WALLIX_BASTION_API_VERSION) environment variable is used, then V(v3.12).
    type: str
  validate_certs:
    description:
      - Whether to validate the Bastion's TLS certificate.
      - Only disable this for test instances with self-signed certificates.
      - If not set, E(WALLIX_BASTION_VALIDATE_CERTS) is used, then the inverse of
        E(WALLIX_INSECURE_SKIP_VERIFY), then V(true).
    type: bool
  csrf_enabled:
    description:
      - Send the CSRF token the Bastion issues at login (Bastion 12.0.3 and later).
      - If not set, the value of the E(WALLIX_CSRF_ENABLED) environment variable is used, then V(true).
    type: bool
  bastion_timeout:
    description:
      - Timeout in seconds of each HTTP request to the Bastion API.
    type: int
    default: 30
notes:
  - The environment variables are the ones of the C(wallix/wallix-bastion) Terraform provider,
    so one shell configuration serves both tools.
  - Set the connection options once per play with C(module_defaults) and the
    C(group/wallix.bastion.bastion) action group.
  - These modules call the Bastion API from the host they run on; use them with C(delegate_to)
    or on a play targeting C(localhost).
"""
