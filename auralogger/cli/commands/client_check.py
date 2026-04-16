"""`auralogger client-check` — parity with node/src/cli/services/client-check.ts."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import websocket
from websocket import create_connection

from auralogger.cli.aside_pools import CHECK_RETRY_ASIDES, ENV_RECOVERY_HINT_PLAIN, CLIENT_CHECK_START_PETER_ASIDES, CLIENT_CHECK_SUCCESS_ASIDES, pick_aside
from auralogger.cli.cli_auth import resolve_project_context_for_cli_checks
from auralogger.cli.cli_load_env import ensure_utf8_stdio
from auralogger.cli.cli_style import bold_white, dim, green, hex_color, white
from auralogger.cli.cli_tone import maybe_print_generic_spice, print_aside
from auralogger.utils.backend_origin import (
    build_create_browser_logs_url,
    resolve_ws_base_url,
)

CONNECT_TIMEOUT_S = 5
MAX_RETRIES = 2
RETRY_WAIT_S = 0.7


def _iso_timestamp_with_micros(epoch_ms: float) -> str:
    dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
    base = dt.strftime("%Y-%m-%dT%H:%M:%S")
    micros = f"{dt.microsecond:06d}"
    return f"{base}.{micros}Z"


def run_client_check() -> None:
    ensure_utf8_stdio()
    context = resolve_project_context_for_cli_checks()
    project_token = context.project_token
    project_id = context.project_id
    project_name = context.project_name
    session = context.session

    print(
        dim("🌐 ")
        + white("Trying the ")
        + bold_white("browser-style")
        + white(" log tunnel (path-only socket auth)…"),
    )
    a = pick_aside(CLIENT_CHECK_START_PETER_ASIDES)
    print_aside(a["emoji"], a["line"])

    ws_base = resolve_ws_base_url()
    ws_url = build_create_browser_logs_url(ws_base, project_token)

    def _send_attempt() -> None:
        try:
            ws = create_connection(ws_url, timeout=CONNECT_TIMEOUT_S)
        except websocket.WebSocketTimeoutException as e:
            raise ValueError(
                "Browser-style socket never connected — check network/VPN, corporate proxy, and "
                "AURALOGGER_WS_URL if custom; token must match the project. "
                + ENV_RECOVERY_HINT_PLAIN
            ) from e
        except Exception as e:
            raise ValueError(
                f"Browser tunnel error ({e}). Same fixes as timeout: network, proxy, env in the right "
                f"cwd, then rerun. {ENV_RECOVERY_HINT_PLAIN}"
            ) from e

        now_ms = time.time() * 1000.0
        payload = {
            "type": "info",
            "message": "this is from cli client-check",
            "location": "cli/client-check",
            "session": session,
            "created_at": _iso_timestamp_with_micros(now_ms),
            "data": json.dumps({"kind": "client-check"}),
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
                + bold_white("client-check")
                + white(f" (attempt {attempt + 1}/{MAX_RETRIES + 1})...")
            )
            time.sleep(RETRY_WAIT_S)

    label = project_name or project_id
    print()
    print(
        green("🎉 ")
        + white("Browser-style path works — test log zoomed for project ")
        + hex_color("#ffa657", label)
        + white("."),
    )
    a = pick_aside(CLIENT_CHECK_SUCCESS_ASIDES)
    print_aside(a["emoji"], a["line"])
    maybe_print_generic_spice()
