#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: application
short_description: Manage applications on a WALLIX Bastion
version_added: 1.1.0
description:
  - Create, update or delete an application on a WALLIX Bastion.
  - An application of category V(standard) is a program started on a jump server (a cluster of RDP
    services); an application of category V(web_application) is a web site opened through the Bastion.
  - Equivalent of the C(wallix-bastion_application) Terraform resource.
  - Local domains of the application are managed with M(wallix.bastion.application_localdomain).
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
  application_name:
    description:
      - Name of the application. Identifies the application on the Bastion.
    type: str
    required: true
  connection_policy:
    description:
      - Name of the connection policy of the application, for example V(RDP) for a V(standard)
        application or V(WEBAPP) for a V(web_application).
      - Required when the application does not exist yet and O(state=present).
    type: str
  category:
    description:
      - Category of the application. It cannot be changed once the application exists.
      - When the application is created and this option is not set, V(standard) is used, as the
        Terraform provider does.
      - V(jumphost) is only accepted by Bastion API versions older than v3.12, which replaced it with V(web_application).
    type: str
    choices: [standard, jumphost, web_application]
  application_url:
    description:
      - URL of the application, for the V(web_application) and V(jumphost) categories.
      - Required when a V(web_application) is created.
    type: str
  login_form_url:
    description:
      - URL of the login form the Bastion fills in with the account credentials, for the
        V(web_application) category, when it differs from O(application_url).
      - Use V("") to remove it.
      - Not in the C(wallix-bastion_application) Terraform resource.
    type: str
    version_added: 1.2.0
  login_button_selector:
    description:
      - CSS selector of the submit button of the login form, for the V(web_application) category.
      - Use V("") to remove it.
      - Not in the C(wallix-bastion_application) Terraform resource.
    type: str
    version_added: 1.2.0
  allow_non_post_form:
    description:
      - Allow credentials injection in login forms that are not submitted with POST, for the
        V(web_application) category.
      - The Bastion uses V(false) when the application is created without it.
      - Not in the C(wallix-bastion_application) Terraform resource.
    type: bool
    version_added: 1.2.0
  browser:
    description:
      - Browser used to open the application, for the V(jumphost) category.
    type: str
  browser_version:
    description:
      - Version of O(browser), for the V(jumphost) category.
    type: str
  description:
    description:
      - Description of the application.
    type: str
  global_domains:
    description:
      - Names of the global domains whose accounts can be used on the application. Order does not matter.
      - When set, replaces all the global domains of the application. Use V([]) to remove them all.
    type: list
    elements: str
  parameters:
    description:
      - Command line parameters of the program, for the V(standard) category.
    type: str
  paths:
    description:
      - Program started on the jump server, for the V(standard) category.
      - Required when a V(standard) application is created. The Bastion accepts a single path.
      - When set, replaces the path of the application. It cannot be removed.
    type: list
    elements: dict
    suboptions:
      target:
        description:
          - Service of the jump server the program runs on, as V(Interactive@<device>:<service>).
        type: str
        required: true
      program:
        description:
          - Path of the program on the jump server.
        type: str
        required: true
      working_dir:
        description:
          - Working directory of the program. An unset value means no working directory.
        type: str
  target:
    description:
      - Name of the cluster of jump servers the application runs on, for the V(standard) category.
      - Required when a V(standard) application is created.
    type: str
  tags:
    description:
      - Tags of the application. Order does not matter.
      - When set, replaces all the tags of the application. Use V([]) to remove all tags.
    type: list
    elements: dict
    suboptions:
      key:
        description: Tag key.
        type: str
        required: true
      value:
        description: Tag value.
        type: str
        required: true
  state:
    description:
      - Whether the application should exist.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Options left unset keep their current value on the Bastion.
  - The Bastion refuses to delete an application that still has local domain accounts. Remove
    them first with M(wallix.bastion.application_localdomain_account).
"""

EXAMPLES = r"""
- name: Publish a program of a Windows jump server
  wallix.bastion.application:
    application_name: erp-client
    connection_policy: RDP
    category: standard
    target: jump-servers
    paths:
      - target: Interactive@win-jump-01:RDP
        program: C:\Program Files\ERP\erp.exe
        working_dir: C:\Program Files\ERP
    parameters: --server erp.example.com
    global_domains: [corp.local]

- name: Publish a web application
  wallix.bastion.application:
    application_name: intranet
    connection_policy: WEBAPP
    category: web_application
    application_url: https://intranet.example.com/login
    login_form_url: https://intranet.example.com/sso/login
    login_button_selector: "#login-submit"
    allow_non_post_form: false
    tags:
      - key: env
        value: prod

- name: Remove an application
  wallix.bastion.application:
    application_name: intranet
    state: absent
"""

RETURN = r"""
application:
  description:
    - The application as returned by the Bastion API after the change.
    - In check mode, the expected application. V(null) when O(state=absent).
  returned: always
  type: dict
  sample:
    id: 1a0f768b7518980c005056b66c8b
    application_name: erp-client
    category: standard
    connection_policy: RDP
    description: ""
    target: jump-servers
    cluster: jump-servers
    parameters: --server erp.example.com
    paths:
      - target: Interactive@win-jump-01:RDP
        program: C:\Program Files\ERP\erp.exe
        working_dir: C:\Program Files\ERP
    global_domains: [corp.local]
    local_domains: []
    tags: []
    last_connection: null
    url: https://bastion.example.com/api/v3.12/applications/1a0f768b7518980c005056b66c8b
changed_fields:
  description: Options that differed from the Bastion and were updated.
  returned: when the application already existed and O(state=present)
  type: list
  elements: str
  sample: [paths, tags]
"""

from ansible_collections.wallix.bastion.plugins.module_utils.resource import (
    BastionModule,
    BastionResource,
)

REQUIRED_BY_CATEGORY = {
    "standard": ("target", "paths"),
    "web_application": ("application_url",),
    "jumphost": ("application_url", "browser"),
}

# Login form options, only meaningful for web applications.
WEB_FORM_FIELDS = ("login_form_url", "login_button_selector", "allow_non_post_form")
# The Bastion stores "" as null for these: compare them as "".
WEB_FORM_STRINGS = ("login_form_url", "login_button_selector")


class ApplicationResource(BastionResource):
    def desired(self):
        desired = super(ApplicationResource, self).desired()
        if "paths" in desired:
            # The Bastion stores an unset working directory as "".
            desired["paths"] = [dict(p, working_dir=p.get("working_dir") or "") for p in desired["paths"]]
        return desired

    def normalize(self, obj):
        if obj and obj.get("category") == "web_application":
            obj = dict(obj, **{f: obj[f] or "" for f in WEB_FORM_STRINGS if f in obj})
        return obj

    def read(self):
        current = super(ApplicationResource, self).read()
        params = self.module.params
        if params["state"] == "present":
            category = (current or {}).get("category") or params.get("category") or "standard"
            web_form = [f for f in WEB_FORM_FIELDS if params.get(f) is not None]
            if web_form and category != "web_application":
                self.module.fail_json(msg="%s can only be set on a web_application, not on a %s application" % (
                    ", ".join(web_form), category))
        if current is None and params["state"] == "present":
            # Fail before writing anything, in check mode too, with the options the category needs.
            category = params.get("category") or "standard"
            missing = [f for f in REQUIRED_BY_CATEGORY[category] if not params.get(f)]
            if missing:
                self.module.fail_json(msg="application %s does not exist; %s required to create a %s application" % (
                    self.name, ", ".join(missing), category))
        return current

    def create(self, desired):
        if "category" not in desired:
            desired = dict(desired, category="standard")
        return super(ApplicationResource, self).create(desired)


def main():
    module = BastionModule(
        argument_spec=dict(
            application_name=dict(type="str", required=True),
            connection_policy=dict(type="str"),
            category=dict(type="str", choices=["standard", "jumphost", "web_application"]),
            application_url=dict(type="str"),
            login_form_url=dict(type="str"),
            login_button_selector=dict(type="str"),
            allow_non_post_form=dict(type="bool"),
            browser=dict(type="str"),
            browser_version=dict(type="str"),
            description=dict(type="str"),
            global_domains=dict(type="list", elements="str"),
            parameters=dict(type="str"),
            paths=dict(
                type="list",
                elements="dict",
                options=dict(
                    target=dict(type="str", required=True),
                    program=dict(type="str", required=True),
                    working_dir=dict(type="str"),
                ),
            ),
            target=dict(type="str"),
            tags=dict(
                type="list",
                elements="dict",
                options=dict(
                    key=dict(type="str", required=True, no_log=False),
                    value=dict(type="str", required=True),
                ),
            ),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        ),
        supports_check_mode=True,
    )
    if module.params["paths"] == []:
        module.fail_json(msg="paths cannot be empty: the Bastion ignores an empty list")
    resource = ApplicationResource(
        module,
        path="applications",
        name_field="application_name",
        fields=("application_name", "connection_policy", "category", "application_url", "login_form_url",
                "login_button_selector", "allow_non_post_form", "browser", "browser_version", "description",
                "global_domains", "parameters", "paths", "target", "tags"),
        set_fields=("global_domains", "paths", "tags"),
        result_key="application",
        required_on_create=("connection_policy",),
        create_only_fields=("category",),
        # Without force=true the Bastion appends to global_domains and tags instead of replacing them.
        update_query="force=true",
        # The PUT refuses the category, even unchanged.
        exclude_on_update=("category",),
    )
    resource.ensure(module.params["state"])


if __name__ == "__main__":
    main()
