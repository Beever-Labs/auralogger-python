"""Runtime log helper: styled console line + optional WebSocket send (mirrors node aura-log / server-log)."""

from __future__ import annotations

import json
import sys
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import websocket
from websocket import create_connection

from auralogger.backend_origin import resolve_ws_base_url
from auralogger.env_config import (
    get_resolved_project_token,
    get_resolved_session,
    get_resolved_user_secret,
    try_parse_resolved_styles,
)
from auralogger.log_print import print_log
from auralogger.log_styles import build_style_entries_from_api
from auralogger.proj_auth import fetch_proj_auth_payload

UNKNOWN_TYPE = "unknown"
CONNECT_TIMEOUT_S = 5

_ws: Optional[Any] = None
_bound_url: Optional[str] = None
_warned_incomplete_env = False
_local_session_id: Optional[str] = None

_hydrate_lock = threading.Lock()
_hydration_cache_token: Optional[str] = None
_hydration_cache_raw: Optional[Dict[str, Any]] = None


def _encode_path_token(project_token: str) -> str:
    from urllib.parse import quote

    return quote(project_token.strip(), safe="-_.!~*'()")


def _build_ws_url(project_token: str) -> str:
    encoded = _encode_path_token(project_token)
    return f"{resolve_ws_base_url()}/{encoded}/create_log"


def _is_plain_object(value: Any) -> bool:
    return isinstance(value, dict)


def _normalize_type(raw: str) -> str:
    s = (raw or "").strip()
    return s if s else UNKNOWN_TYPE


def _normalize_location(location: Optional[str]) -> Optional[str]:
    if not isinstance(location, str):
        return None
    s = location.strip()
    return s or None


def _maybe_data(data: Any) -> Optional[str]:
    if data is None:
        return None
    if isinstance(data, str):
        return data
    if _is_plain_object(data):
        try:
            return json.dumps(data)
        except (TypeError, ValueError):
            return None
    return None


def _iso_timestamp_utc(dt: Optional[datetime] = None) -> str:
    now = dt or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    base = now.strftime("%Y-%m-%dT%H:%M:%S")
    micros = f"{now.microsecond:06d}"
    return f"{base}.{micros}Z"


def _get_or_create_local_session() -> str:
    global _local_session_id
    if _local_session_id is None:
        _local_session_id = str(uuid.uuid4())
    return _local_session_id


def _close_ws_connection() -> None:
    global _ws, _bound_url
    if _ws is not None:
        try:
            _ws.close()
        except Exception:
            pass
    _ws = None
    _bound_url = None


def close_aura_log_socket() -> None:
    """Close the cached WebSocket and drop cached ``proj_auth`` data for this process."""
    global _hydration_cache_token, _hydration_cache_raw
    _close_ws_connection()
    _hydration_cache_token = None
    _hydration_cache_raw = None


def _fetch_proj_auth_cached(project_token: str) -> Optional[Dict[str, Any]]:
    global _hydration_cache_token, _hydration_cache_raw
    with _hydrate_lock:
        if _hydration_cache_token == project_token and _hydration_cache_raw is not None:
            return _hydration_cache_raw
        try:
            raw = fetch_proj_auth_payload(project_token)
        except ValueError:
            return None
        _hydration_cache_token = project_token
        _hydration_cache_raw = raw
        return raw


def _merged_runtime_for_send(project_token: str) -> Optional[Dict[str, Any]]:
    from auralogger.env_config import get_resolved_project_id

    pid = (get_resolved_project_id() or "").strip()
    sess = (get_resolved_session() or "").strip()
    styles = try_parse_resolved_styles()

    need_fetch = not pid or not sess or styles is None

    if need:
        raw = _fetch_proj_auth_cached(project_token)
        if raw is None:
            return None
        if not pid:
            x = raw.get("project_id")
            if isinstance(x, str):
                pid = x.strip()
            elif x is not None:
                pid = str(x).strip()
            else:
                pid = ""
        if not sess:
            x = raw.get("session")
            sess = x.strip() if isinstance(x, str) else ""
        if styles is None:
            rows = raw.get("styles")
            rows = rows if isinstance(rows, list) else []
            styles = build_style_entries_from_api(rows)

    if not pid or not sess:
        return None
    if styles is None:
        styles = build_style_entries_from_api([])
    return {"project_id": pid, "session": sess, "styles": styles}


def _ensure_ws(project_token: str, user_secret: str):
    global _ws, _bound_url
    url = _build_ws_url(project_token)
    if _ws is not None and _bound_url == url:
        return _ws
    _close_ws_connection()
    conn = create_connection(
        url,
        timeout=CONNECT_TIMEOUT_S,
        header=[f"Authorization: Bearer {user_secret}"],
    )
    _ws = conn
    _bound_url = url
    return conn


def _styles_for_console(
    project_token: Optional[str], merged: Optional[Dict[str, Any]]
) -> Any:
    s = try_parse_resolved_styles()
    if s is not None:
        return s
    if merged is not None:
        return merged.get("styles")
    if project_token:
        raw = _fetch_proj_auth_cached(project_token)
        if raw is not None:
            rows = raw.get("styles")
            rows = rows if isinstance(rows, list) else []
            return build_style_entries_from_api(rows)
    return None


def aura_log(
    type: str,
    message: str,
    location: Optional[str] = None,
    data: Any = None,
) -> None:
    """
    Print a styled log line locally and, when ``AURALOGGER_PROJECT_TOKEN``,
    ``AURALOGGER_USER_SECRET``, and resolved project context are available,
    send the same payload over the logging WebSocket.
    """
    global _warned_incomplete_env

    project_token = get_resolved_project_token()
    user_secret = get_resolved_user_secret()

    merged = None
    if project_token and user_secret:
        merged = _merged_runtime_for_send(project_token)

    can_send = bool(project_token and user_secret and merged is not None)
    console_only = not can_send

    if console_only and not _warned_incomplete_env:
        _warned_incomplete_env = True
        print(
            "auralogger: logging to console only. Set "
            "AURALOGGER_PROJECT_TOKEN and AURALOGGER_USER_SECRET; id/session/styles "
            "can be filled via proj_auth when the API is reachable (run "
            '"auralogger init" for env hints).',
            file=sys.stderr,
        )

    styles = _styles_for_console(project_token, merged)

    if console_only:
        display_session = _get_or_create_local_session()
    else:
        assert merged is not None
        sess = merged["session"]
        display_session = sess if sess else _get_or_create_local_session()

    payload: Dict[str, Any] = {
        "type": _normalize_type(type),
        "message": "" if message is None else str(message),
        "session": display_session,
        "created_at": _iso_timestamp_utc(),
    }
    loc = _normalize_location(location)
    if loc is not None:
        payload["location"] = loc
    data_str = _maybe_data(data)
    if data_str is not None:
        payload["data"] = data_str

    try:
        print_log(payload, styles)
    except Exception as e:
        print(f"auralogger: failed to print log: {e}", file=sys.stderr)

    if console_only:
        return

    assert merged is not None
    assert project_token is not None
    assert user_secret is not None

    remote_session = merged["session"]
    payload["session"] = remote_session

    try:
        body = json.dumps(payload)
    except (TypeError, ValueError) as e:
        print(f"auralogger: failed to serialize log payload: {e}", file=sys.stderr)
        return

    try:
        ws = _ensure_ws(project_token, user_secret)
        ws.send(body)
    except websocket.WebSocketTimeoutException as e:
        print(f"auralogger: websocket send failed (timeout): {e}", file=sys.stderr)
        close_aura_log_socket()
    except Exception as e:
        print(f"auralogger: websocket send failed: {e}", file=sys.stderr)
        close_aura_log_socket()
