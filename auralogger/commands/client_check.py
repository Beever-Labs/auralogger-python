"""`auralogger client-check` - browser-ingest WebSocket probe."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import websocket
from websocket import create_connection

from auralogger.backend_origin import (
    build_create_browser_logs_url,
    resolve_ws_base_url,
)
from auralogger.cli_auth import resolve_project_context_for_cli_checks

CONNECT_TIMEOUT_S = 5


def _iso_timestamp_with_micros(epoch_ms: float) -> str:
    dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
    base = dt.strftime("%Y-%m-%dT%H:%M:%S")
    micros = f"{dt.microsecond:06d}"
    return f"{base}.{micros}Z"


def run_client_check() -> None:
    context = resolve_project_context_for_cli_checks()
    project_token = context.project_token
    project_id = context.project_id
    project_name = context.project_name
    session = context.session

    ws_base = resolve_ws_base_url()
    ws_url = build_create_browser_logs_url(ws_base, project_token)
    print(f"Checking browser ingest connectivity to {ws_base} ...")

    try:
        # Browser ingest route is path-auth only; do not send auth headers.
        ws = create_connection(ws_url, timeout=CONNECT_TIMEOUT_S)
    except websocket.WebSocketTimeoutException as e:
        raise ValueError(
            f"Browser ingest connect timed out after {CONNECT_TIMEOUT_S * 1000}ms."
        ) from e
    except Exception as e:
        raise ValueError(f"auralogger: client-check connect failed: {e}") from e

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
        raise ValueError(f"Could not pack the test log: {e}") from e

    try:
        ws.send(body)
    except Exception as e:
        try:
            ws.close()
        except Exception:
            pass
        raise ValueError(f"Log did not send - {e}") from e

    try:
        ws.close()
    except Exception:
        pass

    label = project_name or project_id
    print(
        f"Browser ingest is reachable. Client check log accepted for project {label!s}."
    )
