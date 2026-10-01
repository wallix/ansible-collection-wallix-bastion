#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: cluster
short_description: Manage clusters on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete a cluster on a WALLIX Bastion.
  - A cluster groups several targets so that sessions opened on the cluster are spread over them.
  - Equivalent of the C(wallix-bastion_cluster) Terraform resource.
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
  cluster_name:
    description:
      - Name of the cluster. Identifies the cluster on the Bastion.
    type: str
    required: true
  description:
    description:
      - Description of the cluster.
    type: str
  accounts:
    description:
      - Account targets of the cluster, as V(<account>@<domain>@<device>:<service>), for example
        V(administrator@local@srv-win-01:RDP). Order does not matter.
      - When set, replaces all the account targets of the cluster. Use V([]) to remove them all.
    type: list
    elements: str
  account_mappings:
    description:
      - Account mapping targets of the cluster, as V(<device>:<service>). Order does not matter.
      - When set, replaces all the account mapping targets of the cluster. Use V([]) to remove them all.
    type: list
    elements: str
  interactive_logins:
    description:
      - Interactive login targets of the cluster, as V(<device>:<service>). Order does not matter.
      - When set, replaces all the interactive login targets of the cluster. Use V([]) to remove them all.
    type: list
    elements: str
  state:
    description:
      - Whether the cluster should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - A cluster needs at least one target in O(accounts), O(account_mappings) or O(interactive_logins).
    The module fails, in check mode too, when the cluster would have none.
  - The Bastion 12.4 only accepts targets on RDP services in a cluster.
  - The devices, services and accounts referenced must exist; the Bastion rejects the change otherwise.
  - The application targets of a cluster (the C(applications) field of RV(cluster)) are returned but not managed, and
    are kept when the cluster is updated.
  - The cluster is looked up by O(cluster_name), so it cannot be renamed with this module.
"""

EXAMPLES = r"""
- name: Spread RDP sessions over two Windows servers
  wallix.bastion.cluster:
    cluster_name: windows-farm
    description: Windows RDS farm
    interactive_logins:
      - srv-win-01:RDP
      - srv-win-02:RDP
    accounts:
      - administrator@local@srv-win-01:RDP
      - administrator@local@srv-win-02:RDP

- name: Replace the interactive logins, keep the accounts
  wallix.bastion.cluster:
    cluster_name: windows-farm
    interactive_logins:
      - srv-win-03:RDP

- name: Remove a cluster
  wallix.bastion.cluster:
    cluster_name: windows-farm
    state: absent
"""

RETURN = r"""
cluster:
  description:
    - The cluster as returned by the Bastion API after the change.
    - In check mode, the expected cluster. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f769b8c92a15c005056b66c8b
    cluster_name: windows-farm
    description: Windows RDS farm
    accounts:
      - administrator@local@srv-win-01:RDP
      - administrator@local@srv-win-02:RDP
    account_mappings: []
    interactive_logins:
      - srv-win-01:RDP
      - srv-win-02:RDP
    applications: []
    url: https://bastion.example.com/api/v3.12/clusters/1a0f769b8c92a15c005056b66c8b
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the cluster already existed and O(state=present)
  type: list
  elements: str
  sample: [interactive_logins]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.client import BastionError
from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)

TARGETS = ("accounts", "account_mappings", "interactive_logins")
_UNREAD = object()


class ClusterResource(BastionResource):
    """Clusters must keep at least one target: check it before any write, in check mode too."""

    _cached = _UNREAD

    def read(self):
        if self._cached is not _UNREAD:
            current, self._cached = self._cached, _UNREAD
            return current
        return super(ClusterResource, self).read()

    def ensure(self, state):
        if state == "present":
            try:
                current = self.read()
            except BastionError as e:
                self.module.fail_json(msg=str(e), status=e.status, body=e.body)
            targets = dict((f, (current or {}).get(f) or []) for f in TARGETS)
            targets.update((f, v) for f, v in self.desired().items() if f in TARGETS)
            if not any(targets.values()):
                self.module.fail_json(msg="cluster %s needs at least one target in %s" % (
                    self.name, ", ".join(TARGETS)))
            # Hand the object over to the generic ensure() instead of reading it again.
            self._cached = current
        super(ClusterResource, self).ensure(state)


def main():
    module = BastionModule(
        argument_spec=dict(
            cluster_name=dict(type="str", required=True),
            description=dict(type="str"),
            accounts=dict(type="list", elements="str"),
            account_mappings=dict(type="list", elements="str"),
            interactive_logins=dict(type="list", elements="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    resource = ClusterResource(
        module,
        path="clusters",
        name_field="cluster_name",
        fields=("cluster_name", "description") + TARGETS,
        set_fields=TARGETS,
        result_key="cluster",
        # Without force=true the API appends to the target lists instead of replacing them.
        update_query="force=true",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
