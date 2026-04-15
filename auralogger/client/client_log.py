"""Browser-ingest client runtime (Python parity for Node AuraClient)."""

from __future__ import annotations

import json
import sys
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

import websocket
from pydantic import BaseModel, Field
from websocket import create_connection

from auralogger.backend_origin import build_create_browser_logs_url, resolve_ws_base_url
from auralogger.env_config import get_resolved_project_token, try_parse_resolved_styles
from auralogger.log_print import print_log
from auralogger.log_styles import build_style_entries_from_api
from auralogger.proj_auth import fetch_proj_auth_payload

UNKNOWN_TYPE = "unknown"
CONNECT_TIMEOUT_S = 5
DEFAULT_SOCKET_IDLE_CLOSE_MS = 60_000

_ws: Optional[Any] = None
_bound_url: Optional[str] = None
_socket_idle_timer: Optional[threading.Timer] = None
_local_session_id: Optional[str] = None
_warned_missing_project_token = False
_warned_missing_project_id = False

_hydrate_lock = threading.Lock()
_hydration_cache_token: Optional[str] = None
_hydration_cache_raw: Optional[Dict[str, Any]] = None
_override_project_token: Optional[str] = None


class ClientLogInputs(BaseModel):
    type: Literal["debug", "info", "warn", "error"] = "info"
    message: str = Field(..., min_length=1)
    location: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


def _reset_socket_idle_timer() -> None:
    global _socket_idle_timer
    if _socket_idle_timer is not None:
        _socket_idle_timer.cancel()
        _socket_idle_timer = None


def _schedule_socket_idle_close() -> None:
    global _socket_idle_timer
    _reset_socket_idle_timer()

    def _close_if_idle() -> None:
        global _socket_idle_timer
        _socket_idle_timer = None
        close_client_log_socket()

    timer = threading.Timer(DEFAULT_SOCKET_IDLE_CLOSE_MS / 1000.0, _close_if_idle)
    timer.daemon = True
    timer.start()
    _socket_idle_timer = timer


def _close_ws_connection() -> None:
    global _ws, _bound_url
    _reset_socket_idle_timer()
    if _ws is not None:
        try:
            _ws.close()
        except Exception:
            pass
    _ws = None
    _bound_url = None


def close_client_log_socket() -> None:
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


def _resolve_project_token_runtime() -> Optional[str]:
    if _override_project_token is not None:
        s = _override_project_token.strip()
        if s:
            return s
    return get_resolved_project_token()


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


def _merged_runtime_for_send(project_token: str) -> Optional[Dict[str, Any]]:
    sess = ""
    styles = try_parse_resolved_styles()
    pid = ""
    need_fetch = not pid or not sess or styles is None

    if need_fetch:
        raw = _fetch_proj_auth_cached(project_token)
        if raw is None:
            return None
        x = raw.get("project_id")
        if isinstance(x, str):
            pid = x.strip()
        elif x is not None:
            pid = str(x).strip()
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


def _ensure_ws(project_token: str):
    global _ws, _bound_url
    url = build_create_browser_logs_url(resolve_ws_base_url(), project_token)
    if _ws is not None and _bound_url == url:
        return _ws
    _close_ws_connection()
    conn = create_connection(
        url,
        timeout=CONNECT_TIMEOUT_S,
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


def client_log(
    type: str,
    message: str,
    location: Optional[str] = None,
    data: Any = None,
) -> None:
    global _warned_missing_project_token, _warned_missing_project_id

    project_token = _resolve_project_token_runtime()
    if not project_token:
        if not _warned_missing_project_token:
            _warned_missing_project_token = True
            print(
                "auralogger: missing project token. Call AuraClient.configure(project_token) "
                "or set AURALOGGER_PROJECT_TOKEN.",
                file=sys.stderr,
            )
        return

    merged = _merged_runtime_for_send(project_token)
    can_send = merged is not None
    if not can_send and not _warned_missing_project_id:
        _warned_missing_project_id = True
        print(
            "auralogger: client logger is running in console-only mode. "
            "proj_auth did not yield a valid project id/session.",
            file=sys.stderr,
        )

    styles = _styles_for_console(project_token, merged)
    display_session = (
        merged["session"] if (merged is not None and merged.get("session")) else _get_or_create_local_session()
    )

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

    if not can_send:
        return

    try:
        body = json.dumps(payload)
    except (TypeError, ValueError) as e:
        print(f"auralogger: failed to serialize log payload: {e}", file=sys.stderr)
        return

    try:
        ws = _ensure_ws(project_token)
        ws.send(body)
        _schedule_socket_idle_close()
    except websocket.WebSocketTimeoutException as e:
        print(f"auralogger: websocket send failed (timeout): {e}", file=sys.stderr)
        close_client_log_socket()
    except Exception as e:
        print(f"auralogger: websocket send failed: {e}", file=sys.stderr)
        close_client_log_socket()


def auralog(loginputs: ClientLogInputs) -> None:
    AuraClient.log(
        loginputs.type,
        loginputs.message,
        loginputs.location,
        loginputs.data,
    )


class AuraClient:
    @staticmethod
    def configure(project_token: str) -> None:
        global _override_project_token, _warned_missing_project_token
        global _warned_missing_project_id, _local_session_id
        global _hydration_cache_token, _hydration_cache_raw
        trimmed = project_token.strip()
        if not trimmed:
            raise ValueError("AuraClient.configure: project token cannot be empty.")
        _override_project_token = trimmed
        _warned_missing_project_token = False
        _warned_missing_project_id = False
        _local_session_id = None
        with _hydrate_lock:
            _hydration_cache_token = None
            _hydration_cache_raw = None

    @staticmethod
    def sync_from_secret(project_token: str) -> None:
        trimmed = project_token.strip()
        if not trimmed:
            raise ValueError("AuraClient.sync_from_secret: project token cannot be empty.")
        AuraClient.configure(trimmed)
        raw = fetch_proj_auth_payload(trimmed)
        project_id_raw = raw.get("project_id")
        session_raw = raw.get("session")
        project_id = project_id_raw.strip() if isinstance(project_id_raw, str) else ""
        session = session_raw.strip() if isinstance(session_raw, str) else ""
        if not project_id or not session:
            raise ValueError(
                "AuraClient.sync_from_secret: proj_auth response missing project id or session."
            )
        with _hydrate_lock:
            global _hydration_cache_token, _hydration_cache_raw
            _hydration_cache_token = trimmed
            _hydration_cache_raw = raw

    @staticmethod
    def log(type: str, message: str, location: Optional[str] = None, data: Any = None) -> None:
        client_log(type, message, location, data)

    @staticmethod
    def close_socket(timeout_ms: int = 1000) -> None:
        _ = timeout_ms
        close_client_log_socket()
