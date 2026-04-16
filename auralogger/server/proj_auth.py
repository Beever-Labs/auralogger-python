"""Shared ``POST .../proj_auth`` client (mirrors node ``fetchProjAuthConfig``)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, cast

from auralogger.utils.backend_origin import build_proj_auth_url, resolve_api_base_url
from auralogger.utils.recovery_messages import ENV_RECOVERY_HINT_PLAIN
from auralogger.utils.http_utils import parse_error_body


def fetch_proj_auth_payload(project_token: str) -> Dict[str, Any]:
    """
    ``POST /api/{project_token}/proj_auth`` with no auth headers.
    Returns the decoded JSON object (minimal validation: must be a dict).
    """
    base = resolve_api_base_url()
    url = build_proj_auth_url(base, project_token)
    req = urllib.request.Request(url, data=b"", method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            raw_body = resp.read()
            headers = resp.headers
    except urllib.error.HTTPError as e:
        status = e.code
        raw_body = e.read()
        headers = e.headers
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        raise ValueError(
            f"Can't reach Auralogger right now — check your network or VPN, then try again. ({reason}) "
            f"{ENV_RECOVERY_HINT_PLAIN}"
        ) from e

    if status < 200 or status >= 300:
        ctype = headers.get("content-type", "")
        raise ValueError(parse_error_body(status, ctype, raw_body))

    try:
        auth_response: object = json.loads(raw_body.decode("utf8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError(
            "Authentication succeeded but response was not valid JSON."
        ) from None

    if not isinstance(auth_response, dict):
        raise ValueError("Authentication response had an unexpected shape.")

    return cast(Dict[str, Any], auth_response)


def fetch_proj_auth_config(project_token: str) -> Dict[str, Any]:
    """
    Node-parity alias for ``fetch_proj_auth_payload``.

    Mirrors the Node SDK naming (`fetchProjAuthConfig`) while preserving
    Python's existing public function name for backward compatibility.
    """
    return fetch_proj_auth_payload(project_token)
