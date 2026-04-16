"""Fetch and print logs — parity with node/src/cli/services/get-logs.ts."""

from __future__ import annotations

import json
import random
import urllib.error
import urllib.request
from typing import Any, Dict, List, Mapping, Tuple, cast

from auralogger.cli.aside_pools import (
    ENV_RECOVERY_HINT_PLAIN,
    GET_LOGS_DEADPOOL_SCROLL_ASIDES,
    GET_LOGS_EMPTY_ASIDES,
    GET_LOGS_OPEN_ASIDES,
    GET_LOGS_SKIPPED_SETUP_INTENT_ASIDES,
    GET_LOGS_STYLES_ASIDES,
    GET_LOGS_SUCCESS_TEMPLATES,
    format_aside_template,
    pick_aside,
)
from auralogger.cli.cli_auth import resolve_project_token_for_init, resolve_user_secret_for_init
from auralogger.cli.cli_load_env import ensure_utf8_stdio
from auralogger.cli.cli_personality_state import get_successful_run_count
from auralogger.cli.cli_style import bold_hex, cyan, dim, hex_color, white, yellow
from auralogger.cli.cli_tone import maybe_print_generic_spice, print_aside, print_aside_maybe
from auralogger.cli.get_logs_filters import normalize_and_validate_filters
from auralogger.cli.log_print import print_log
from auralogger.cli.log_styles import build_style_entries_from_api
from auralogger.server.proj_auth import fetch_proj_auth_payload
from auralogger.utils.backend_origin import build_project_logs_url, resolve_api_base_url
from auralogger.utils.env_config import get_resolved_project_token, try_parse_resolved_styles
from auralogger.utils.http_utils import parse_error_body
from auralogger.utils.parser import parse_command


def _is_record(value: object) -> bool:
    return isinstance(value, dict)


def format_get_logs_help() -> str:
    return "\n".join(
        [
            "🔍 Filter syntax (get-logs):",
            "  -<field> [--<op>] <json-value-token>",
            "",
            "Value rules:",
            "  - maxcount, skip: JSON number (e.g. 50)",
            "  - everything else: JSON array (e.g. [\"error\",\"warn\"])",
            "",
            "Examples:",
            "  auralogger get-logs -type '[\"error\",\"warn\"]' -maxcount 50",
            "  auralogger get-logs -message '[\"timeout\"]' -skip 20 -maxcount 30",
            "  auralogger get-logs -type --not-in '[\"info\",\"debug\"]' -time --since '[\"10m\"]'",
            '  auralogger get-logs -data.userId \'["06431f39-55e2-4289-80c8-5d0340a8b66e"]\'',
        ]
    )


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
                yellow("⚠️ ")
                + white("POST ")
                + dim("/api/{project_token}/logs")
                + white(
                    " returned 404 — wrong API host, old backend, or route not deployed. "
                )
                + dim("Check ")
                + cyan("AURALOGGER_API_URL")
                + dim("."),
            )
            return {"logs": []}, True
        status = e.code
        raw = e.read()
        hdrs = e.headers
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        raise ValueError(
            f"Can't reach Auralogger to fetch logs — check connection and try again. ({reason}) "
            f"{ENV_RECOVERY_HINT_PLAIN}"
        ) from e

    if status < 200 or status >= 300:
        ctype = hdrs.get("content-type", "")
        body_text = parse_error_body(status, ctype, raw)
        authish = status == 401 or status == 403
        raise ValueError(
            f"{body_text} {ENV_RECOVERY_HINT_PLAIN}" if authish else body_text
        )

    try:
        body: object = json.loads(raw.decode("utf8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("The log list came back garbled (not JSON). Try again?") from None

    if not _is_record(body):
        raise ValueError("The log list didn’t look right. Weird — try again.")
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
            hex_color("#79c0ff", "🎨 ")
            + white("No styles in your shell — using freshly fetched styling for this run.")
        )
        a = pick_aside(GET_LOGS_STYLES_ASIDES)
        print_aside(a["emoji"], a["line"])
        if random.random() < 0.35:
            d = pick_aside(GET_LOGS_DEADPOOL_SCROLL_ASIDES)
            print_aside(d["emoji"], d["line"])
        return build_style_entries_from_api(rows)
    except ValueError as e:
        print(
            yellow("⚠️ ")
            + white(
                f"Couldn’t load styles from the API ({e}). Using default terminal colors for log lines."
            )
        )
        print(
            dim("   Set ")
            + cyan("AURALOGGER_PROJECT_STYLES")
            + dim(" (or NEXT_PUBLIC_/VITE_…) from ")
            + cyan("auralogger init")
            + dim(" to match the dashboard, or fix API/network access.")
        )
        return build_style_entries_from_api([])


def run_get_logs_core(
    project_token: str,
    user_secret: str,
    config_styles: Any,
    argv: List[str],
) -> None:
    try:
        parsed = parse_command(argv)
        filters = normalize_and_validate_filters(parsed.filters)
    except Exception as e:
        msg = str(e)
        raise ValueError(f"{msg}\n\n{format_get_logs_help()}") from e

    base_url = resolve_api_base_url()
    body, logs_endpoint_not_found = _post_logs(base_url, project_token, user_secret, filters)

    logs_raw = body.get("logs")
    logs = logs_raw if isinstance(logs_raw, list) else []
    if len(logs) == 0:
        if logs_endpoint_not_found:
            return
        print(
            yellow("👻 ")
            + white(
                "Nothing matched — try looser filters, smaller -skip, or bigger -maxcount; "
                "if it's a new project, maybe nothing's logged yet."
            )
        )
        a = pick_aside(GET_LOGS_EMPTY_ASIDES)
        print_aside(a["emoji"], a["line"])
        return

    printed = 0
    for item in logs:
        if _is_record(item):
            print_log(cast(Mapping[str, Any], item), config_styles)
            printed += 1
    if printed > 0:
        t = pick_aside(GET_LOGS_SUCCESS_TEMPLATES)
        print_aside(
            t["emoji"],
            format_aside_template(t["line"], {"n": printed}),
        )


def run_get_logs(argv: List[str]) -> None:
    ensure_utf8_stdio()
    if not get_resolved_project_token() and get_successful_run_count("init") == 0:
        a = pick_aside(GET_LOGS_SKIPPED_SETUP_INTENT_ASIDES)
        print_aside_maybe(a["emoji"], a["line"], 0.12)

    print(
        bold_hex("#79c0ff", "📜 ") + white("get-logs — opening the archive…"),
    )
    a = pick_aside(GET_LOGS_OPEN_ASIDES)
    print_aside_maybe(a["emoji"], a["line"], 0.12)

    project_token = resolve_project_token_for_init()
    user_secret = resolve_user_secret_for_init()
    config_styles = _resolve_config_styles(project_token)

    run_get_logs_core(project_token, user_secret, config_styles, argv)
    maybe_print_generic_spice()
