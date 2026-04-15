"""Fetch and print logs (mirrors node/src/cli/services/get-logs.ts)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Mapping, Tuple, cast

from auralogger.cli.cli_auth import resolve_project_token_for_init, resolve_user_secret_for_init
from auralogger.cli.get_logs_filters import normalize_and_validate_filters
from auralogger.cli.log_print import print_log
from auralogger.cli.log_styles import build_style_entries_from_api
from auralogger.server.proj_auth import fetch_proj_auth_payload
from auralogger.utils.backend_origin import build_project_logs_url, resolve_api_base_url
from auralogger.utils.env_config import try_parse_resolved_styles
from auralogger.utils.http_utils import parse_error_body
from auralogger.utils.parser import parse_command


def _is_record(value: object) -> bool:
    return isinstance(value, dict)


def _post_logs(
    base_url: str,
    project_token: str,
    user_secret: str,
    filters: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], bool]:
    route = build_project_logs_url(base_url, project_token)
    body_bytes = json.dumps({"filters": filters}).encode("utf8")
    headers = {
        "secret": user_secret,
        "user_secret": user_secret,
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(route, data=body_bytes, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            raw = resp.read()
            hdrs = resp.headers
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(
                "POST /api/{project_token}/logs returned 404 — wrong API host, old backend, "
                "or route not deployed. Check AURALOGGER_API_URL.",
                file=sys.stderr,
            )
            return {"logs": []}, True
        status = e.code
        raw = e.read()
        hdrs = e.headers
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        raise ValueError(f"Unable to reach {base_url}: {reason}") from e

    if status < 200 or status >= 300:
        ctype = hdrs.get("content-type", "")
        raise ValueError(parse_error_body(status, ctype, raw))

    try:
        body: object = json.loads(raw.decode("utf8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("Logs response was not valid JSON.") from None

    if not _is_record(body):
        raise ValueError("Logs response had an unexpected shape.")
    return cast(Dict[str, Any], body), False


def _resolve_config_styles(project_token: str) -> List[Any]:
    from_env = try_parse_resolved_styles()
    if from_env is not None:
        return from_env
    try:
        raw = fetch_proj_auth_payload(project_token)
        styles_raw = raw.get("styles")
        rows = styles_raw if isinstance(styles_raw, list) else []
        print(
            "No styles in your shell — using freshly fetched styling for this run.",
            file=sys.stderr,
        )
        return build_style_entries_from_api(rows)
    except ValueError as e:
        print(
            f"Could not load styles from the API ({e}). Using default terminal colors.",
            file=sys.stderr,
        )
        return build_style_entries_from_api([])


def run_get_logs(argv: List[str]) -> None:
    project_token = resolve_project_token_for_init()
    user_secret = resolve_user_secret_for_init()
    config_styles = _resolve_config_styles(project_token)

    parsed = parse_command(argv)
    filters = normalize_and_validate_filters(parsed.filters)

    base_url = resolve_api_base_url()
    body, logs_endpoint_not_found = _post_logs(
        base_url, project_token, user_secret, filters
    )

    logs_raw = body.get("logs")
    logs = logs_raw if isinstance(logs_raw, list) else []
    if len(logs) == 0:
        if not logs_endpoint_not_found:
            print("No logs matched your filters.")
        return

    for item in logs:
        if _is_record(item):
            print_log(cast(Mapping[str, Any], item), config_styles)
