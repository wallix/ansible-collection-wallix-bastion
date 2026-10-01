# -*- coding: utf-8 -*-
# Copyright (c) 2026, WALLIX
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""HTTP client for the WALLIX Bastion REST API.

Mirrors the session handling of terraform-provider-wallix-bastion (bastion/client.go):
authenticate once with POST /api (basic auth or X-Auth-User/X-Auth-Key), keep the
wab_session_id cookie, send the CSRF token when the Bastion issues one, re-authenticate
once on 401 and refresh the CSRF token once on 403.

This file has no dependency on AnsibleModule so it can be shared by modules and
controller-side plugins (lookups).
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import os

from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import quote

from ansible.module_utils.urls import Request

DEFAULT_API_VERSION = "v3.12"
SUPPORTED_API_VERSIONS = ("v3.8", "v3.12")
SESSION_COOKIE = "wab_session_id"
CSRF_COOKIE = "api_csrf_token"
CSRF_HEADER = "X-CSRF-Token"
USER_AGENT = "ansible-collection-wallix-bastion"

# Connection options shared by every module, see plugins/doc_fragments/connection.py.
CONNECTION_ARGUMENT_SPEC = dict(
    bastion_host=dict(type="str"),
    bastion_port=dict(type="int"),
    bastion_user=dict(type="str"),
    bastion_password=dict(type="str", no_log=True),
    bastion_token=dict(type="str", no_log=True),
    api_version=dict(type="str"),
    validate_certs=dict(type="bool"),
    csrf_enabled=dict(type="bool"),
    bastion_timeout=dict(type="int", default=30),
)

_TRUE = ("1", "true", "yes", "on")


class BastionError(Exception):
    """Raised for transport failures and unexpected API responses."""

    def __init__(self, message, status=None, body=None):
        super(BastionError, self).__init__(message)
        self.status = status
        self.body = body


class Response:
    def __init__(self, status, body, headers):
        self.status = status
        self.body = body
        self.headers = headers or {}

    def json(self):
        if not self.body:
            return None
        try:
            return json.loads(self.body)
        except ValueError:
            raise BastionError("Invalid JSON in API response", self.status, self.body)

    def header(self, name):
        for key, value in self.headers.items():
            if key.lower() == name.lower():
                return value
        return None


def _env_bool(name):
    value = os.environ.get(name)
    if value is None or value == "":
        return None
    return value.strip().lower() in _TRUE


def resolve_connection(params):
    """Fill unset connection options from the environment, like the provider's EnvDefaultFunc.

    Uses the same variable names as terraform-provider-wallix-bastion so a shell configured
    for Terraform works unchanged.
    """
    conn = dict(params)
    env_map = dict(
        bastion_host="WALLIX_BASTION_HOST",
        bastion_user="WALLIX_BASTION_USER",
        bastion_password="WALLIX_BASTION_PASSWORD",
        bastion_token="WALLIX_BASTION_TOKEN",
        api_version="WALLIX_BASTION_API_VERSION",
    )
    for option, env in env_map.items():
        if not conn.get(option):
            conn[option] = os.environ.get(env) or None

    if conn.get("bastion_port") is None:
        port = os.environ.get("WALLIX_BASTION_PORT")
        conn["bastion_port"] = int(port) if port else 443
    if not conn.get("api_version"):
        conn["api_version"] = DEFAULT_API_VERSION
    if conn.get("csrf_enabled") is None:
        env = _env_bool("WALLIX_CSRF_ENABLED")
        conn["csrf_enabled"] = True if env is None else env
    if conn.get("validate_certs") is None:
        env = _env_bool("WALLIX_BASTION_VALIDATE_CERTS")
        if env is None:
            insecure = _env_bool("WALLIX_INSECURE_SKIP_VERIFY")
            env = not insecure if insecure is not None else True
        conn["validate_certs"] = env
    if conn.get("bastion_timeout") is None:
        conn["bastion_timeout"] = 30
    return conn


def validate_connection(conn):
    """Return an error message for an unusable connection, or None."""
    if not conn.get("bastion_host"):
        return "bastion_host is required (or set WALLIX_BASTION_HOST)"
    if not conn.get("bastion_user"):
        return "bastion_user is required (or set WALLIX_BASTION_USER)"
    if not conn.get("bastion_password") and not conn.get("bastion_token"):
        return ("one of bastion_password or bastion_token is required "
                "(or set WALLIX_BASTION_PASSWORD / WALLIX_BASTION_TOKEN)")
    if not 0 < conn["bastion_port"] <= 65535:
        return "bastion_port must be between 1 and 65535, got %d" % conn["bastion_port"]
    if conn["api_version"] not in SUPPORTED_API_VERSIONS:
        return "api_version must be one of %s, got %s" % (", ".join(SUPPORTED_API_VERSIONS), conn["api_version"])
    return None


class BastionClient:
    def __init__(self, bastion_host, bastion_user, bastion_password=None, bastion_token=None,
                 bastion_port=443, api_version=DEFAULT_API_VERSION, validate_certs=True,
                 csrf_enabled=True, bastion_timeout=30, **kwargs):
        self.host = bastion_host
        self.port = bastion_port
        self.user = bastion_user
        self.password = bastion_password
        self.token = bastion_token
        self.api_version = api_version
        self.validate_certs = validate_certs
        self.csrf_enabled = csrf_enabled
        self.timeout = bastion_timeout

        self._cookies = CookieJar()
        self._csrf_token = None
        self._authenticated = False

    @classmethod
    def from_params(cls, params):
        return cls(**resolve_connection(params))

    @property
    def base_url(self):
        host = self.host
        if ":" in host and not host.startswith("["):
            host = "[%s]" % host  # IPv6 literal
        return "https://%s:%d" % (host, self.port)

    def _open(self, method, url, data=None, headers=None, url_username=None, url_password=None,
              force_basic_auth=False):
        """Single HTTP exchange. Returns a Response for every HTTP status; raises only on transport errors."""
        request = Request(
            cookies=self._cookies,
            validate_certs=self.validate_certs,
            timeout=self.timeout,
            http_agent=USER_AGENT,
        )
        try:
            resp = request.open(
                method, url, data=data, headers=headers,
                url_username=url_username, url_password=url_password,
                force_basic_auth=force_basic_auth,
            )
            return Response(resp.getcode(), resp.read().decode("utf-8"), dict(resp.headers))
        except HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            return Response(e.code, body, dict(e.headers or {}))
        except URLError as e:
            raise BastionError("Cannot reach WALLIX Bastion at %s: %s" % (self.base_url, e.reason))

    def _cookie(self, name):
        for cookie in self._cookies:
            if cookie.name == name:
                return cookie.value
        return None

    def _extract_csrf(self, resp):
        if not self.csrf_enabled:
            return
        self._csrf_token = resp.header(CSRF_HEADER) or self._cookie(CSRF_COOKIE) or self._csrf_token

    def authenticate(self):
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        kwargs = {}
        if self.token:
            headers["X-Auth-User"] = self.user
            headers["X-Auth-Key"] = self.token
        else:
            kwargs = dict(url_username=self.user, url_password=self.password, force_basic_auth=True)

        resp = self._open("POST", self.base_url + "/api", headers=headers, **kwargs)
        if not 200 <= resp.status < 300:
            raise BastionError(
                "Authentication to WALLIX Bastion failed: HTTP %d: %s" % (resp.status, resp.body.strip()),
                resp.status, resp.body)
        if not self._cookie(SESSION_COOKIE):
            raise BastionError("Authentication to WALLIX Bastion failed: no %s cookie returned" % SESSION_COOKIE)
        self._extract_csrf(resp)
        self._authenticated = True

    def url(self, path):
        return "%s/api/%s/%s" % (self.base_url, self.api_version, path.lstrip("/"))

    def request(self, method, path, body=None, headers=None):
        """Authenticated API call. Returns a Response whatever the HTTP status.

        `headers` adds request headers, e.g. X-Key-Passphrase for checkouts.
        """
        if not self._authenticated:
            self.authenticate()
        extra_headers = headers or {}

        def send():
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            headers.update(extra_headers)
            if self.csrf_enabled and self._csrf_token:
                headers[CSRF_HEADER] = self._csrf_token
            data = json.dumps(body) if body is not None else None
            return self._open(method, self.url(path), data=data, headers=headers)

        resp = send()
        if resp.status == 401:
            self._authenticated = False
            self._cookies.clear()
            self.authenticate()
            resp = send()
        elif resp.status == 403 and self.csrf_enabled and self._csrf_token:
            self._csrf_token = None
            self._extract_csrf(resp)
            resp = send()
        return resp

    def call(self, method, path, body=None, expected=(200, 204), headers=None):
        """API call that raises BastionError unless the status is expected. Returns the Response."""
        resp = self.request(method, path, body, headers=headers)
        if resp.status not in expected:
            raise BastionError(
                "%s %s returned HTTP %d: %s" % (method, path, resp.status, resp.body.strip()),
                resp.status, resp.body)
        return resp

    def get(self, path):
        """GET returning decoded JSON, or None on 404."""
        resp = self.call("GET", path, expected=(200, 404))
        if resp.status == 404:
            return None
        return resp.json()

    def find(self, path, field, value):
        """Return the object of a collection whose `field` equals `value` exactly, or None.

        Same lookup as the provider's searchResource* helpers (GET <path>?q=<field>=<value>),
        with an exact-match filter since q= may match more than one object.
        """
        results = self.get("%s?q=%s=%s" % (path.rstrip("/"), field, quote(value, safe=""))) or []
        matches = [r for r in results if r.get(field) == value]
        if len(matches) > 1:
            raise BastionError("More than one object in %s has %s=%s" % (path, field, value))
        return matches[0] if matches else None
