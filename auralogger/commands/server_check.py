"""`auralogger server-check` (mirrors node/src/cli/services/server-check.ts)."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, cast

import websocket
from websocket import create_connection

from auralogger.backend_origin import resolve_ws_base_url
from auralogger.env_config import require_project_token_for_cli, require_user_secret_for_cli
from auralogger.proj_auth import fetch_proj_auth_payload

CONNECT_TIMEOUT_S = 5


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
    project_token = require_project_token_for_cli()
    user_secret = require_user_secret_for_cli()

    raw = fetch_proj_auth_payload(project_token)
    auth = cast(Dict[str, Any], raw)
    project_id = auth.get("project_id")
    project_name = auth.get("project_name")
    session_raw = auth.get("session")
    session = session_raw.strip() if isinstance(session_raw, str) else ""
    if not session:
        raise ValueError("proj_auth response did not include a session string.")

    ws_base = resolve_ws_base_url()
    ws_url = _build_ws_url(project_token)
    print(f"Checking WebSocket connectivity to {ws_base} …")

    auth_header = f"Authorization: Bearer {user_secret}"

    try:
        ws = create_connection(
            ws_url,
            timeout=CONNECT_TIMEOUT_S,
            header=[auth_header],
        )
    except websocket.WebSocketTimeoutException as e:
        raise ValueError(
            f"WebSocket connect timed out after {CONNECT_TIMEOUT_S * 1000}ms."
        ) from e
    except Exception as e:
        raise ValueError(f"auralogger: server connect failed: {e}") from e

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
        raise ValueError(f"Could not pack the test log: {e}") from e

    try:
        ws.send(body)
    except Exception as e:
        try:
            ws.close()
        except Exception:
            pass
        raise ValueError(f"Log did not send — {e}") from e

    try:
        ws.close()
    except Exception:
        pass

    label = project_name if isinstance(project_name, str) and project_name.strip() else project_id
    print(
        f"Auralogger is reachable. Server logger accepted a test log for project {label!s}."
    )
