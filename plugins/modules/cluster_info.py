#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: cluster_info
short_description: Get clusters from a WALLIX Bastion
version_added: 1.1.0
description:
  - Return one cluster by name, or every cluster of the Bastion.
  - Equivalent of the C(wallix-bastion_cluster) Terraform data source.
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
  cluster_name:
    description:
      - Name of the cluster to return. Without it, all clusters are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one cluster
  wallix.bastion.cluster_info:
    cluster_name: windows-farm
  register: result

- name: Show its interactive login targets
  ansible.builtin.debug:
    msg: "{{ result.clusters[0].interactive_logins }}"

- name: List every cluster
  wallix.bastion.cluster_info:
  register: all_clusters
"""

RETURN = r"""
clusters:
  description:
    - Matching clusters, as returned by the Bastion API. Empty when O(cluster_name) matches no cluster.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 1a0f769b8c92a15c005056b66c8b
      cluster_name: windows-farm
      description: Windows RDS farm
      accounts: [administrator@local@srv-win-01:RDP]
      account_mappings: []
      interactive_logins: [srv-win-01:RDP, srv-win-02:RDP]
      applications: []
      url: https://bastion.example.com/api/v3.12/clusters/1a0f769b8c92a15c005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, run_info


def main():
    module = BastionModule(
        argument_spec=dict(cluster_name=dict(type="str")),
        supports_check_mode=True,
    )
    run_info(module, path="clusters", name_field="cluster_name", result_key="clusters")


if __name__ == "__main__":
    main()
