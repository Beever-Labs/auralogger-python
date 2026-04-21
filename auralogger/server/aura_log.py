"""Runtime log helper: styled console line + optional WebSocket send (mirrors node aura-log / server-log)."""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import websocket
from websocket import create_connection

from auralogger.cli.log_print import print_log
from auralogger.cli.log_styles import build_style_entries_from_api
from auralogger.server.proj_auth import fetch_proj_auth_payload
from auralogger.utils.backend_origin import resolve_ws_base_url
from auralogger.utils.env_config import (
    get_resolved_project_token,
    get_resolved_session,
    get_resolved_user_secret,
    try_parse_resolved_styles,
)

UNKNOWN_TYPE = "unknown"
CONNECT_TIMEOUT_S = 5
SDK_RETRY_ATTEMPTS = 3
SDK_RETRY_DELAY_S = 0.5
BATCH_FLUSH_INTERVAL_S = 0.03
BATCH_MAX_SIZE = 30

_ws: Optional[Any] = None
_bound_url: Optional[str] = None
_local_session_id: Optional[str] = None

_hydrate_lock = threading.Lock()
_hydration_cache_token: Optional[str] = None
_hydration_cache_raw: Optional[Dict[str, Any]] = None
_override_project_token: Optional[str] = None
_override_user_secret: Optional[str] = None
_encrypted: bool = True
_send_buffer_lock = threading.Lock()
_send_buffer: list[Dict[str, Any]] = []
_flush_timer: Optional[threading.Timer] = None


def _suppress_websocket_client_noise() -> None:
    """Hide websocket-client connection/debug logs unless app explicitly overrides."""
    logging.getLogger("websocket").setLevel(logging.WARNING)


_suppress_websocket_client_noise()


def _encode_path_token(project_token: str) -> str:
    from urllib.parse import quote

    return quote(project_token.strip(), safe="-_.!~*'()")


def _build_ws_url(project_token: str) -> str:
    encoded = _encode_path_token(project_token)
    return f"{resolve_ws_base_url()}/{encoded}/create_log"


def _read_encrypted_flag(raw: Dict[str, Any]) -> bool:
    enc = raw.get("encrypted")
    if not isinstance(enc, bool):
        enc = raw.get("encryption")
    return enc if isinstance(enc, bool) else True


def _build_ws_url_no_auth(project_token: str) -> str:
    encoded = _encode_path_token(project_token)
    return f"{resolve_ws_base_url()}/{encoded}/create_browser_logs"


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


def _cancel_flush_timer_locked() -> None:
    global _flush_timer
    if _flush_timer is not None:
        _flush_timer.cancel()
        _flush_timer = None


def _flush_buffer_now(project_token: str, user_secret: str) -> None:
    global _send_buffer
    with _send_buffer_lock:
        if not _send_buffer:
            _cancel_flush_timer_locked()
            return
        batch = _send_buffer[:]
        _send_buffer = []
        _cancel_flush_timer_locked()
    _send_payload_async(project_token, user_secret, batch)


def _schedule_or_flush_buffer(project_token: str, user_secret: str) -> None:
    with _send_buffer_lock:
        if len(_send_buffer) >= BATCH_MAX_SIZE:
            should_flush = True
        else:
            should_flush = False
            _cancel_flush_timer_locked()
            timer = threading.Timer(
                BATCH_FLUSH_INTERVAL_S,
                _flush_buffer_now,
                args=(project_token, user_secret),
            )
            timer.daemon = True
            timer.start()
            global _flush_timer
            _flush_timer = timer
    if should_flush:
        _flush_buffer_now(project_token, user_secret)


def _enqueue_payload_for_send(project_token: str, user_secret: str, payload: Dict[str, Any]) -> None:
    with _send_buffer_lock:
        _send_buffer.append(payload)
    _schedule_or_flush_buffer(project_token, user_secret)


def close_aura_log_socket() -> None:
    """Close the cached WebSocket and drop cached ``proj_auth`` data for this process."""
    global _hydration_cache_token, _hydration_cache_raw
    project_token = _resolve_project_token_runtime()
    user_secret = _resolve_user_secret_runtime() or ""
    if project_token and (user_secret or not _encrypted):
        _flush_buffer_now(project_token, user_secret)
    else:
        with _send_buffer_lock:
            global _send_buffer
            _send_buffer = []
            _cancel_flush_timer_locked()
    _close_ws_connection()
    _hydration_cache_token = None
    _hydration_cache_raw = None


def _fetch_proj_auth_cached(project_token: str) -> Optional[Dict[str, Any]]:
    global _hydration_cache_token, _hydration_cache_raw
    with _hydrate_lock:
        if _hydration_cache_token == project_token and _hydration_cache_raw is not None:
            return _hydration_cache_raw
        raw = None
        for attempt in range(1, SDK_RETRY_ATTEMPTS + 1):
            try:
                raw = fetch_proj_auth_payload(project_token)
                break
            except ValueError:
                if attempt >= SDK_RETRY_ATTEMPTS:
                    return None
                print(
                    f"auralogger: proj_auth failed; retrying ({attempt + 1}/{SDK_RETRY_ATTEMPTS})...",
                    file=sys.stderr,
                )
                threading.Event().wait(SDK_RETRY_DELAY_S)
        if raw is None:
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


def _resolve_user_secret_runtime() -> Optional[str]:
    if _override_user_secret is not None:
        s = _override_user_secret.strip()
        if s:
            return s
    return get_resolved_user_secret()


def _merged_runtime_for_send(project_token: str) -> Optional[Dict[str, Any]]:
    from auralogger.utils.env_config import get_resolved_project_id

    pid = (get_resolved_project_id() or "").strip()
    sess = (get_resolved_session() or "").strip()
    styles = try_parse_resolved_styles()

    need_fetch = not pid or not sess or styles is None

    if need_fetch:
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
    url = _build_ws_url_no_auth(project_token) if not _encrypted else _build_ws_url(project_token)
    if _ws is not None and _bound_url == url and _ws.connected:
        return _ws
    _close_ws_connection()
    headers = [] if not _encrypted else [f"Authorization: Bearer {user_secret}"]
    conn = create_connection(
        url,
        timeout=CONNECT_TIMEOUT_S,
        header=headers,
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


def _send_payload_async(
    project_token: str, user_secret: str, payload_batch: list[Dict[str, Any]]
) -> None:
    try:
        body = json.dumps(payload_batch)
    except (TypeError, ValueError) as e:
        print(f"auralogger: failed to serialize log batch payload: {e}", file=sys.stderr)
        return

    for attempt in range(1, SDK_RETRY_ATTEMPTS + 1):
        try:
            ws = _ensure_ws(project_token, user_secret)
            ws.send(body)
            return
        except websocket.WebSocketTimeoutException as e:
            close_aura_log_socket()
            if attempt >= SDK_RETRY_ATTEMPTS:
                print(f"auralogger: websocket send failed (timeout): {e}", file=sys.stderr)
                return
            print(
                f"auralogger: websocket send timeout; retrying ({attempt + 1}/{SDK_RETRY_ATTEMPTS})...",
                file=sys.stderr,
            )
            threading.Event().wait(SDK_RETRY_DELAY_S)
        except Exception as e:
            close_aura_log_socket()
            if attempt >= SDK_RETRY_ATTEMPTS:
                print(f"auralogger: websocket send failed: {e}", file=sys.stderr)
                return
            print(
                f"auralogger: websocket send failed ({e}); retrying ({attempt + 1}/{SDK_RETRY_ATTEMPTS})...",
                file=sys.stderr,
            )
            threading.Event().wait(SDK_RETRY_DELAY_S)


def aura_log(
    type: str,
    message: str,
    location: Optional[str] = None,
    data: Any = None,
) -> None:
    """
    Print a styled log line locally and, when ``AURALOGGER_PROJECT_TOKEN`` and
    ``AURALOGGER_USER_SECRET`` are available, send the same payload over the logging WebSocket.
    """
    project_token = _resolve_project_token_runtime()
    user_secret = _resolve_user_secret_runtime()

    payload: Dict[str, Any] = {
        "type": _normalize_type(type),
        "message": "" if message is None else str(message),
        "session": _get_or_create_local_session(),
        "created_at": _iso_timestamp_utc(),
    }
    loc = _normalize_location(location)
    if loc is not None:
        payload["location"] = loc
    data_str = _maybe_data(data)
    if data_str is not None:
        payload["data"] = data_str

    styles = _styles_for_console(project_token, None)
    try:
        print_log(payload, styles)
    except Exception as e:
        print(f"auralogger: failed to print log: {e}", file=sys.stderr)

    if not project_token:
        return
    if _encrypted and not user_secret:
        return

    merged = _merged_runtime_for_send(project_token)
    if merged is None:
        return

    send_payload = payload.copy()
    send_payload["session"] = merged["session"]
    _enqueue_payload_for_send(project_token, user_secret or "", send_payload)


class auralogger:
    """Logger wrapper over ``aura_log`` runtime behavior (configure, sync, log, close socket)."""

    @staticmethod
    def _apply_runtime_config(
        project_token: str,
        user_secret: str,
        enc: bool = True,
    ) -> None:
        global _override_project_token, _override_user_secret, _encrypted
        global _hydration_cache_token, _hydration_cache_raw, _local_session_id
        _override_project_token = project_token
        _override_user_secret = user_secret
        _encrypted = enc
        _local_session_id = None
        with _hydrate_lock:
            _hydration_cache_token = None
            _hydration_cache_raw = None

    @staticmethod
    def configure(
        project_token: Optional[str] = None,
        user_secret: Optional[str] = None,
    ) -> None:
        resolved_project_token = (
            project_token.strip()
            if isinstance(project_token, str)
            else os.environ.get("AURALOGGER_PROJECT_TOKEN", "").strip()
        )
        resolved_user_secret = (
            user_secret.strip()
            if isinstance(user_secret, str)
            else os.environ.get("AURALOGGER_USER_SECRET", "").strip()
        )
        if not resolved_project_token:
            auralogger._apply_runtime_config(resolved_project_token, resolved_user_secret)
            return
        raw = fetch_proj_auth_payload(resolved_project_token)
        enc = _read_encrypted_flag(raw)
        auralogger._apply_runtime_config(resolved_project_token, resolved_user_secret, enc)
        if enc and not resolved_user_secret:
            return
        project_id_raw = raw.get("project_id")
        session_raw = raw.get("session")
        project_id = project_id_raw.strip() if isinstance(project_id_raw, str) else ""
        session = session_raw.strip() if isinstance(session_raw, str) else ""
        if not project_id or not session:
            raise ValueError(
                "auralogger.configure: proj_auth response missing project id or session."
            )
        with _hydrate_lock:
            global _hydration_cache_token, _hydration_cache_raw
            _hydration_cache_token = resolved_project_token
            _hydration_cache_raw = raw

    @staticmethod
    def sync_from_secret(project_token: str, user_secret: Optional[str] = None) -> None:
        trimmed = project_token.strip()
        if not trimmed:
            raise ValueError("auralogger.sync_from_secret: project token cannot be empty.")
        raw = fetch_proj_auth_payload(trimmed)
        enc = _read_encrypted_flag(raw)
        resolved_user_secret = (
            user_secret.strip()
            if isinstance(user_secret, str)
            else os.environ.get("AURALOGGER_USER_SECRET", "").strip()
        )
        if enc and not resolved_user_secret:
            raise RuntimeError("Missing AURALOGGER_USER_SECRET")
        auralogger._apply_runtime_config(trimmed, resolved_user_secret, enc)
        project_id_raw = raw.get("project_id")
        session_raw = raw.get("session")
        project_id = project_id_raw.strip() if isinstance(project_id_raw, str) else ""
        session = session_raw.strip() if isinstance(session_raw, str) else ""
        if not project_id or not session:
            raise ValueError(
                "auralogger.sync_from_secret: proj_auth response missing project id or session."
            )
        with _hydrate_lock:
            global _hydration_cache_token, _hydration_cache_raw
            _hydration_cache_token = trimmed
            _hydration_cache_raw = raw

    @staticmethod
    def log(type: str, message: str, location: Optional[str] = None, data: Any = None) -> None:
        aura_log(type, message, location, data)

    @staticmethod
    def close_socket(timeout_ms: int = 1000) -> None:
        _ = timeout_ms
        close_aura_log_socket()
