#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: timeframe_info
short_description: Get timeframes from a WALLIX Bastion
version_added: 1.0.0
description:
  - Return one timeframe by name, or every timeframe of the Bastion.
  - Equivalent of the C(wallix-bastion_timeframe) Terraform data source.
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
  timeframe_name:
    description:
      - Name of the timeframe to return. Without it, all timeframes are returned.
    type: str
"""

EXAMPLES = r"""
- name: Get one timeframe
  wallix.bastion.timeframe_info:
    timeframe_name: office-hours
  register: result

- name: Fail if the timeframe is missing
  ansible.builtin.assert:
    that: result.timeframes | length == 1

- name: List every timeframe
  wallix.bastion.timeframe_info:
  register: all_timeframes
"""

RETURN = r"""
timeframes:
  description:
    - Matching timeframes, as returned by the Bastion API. Empty when O(timeframe_name) matches no timeframe.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 19f463ca6a351f23005056b66c8b
      timeframe_name: allthetime
      description: ""
      is_overtimable: false
      periods:
        - start_date: "2011-01-01"
          end_date: "2099-12-30"
          start_time: "00:00"
          end_time: "00:00"
          week_days: [monday, tuesday, wednesday, thursday, friday, saturday, sunday]
      url: https://bastion.example.com/api/v3.12/timeframes/19f463ca6a351f23005056b66c8b
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import BastionModule, run_info


def main():
    module = BastionModule(
        argument_spec=dict(timeframe_name=dict(type="str")),
        supports_check_mode=True,
    )
    run_info(module, path="timeframes", name_field="timeframe_name", result_key="timeframes")


if __name__ == "__main__":
    main()
