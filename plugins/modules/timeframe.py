#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: timeframe
short_description: Manage timeframes on a WALLIX Bastion
version_added: 1.0.0
description:
  - Create, update or delete a timeframe on a WALLIX Bastion.
  - A timeframe is a set of periods during which users, groups or authorizations are allowed.
  - Equivalent of the C(wallix-bastion_timeframe) Terraform resource.
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
  timeframe_name:
    description:
      - Name of the timeframe. Identifies the timeframe on the Bastion.
    type: str
    required: true
  description:
    description:
      - Description of the timeframe.
    type: str
  is_overtimable:
    description:
      - Whether sessions may go on after the end of the timeframe.
    type: bool
  periods:
    description:
      - Periods of the timeframe. Order does not matter, neither does the order of O(periods[].week_days).
      - When set, replaces all the periods of the timeframe. Use V([]) to remove all periods.
      - Two identical periods are refused by the Bastion.
    type: list
    elements: dict
    suboptions:
      start_date:
        description: First day of the period, as C(YYYY-MM-DD).
        type: str
        required: true
      end_date:
        description: Last day of the period, as C(YYYY-MM-DD).
        type: str
        required: true
      start_time:
        description: Start of the daily time slot, as C(hh:mm).
        type: str
        required: true
      end_time:
        description:
          - End of the daily time slot, as C(hh:mm). Must be after O(periods[].start_time),
            or V(00:00) for the end of the day.
        type: str
        required: true
      week_days:
        description: Days of the week the time slot applies to. At least one is required.
        type: list
        elements: str
        required: true
        choices: [monday, tuesday, wednesday, thursday, friday, saturday, sunday]
  state:
    description:
      - Whether the timeframe should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - Do not manage the built-in V(allthetime) timeframe with this module.
"""

EXAMPLES = r"""
- name: Allow access during office hours in 2026
  wallix.bastion.timeframe:
    timeframe_name: office-hours
    description: Monday to Friday, 8:00 to 18:00
    periods:
      - start_date: "2026-01-01"
        end_date: "2026-12-31"
        start_time: "08:00"
        end_time: "18:00"
        week_days: [monday, tuesday, wednesday, thursday, friday]

- name: Remove a timeframe
  wallix.bastion.timeframe:
    timeframe_name: office-hours
    state: absent
"""

RETURN = r"""
timeframe:
  description:
    - The timeframe as returned by the Bastion API after the change.
    - In check mode, the expected timeframe. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f6daa9f92d6b9005056b66c8b
    timeframe_name: office-hours
    description: Monday to Friday, 8:00 to 18:00
    is_overtimable: false
    periods:
      - start_date: "2026-01-01"
        end_date: "2026-12-31"
        start_time: "08:00"
        end_time: "18:00"
        week_days: [monday, tuesday, wednesday, thursday, friday]
    url: https://bastion.example.com/api/v3.12/timeframes/1a0f6daa9f92d6b9005056b66c8b
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the timeframe already existed and O(state=present)
  type: list
  elements: str
  sample: [periods]
"""

import re

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)

WEEK_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DATE_RE = re.compile(r"^[12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
PERIOD_FIELDS = ("start_date", "end_date", "start_time", "end_time", "week_days")


def canonical_period(period):
    """A period with its week days in calendar order, as the Bastion stores them."""
    period = {k: period.get(k) for k in PERIOD_FIELDS}
    period["week_days"] = sorted(set(period["week_days"] or []), key=WEEK_DAYS.index)
    return period


class TimeframeResource(BastionResource):
    """Timeframes, with week days compared order-insensitively and PUT forced.

    Without ?force=true the Bastion answers 204 to a PUT with "periods": [] but keeps
    the periods; the provider always forces its updates too.
    """

    def desired(self):
        desired = super(TimeframeResource, self).desired()
        if "periods" in desired:
            desired["periods"] = [canonical_period(p) for p in desired["periods"]]
        return desired

    def normalize(self, obj):
        if obj and isinstance(obj.get("periods"), list):
            obj = dict(obj, periods=[canonical_period(p) for p in obj["periods"]])
        return obj


def validate_periods(module):
    for i, period in enumerate(module.params.get("periods") or []):
        for field, pattern, fmt in (("start_date", DATE_RE, "YYYY-MM-DD"), ("end_date", DATE_RE, "YYYY-MM-DD"),
                                    ("start_time", TIME_RE, "hh:mm"), ("end_time", TIME_RE, "hh:mm")):
            if not pattern.match(period[field]):
                module.fail_json(msg="periods[%d].%s must use the format %s, got %s" % (i, field, fmt, period[field]))
        if not period["week_days"]:
            module.fail_json(msg="periods[%d].week_days must contain at least one day" % i)


def main():
    module = BastionModule(
        argument_spec=dict(
            timeframe_name=dict(type="str", required=True),
            description=dict(type="str"),
            is_overtimable=dict(type="bool"),
            periods=dict(
                type="list",
                elements="dict",
                options=dict(
                    start_date=dict(type="str", required=True),
                    end_date=dict(type="str", required=True),
                    start_time=dict(type="str", required=True),
                    end_time=dict(type="str", required=True),
                    week_days=dict(type="list", elements="str", required=True, choices=WEEK_DAYS),
                ),
            ),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    if module.params["state"] == "present":
        validate_periods(module)
    resource = TimeframeResource(
        module,
        path="timeframes",
        name_field="timeframe_name",
        fields=("timeframe_name", "description", "is_overtimable", "periods"),
        set_fields=("periods",),
        result_key="timeframe",
        update_query="force=true",
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
