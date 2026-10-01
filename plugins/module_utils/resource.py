# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""Generic present/absent logic for Bastion API objects addressed by a unique name.

The Ansible counterpart of the search/add/read/update/delete functions every
resource_*.go file of terraform-provider-wallix-bastion implements, with what
Terraform gets from its plan for free: only options the user set are compared,
check mode and diff mode are honoured, and `changed` is only true when the
Bastion was (or would be) modified.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import copy
import json

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.wallix.bastion.plugins.module_utils.client import (
    CONNECTION_ARGUMENT_SPEC,
    BastionClient,
    BastionError,
    resolve_connection,
    validate_connection,
)


def connection_argument_spec():
    return copy.deepcopy(CONNECTION_ARGUMENT_SPEC)


class BastionModule(AnsibleModule):
    """AnsibleModule with the shared connection options and a lazily built client."""

    def __init__(self, argument_spec, **kwargs):
        spec = connection_argument_spec()
        spec.update(argument_spec)
        super(BastionModule, self).__init__(argument_spec=spec, **kwargs)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            conn = resolve_connection({k: self.params.get(k) for k in CONNECTION_ARGUMENT_SPEC})
            error = validate_connection(conn)
            if error:
                self.fail_json(msg=error)
            self._client = BastionClient(**conn)
        return self._client


def _normalize(value, as_set):
    """Canonical form for comparison: sets of dicts/strings compare order-insensitively."""
    if as_set and isinstance(value, list):
        return sorted(json.dumps(v, sort_keys=True) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return value


class BastionResource:
    """Manage one API collection whose objects are identified by a unique name field.

    path                collection path relative to /api/<version>/, e.g. "devices", or
                        "devices/<id>/services" for child objects (see find_parent)
    name_field          API field holding the unique name, e.g. "device_name"
    fields              writable API fields this module exposes; module options use the same names
    set_fields          list fields whose order is meaningless (e.g. tags)
    result_key          key the object is returned under, e.g. "device"
    required_on_create  options that must be set when the object does not exist yet
    create_only_fields  options the API cannot change after creation (ForceNew in the provider);
                        a different value fails instead of silently recreating the object
    secret_fields       write-only options (passwords, keys) the API never returns: sent on
                        creation, and on update only when update_secrets is true
    update_secrets      send secret_fields on every run; they then always count as changed
    update_query        query string added to PUT, e.g. "force=true" for objects with list fields:
                        without it the Bastion appends to lists instead of replacing them
    merge_on_update     PUT the current fields overlaid with the requested ones (default), or only
                        the requested ones, for objects whose PUT rejects fields read back by GET
    exclude_on_update   fields the API refuses in a PUT body (often the name or the protocol)
    search              how read() finds the object: "query" (GET <path>?q=<name_field>=<name>),
                        or "list" (GET <path> and match) for collections without q= support

    Subclass and override desired(), normalize() or body() for objects whose API shape
    differs from their module options.
    """

    def __init__(self, module, path, name_field, fields, set_fields=(), result_key=None,
                 required_on_create=(), create_only_fields=(), secret_fields=(), update_secrets=False,
                 update_query=None, merge_on_update=True, exclude_on_update=(), search="query"):
        self.module = module
        self.path = path.strip("/")
        self.name_field = name_field
        self.fields = tuple(fields)
        self.set_fields = frozenset(set_fields)
        self.result_key = result_key or self.path.rstrip("s")
        self.required_on_create = tuple(required_on_create)
        self.create_only_fields = frozenset(create_only_fields)
        self.secret_fields = frozenset(secret_fields)
        self.update_secrets = update_secrets
        self.update_query = update_query
        self.merge_on_update = merge_on_update
        self.exclude_on_update = frozenset(exclude_on_update)
        self.search = search

    @property
    def client(self):
        return self.module.client

    @property
    def name(self):
        return self.module.params[self.name_field]

    def desired(self):
        """Fields the user set; None means "leave as is", like an omitted Terraform attribute."""
        return {f: self.module.params[f] for f in self.fields if self.module.params.get(f) is not None}

    def normalize(self, obj):
        """Hook: convert an API object to the shape of desired() before comparing."""
        return obj

    def body(self, values):
        """Hook: convert option values to the JSON body the API expects."""
        return values

    def object_path(self, object_id):
        return "%s/%s" % (self.path, object_id)

    def read(self):
        if self.search == "list":
            matches = [o for o in self.client.get(self.path) or [] if o.get(self.name_field) == self.name]
            found = matches[0] if matches else None
        else:
            found = self.client.find(self.path, self.name_field, self.name)
        if found is None:
            return None
        # The collection listing may be abridged; re-read the object like the provider does.
        return self.normalize(self.client.get(self.object_path(found["id"])) or found)

    def differences(self, current, desired):
        return sorted(
            f for f, value in desired.items()
            if f not in self.secret_fields
            and _normalize(current.get(f), f in self.set_fields) != _normalize(value, f in self.set_fields)
        )

    def _view(self, obj):
        return {f: obj.get(f) for f in self.fields
                if obj is not None and f in obj and f not in self.secret_fields}

    def create(self, desired):
        resp = self.client.call("POST", self.path, self.body(desired))
        object_id = resp.header("X-Object-Id")
        if object_id:
            return self.normalize(self.client.get(self.object_path(object_id)))
        # Bastion versions that don't return X-Object-Id: find it by name, as the provider does.
        created = self.read()
        if created is None:
            raise BastionError("%s %s not found after creation" % (self.result_key, self.name))
        return created

    def update(self, current, desired):
        # By default PUT the current writable fields overlaid with the requested ones, so options
        # the user left unset are preserved whatever the API's PUT semantics. Nulls are what GET
        # returns for unset fields; the API refuses them back.
        values = {}
        if self.merge_on_update:
            values = {f: current[f] for f in self.fields
                      if current.get(f) is not None and f not in self.secret_fields}
        values.update(desired)
        for field in self.exclude_on_update:
            values.pop(field, None)
        path = self.object_path(current["id"])
        self.client.call("PUT", path + ("?" + self.update_query if self.update_query else ""), self.body(values))
        return self.normalize(self.client.get(path))

    def delete(self, current):
        self.client.call("DELETE", self.object_path(current["id"]), expected=(200, 204, 404))

    def ensure(self, state):
        """Converge to `state` and exit the module."""
        module = self.module
        try:
            current = self.read()
            result = dict(changed=False)

            if state == "absent":
                if current is not None:
                    result["changed"] = True
                    if not module.check_mode:
                        self.delete(current)
                result["diff"] = dict(before=self._view(current), after={})
                result[self.result_key] = None
                module.exit_json(**result)

            desired = self.desired()
            if current is None:
                missing = [f for f in self.required_on_create if f not in desired]
                if missing:
                    module.fail_json(msg="%s %s does not exist; %s required to create it" % (
                        self.result_key, self.name, ", ".join(missing)))
                result["changed"] = True
                after = self.create(desired) if not module.check_mode else desired
                result["diff"] = dict(before={}, after=self._view(after))
            else:
                changes = self.differences(current, desired)
                frozen = sorted(self.create_only_fields.intersection(changes))
                if frozen:
                    module.fail_json(msg="%s %s: %s cannot be changed after creation; delete and recreate it" % (
                        self.result_key, self.name, ", ".join(frozen)))
                if self.update_secrets:
                    changes = sorted(set(changes) | (self.secret_fields & set(desired)))
                if not self.update_secrets:
                    desired = {f: v for f, v in desired.items() if f not in self.secret_fields}
                after = current
                if changes:
                    result["changed"] = True
                    if module.check_mode:
                        after = dict(current, **desired)
                    else:
                        after = self.update(current, desired)
                result["diff"] = dict(before=self._view(current), after=self._view(after))
                result["changed_fields"] = changes

            result[self.result_key] = {k: v for k, v in after.items() if k not in self.secret_fields}
            module.exit_json(**result)
        except BastionError as e:
            module.fail_json(msg=str(e), status=e.status, body=e.body)


def find_parent(module, path, name_field, name, label=None):
    """Id of the parent object a child resource lives under, e.g. the device of a service.

    Fails the module if the parent does not exist, unless the play is removing the child:
    then None is returned and the caller exits unchanged.
    """
    try:
        found = module.client.find(path, name_field, name)
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)
    if found is not None:
        return found["id"]
    if module.params.get("state") == "absent":
        return None
    module.fail_json(msg="%s %s does not exist" % (label or name_field, name))


def run_info(module, path, name_field, result_key, normalize=None):
    """Shared body of the *_info modules: one object by name, or the whole collection."""
    normalize = normalize or (lambda obj: obj)
    try:
        name = module.params.get(name_field)
        if name:
            found = module.client.find(path, name_field, name)
            objects = [module.client.get("%s/%s" % (path, found["id"])) or found] if found else []
        else:
            objects = module.client.get(path) or []
        module.exit_json(changed=False, **{result_key: [normalize(o) for o in objects]})
    except BastionError as e:
        module.fail_json(msg=str(e), status=e.status, body=e.body)
