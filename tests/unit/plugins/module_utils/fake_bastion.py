# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""In-memory stand-in for the Bastion REST API, plugged in at BastionClient._open."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import uuid

from urllib.parse import parse_qs, unquote, urlparse

from ansible_collections.wallix.bastion.plugins.module_utils.client import Response


class FakeBastion:
    def __init__(self, api_version="v3.12", return_object_id=True, csrf_token=None):
        self.api_version = api_version
        self.return_object_id = return_object_id
        self.csrf_token = csrf_token
        self.collections = {}
        self.calls = []
        self.logins = 0
        self.expire_session_once = False

    def add(self, collection, obj):
        obj = dict(obj, id=obj.get("id") or uuid.uuid4().hex)
        self.collections.setdefault(collection, {})[obj["id"]] = obj
        return obj

    def objects(self, collection):
        return list(self.collections.get(collection, {}).values())

    def writes(self):
        return [c for c in self.calls if c[0] in ("POST", "PUT", "DELETE") and c[1] != "/api"]

    def bind(self, client):
        def _open(method, url, data=None, headers=None, **kwargs):
            return self.handle(client, method, url, data, headers or {}, kwargs)
        client._open = _open
        return client

    def handle(self, client, method, url, data, headers, auth):
        parsed = urlparse(url)
        path = parsed.path
        body = json.loads(data) if data else None
        self.calls.append((method, path, body))

        if path == "/api" and method == "POST":
            self.logins += 1
            ok = headers.get("X-Auth-Key") == "token" or auth.get("url_password") == "secret"
            if not ok:
                return Response(401, '{"error": "Authentication failure"}', {})
            client._cookies.set_cookie(_cookie("wab_session_id", "session-%d" % self.logins))
            return Response(204, "", {"X-CSRF-Token": self.csrf_token} if self.csrf_token else {})

        if self.expire_session_once:
            self.expire_session_once = False
            return Response(401, '{"error": "session expired"}', {})
        if self.csrf_token and method != "GET" and headers.get("X-CSRF-Token") != self.csrf_token:
            return Response(403, '{"error": "CSRF"}', {})

        prefix = "/api/%s/" % self.api_version
        assert path.startswith(prefix), path
        # Odd segment count addresses a collection (devices, devices/<id>/services),
        # even addresses one object in it (devices/<id>, devices/<id>/services/<id>).
        parts = [unquote(p) for p in path[len(prefix):].strip("/").split("/")]
        is_collection = len(parts) % 2 == 1
        collection = "/".join(parts if is_collection else parts[:-1])
        items = self.collections.setdefault(collection, {})

        if is_collection:
            if method == "GET":
                found = list(items.values())
                for q in parse_qs(parsed.query).get("q", []):
                    field, value = q.split("=", 1)
                    # The real API's q= is a substring search; mimic it to exercise exact-match filtering.
                    found = [o for o in found if value in str(o.get(field, ""))]
                return Response(200, json.dumps(found), {})
            if method == "POST":
                obj = self.add(collection, body)
                return Response(204, "", {"X-Object-Id": obj["id"]} if self.return_object_id else {})
        else:
            obj = items.get(parts[-1])
            if obj is None:
                return Response(404, '{"error": "not found"}', {})
            if method == "GET":
                return Response(200, json.dumps(obj), {})
            if method == "PUT":
                obj.update(body)
                return Response(204, "", {})
            if method == "DELETE":
                del items[parts[-1]]
                return Response(204, "", {})
        return Response(405, "", {})


def _cookie(name, value):
    from http.cookiejar import Cookie
    return Cookie(0, name, value, None, False, "bastion.test", False, False, "/", True,
                  True, None, False, None, None, {})
