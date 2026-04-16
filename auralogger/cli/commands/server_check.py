"""`auralogger server-check` — parity with node/src/cli/services/server-check.ts."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import websocket
from websocket import create_connection

from auralogger.cli.aside_pools import CHECK_RETRY_ASIDES, ENV_RECOVERY_HINT_PLAIN, SERVER_CHECK_FAIL_WOLVERINE_ASIDES, SERVER_CHECK_OPEN_ASIDES, SERVER_CHECK_SUCCESS_THOR_ASIDES, pick_aside
from auralogger.cli.cli_auth import resolve_project_context_for_cli_checks
from auralogger.cli.cli_load_env import ensure_utf8_stdio
from auralogger.cli.cli_style import bold_white, dim, green, hex_color, white
from auralogger.cli.cli_tone import maybe_print_generic_spice, print_aside
from auralogger.utils.backend_origin import resolve_ws_base_url

CONNECT_TIMEOUT_S = 5
MAX_RETRIES = 2
RETRY_WAIT_S = 0.7


def _encode_path_token(project_token: str) -> str:
    from urllib.parse import quote

    return quote(project_token.strip(), safe="-_.!~*'()")


def _build_ws_url(project_token: str) -> str:
    encoded = _encode_path_token(project_token)
    return f"{resolve_ws_base_url()}/{encoded}/create_log"


def _iso_timestamp_with_micros(epoch_ms: float) -> str:
    dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
    base = dt.strftime("%Y-%m-%dT%H:%M:%S")
    micros = f"{dt.microsecond:06d}"
    return f"{base}.{micros}Z"


def run_server_check() -> None:
    ensure_utf8_stdio()
    context = resolve_project_context_for_cli_checks()
    project_token = context.project_token
    user_secret = context.user_secret
    project_id = context.project_id
    project_name = context.project_name
    session = context.session

    print(
        dim("📡 ")
        + white("Pinging the ")
        + bold_white("server")
        + white(" logger — one tiny test log coming up…"),
    )
    a = pick_aside(SERVER_CHECK_OPEN_ASIDES)
    print_aside(a["emoji"], a["line"])

    ws_url = _build_ws_url(project_token)
    auth_header = f"Authorization: Bearer {user_secret}"

    def _send_attempt() -> None:
        try:
            ws = create_connection(
                ws_url,
                timeout=CONNECT_TIMEOUT_S,
                header=[auth_header],
            )
        except websocket.WebSocketTimeoutException:
            w = pick_aside(SERVER_CHECK_FAIL_WOLVERINE_ASIDES)
            print_aside(w["emoji"], w["line"])
            raise ValueError(
                "Server logger socket didn't open in time — still quiet. Check VPN/Wi‑Fi, firewall, "
                "AURALOGGER_WS_URL if you override it, and that token + user secret match this project. "
                + ENV_RECOVERY_HINT_PLAIN
            ) from None
        except Exception as e:
            w = pick_aside(SERVER_CHECK_FAIL_WOLVERINE_ASIDES)
            print_aside(w["emoji"], w["line"])
            raise ValueError(
                f"Server pipe wouldn't open ({e}). Verify creds in .env, run from the folder that loads "
                f"them, then try again. {ENV_RECOVERY_HINT_PLAIN}"
            ) from e

        now_ms = time.time() * 1000.0
        payload = {
            "type": "info",
            "message": "this is from cli server-check",
            "location": "cli/server-check",
            "session": session,
            "created_at": _iso_timestamp_with_micros(now_ms),
            "data": json.dumps({"kind": "server-check"}),
        }
        try:
            body = json.dumps(payload)
        except (TypeError, ValueError) as e:
            try:
                ws.close()
            except Exception:
                pass
            raise ValueError(f"Couldn't pack the test log: {e}") from e

        try:
            ws.send(body)
        except Exception as e:
            try:
                ws.close()
            except Exception:
                pass
            raise ValueError(f"Log didn't send — {e}") from e

        try:
            ws.close()
        except Exception:
            pass

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            _send_attempt()
            break
        except Exception:
            if attempt > MAX_RETRIES:
                raise
            print()
            r = pick_aside(CHECK_RETRY_ASIDES)
            print_aside(r["emoji"], r["line"])
            print(
                dim("🔁 ")
                + white("Retrying ")
                + bold_white("server-check")
                + white(f" (attempt {attempt + 1}/{MAX_RETRIES + 1})...")
            )
            time.sleep(RETRY_WAIT_S)

    label = project_name or project_id
    print()
    print(
        green("🎉 ")
        + white("Server logger is alive — a test log just took off for project ")
        + hex_color("#ffa657", label)
        + white("."),
    )
    a = pick_aside(SERVER_CHECK_SUCCESS_THOR_ASIDES)
    print_aside(a["emoji"], a["line"])
    maybe_print_generic_spice()
