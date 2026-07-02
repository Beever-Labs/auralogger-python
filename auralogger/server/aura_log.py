"""Runtime log helper: styled console line + optional WebSocket send.

Parity with node ``AuraClient`` / ``AuraServer``:
    1. print_log immediately
    2. if no project_token (from configure) → return
    3. proj_auth hydrates project_id + session + styles (+ encrypted flag)
    4. open ws if not yet (Bearer for encrypted, no auth for non-encrypted)
    5. push log into batch; start flush timer if batch was empty, or flush if batch is full
"""

from __future__ import annotations

import atexit
import json
import logging
import os
import sys
import threading
import time
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
)

UNKNOWN_TYPE = "unknown"
LOCAL_FALLBACK_SESSION = "auralogger-local-session"
CONNECT_TIMEOUT_S = 5
BATCH_FLUSH_INTERVAL_S = 0.03
BATCH_MAX_SIZE = 30
PROJ_AUTH_RETRY_ATTEMPTS = 3
PROJ_AUTH_RETRY_DELAY_S = 0.5


def _suppress_websocket_client_noise() -> None:
    logging.getLogger("websocket").setLevel(logging.WARNING)


_suppress_websocket_client_noise()


def _is_debug_enabled() -> bool:
    v = (os.environ.get("AURALOGGER_DEBUG") or "").strip().lower()
    return bool(v) and v not in ("0", "false", "no", "off")


def _trace(event: str, details: Optional[Dict[str, Any]] = None) -> None:
    if not _is_debug_enabled():
        return
    if details:
        print(f"auralogger: [AuraLog] {event} {details}", file=sys.stderr)
    else:
        print(f"auralogger: [AuraLog] {event}", file=sys.stderr)


# ---- state ----------------------------------------------------------------

_state_lock = threading.Lock()

_project_token: Optional[str] = None
_user_secret: Optional[str] = None
# True = encrypted flow (Bearer header, /create_log)
# False = non-encrypted flow (no auth, /create_browser_logs)
_encrypted: bool = True

_session: Optional[str] = None
# Explicit session supplied at configure time (param or env). When set it wins
# over the proj_auth session; when None we fall back to the proj_auth session.
_override_session: Optional[str] = None
_styles: Optional[Any] = None

_proj_auth_event = threading.Event()
_proj_auth_started: bool = False
_proj_auth_ok: bool = False

_ws: Optional[Any] = None
_bound_url: Optional[str] = None

_batch: list[Dict[str, Any]] = []
_flush_timer: Optional[threading.Timer] = None
_flush_in_flight: bool = False

_local_session_id: Optional[str] = None
_auto_init_attempted: bool = False
_warned_missing_user_secret: bool = False


# ---- small helpers --------------------------------------------------------


def _build_ws_url_encrypted(project_token: str) -> str:
    return f"{resolve_ws_base_url()}/{project_token.strip()}/create_log"


def _build_ws_url_open(project_token: str) -> str:
    return f"{resolve_ws_base_url()}/{project_token.strip()}/create_browser_logs"


def _read_encrypted_flag(raw: Dict[str, Any]) -> bool:
    enc = raw.get("encrypted")
    if enc is None:
        enc = raw.get("encryption")
    if enc is True or enc == "true":
        return True
    if enc is False or enc == "false":
        return False
    return True


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
    if isinstance(data, dict):
        try:
            return json.dumps(data)
        except (TypeError, ValueError):
            return None
    return None


def _iso_timestamp_utc() -> str:
    now = datetime.now(timezone.utc)
    base = now.strftime("%Y-%m-%dT%H:%M:%S")
    return f"{base}.{now.microsecond:06d}Z"


def _get_or_create_local_session() -> str:
    global _local_session_id
    if _local_session_id is None:
        _local_session_id = str(uuid.uuid4())
    return _local_session_id


# ---- proj_auth ------------------------------------------------------------


def _apply_proj_auth_payload(raw: Dict[str, Any]) -> bool:
    """Pull session + styles from a proj_auth response. Returns True if usable."""
    global _session, _styles
    pid_raw = raw.get("project_id")
    sess_raw = raw.get("session")
    pid = pid_raw.strip() if isinstance(pid_raw, str) else ""
    sess = sess_raw.strip() if isinstance(sess_raw, str) else ""
    if not pid or not sess:
        return False
    rows = raw.get("styles")
    rows = rows if isinstance(rows, list) else []
    _session = sess
    _styles = build_style_entries_from_api(rows)
    return True


def _proj_auth_worker(token: str) -> None:
    global _proj_auth_ok, _proj_auth_started
    _trace("proj_auth.start", {"hasToken": bool(token)})
    last_err: Optional[BaseException] = None
    raw: Optional[Dict[str, Any]] = None
    for attempt in range(1, PROJ_AUTH_RETRY_ATTEMPTS + 1):
        try:
            raw = fetch_proj_auth_payload(token)
            last_err = None
            break
        except ValueError as e:
            last_err = e
            _trace(
                "proj_auth.attempt_failed",
                {"attempt": attempt, "max": PROJ_AUTH_RETRY_ATTEMPTS, "message": str(e)},
            )
            if attempt < PROJ_AUTH_RETRY_ATTEMPTS:
                time.sleep(PROJ_AUTH_RETRY_DELAY_S)
    if raw is None:
        print(
            f"auralogger: proj_auth failed after {PROJ_AUTH_RETRY_ATTEMPTS} attempts; local-only logging ({last_err})",
            file=sys.stderr,
        )
        with _state_lock:
            _proj_auth_ok = False
            _proj_auth_started = False
            _proj_auth_event.clear()
        return
    if not _apply_proj_auth_payload(raw):
        print(
            "auralogger: proj_auth response missing project id or session; local-only logging.",
            file=sys.stderr,
        )
        with _state_lock:
            _proj_auth_ok = False
            _proj_auth_started = False
            _proj_auth_event.clear()
        return
    with _state_lock:
        _proj_auth_ok = True
        _proj_auth_event.set()


def _start_proj_auth_once() -> None:
    global _proj_auth_started
    with _state_lock:
        if _proj_auth_started or not _project_token:
            return
        _proj_auth_started = True
        token = _project_token
    t = threading.Thread(target=_proj_auth_worker, args=(token,), daemon=True)
    t.start()


# ---- websocket ------------------------------------------------------------


def _close_ws_connection() -> None:
    global _ws, _bound_url
    if _ws is not None:
        try:
            _ws.close()
        except Exception:
            pass
    _ws = None
    _bound_url = None


def _open_ws_if_needed() -> Optional[Any]:
    global _ws, _bound_url, _warned_missing_user_secret
    if not _project_token:
        return None
    if _encrypted and not _user_secret:
        if not _warned_missing_user_secret:
            _warned_missing_user_secret = True
            print(
                "auralogger: missing user secret. Call Auralogger.configure(project_token, user_secret) before logging.",
                file=sys.stderr,
            )
        return None
    url = _build_ws_url_encrypted(_project_token) if _encrypted else _build_ws_url_open(_project_token)
    if _ws is not None and _bound_url == url and getattr(_ws, "connected", False):
        return _ws
    _close_ws_connection()
    headers = [f"Authorization: Bearer {_user_secret}"] if _encrypted else []
    try:
        conn = create_connection(url, timeout=CONNECT_TIMEOUT_S, header=headers)
    except Exception as e:
        print(f"auralogger: could not open websocket ({e})", file=sys.stderr)
        return None
    _ws = conn
    _bound_url = url
    return conn


def _send_batch(payloads: list[Dict[str, Any]]) -> bool:
    try:
        body = json.dumps(payloads)
    except (TypeError, ValueError) as e:
        print(f"auralogger: failed to serialize log batch: {e}", file=sys.stderr)
        return False
    ws = _open_ws_if_needed()
    if ws is None:
        return False
    try:
        ws.send(body)
        return True
    except websocket.WebSocketTimeoutException as e:
        first_err: BaseException = e
    except Exception as e:
        first_err = e

    # First attempt failed — rebuild socket and retry once (2/2), and do not permanently disable logging.
    print(
        f"auralogger: websocket send failed ({first_err}); retrying with fresh socket (2/2)...",
        file=sys.stderr,
    )
    _trace("send_batch.retry.start", {"message": str(first_err)})
    _close_ws_connection()
    retry_ws = _open_ws_if_needed()
    if retry_ws is None:
        print("auralogger: websocket unavailable after retry; dropping batch.", file=sys.stderr)
        _trace("send_batch.retry.no_socket")
        return False
    try:
        retry_ws.send(body)
        _trace("send_batch.retry.sent")
        return True
    except Exception as e:
        print(f"auralogger: websocket send failed after retry: {e}", file=sys.stderr)
        _trace("send_batch.retry.failed", {"message": str(e)})
        _close_ws_connection()
        return False


# ---- batch / flush --------------------------------------------------------


def _cancel_flush_timer_locked() -> None:
    global _flush_timer
    if _flush_timer is not None:
        _flush_timer.cancel()
        _flush_timer = None


def _schedule_flush_locked() -> None:
    global _flush_timer
    _cancel_flush_timer_locked()
    _flush_timer = threading.Timer(BATCH_FLUSH_INTERVAL_S, _flush_now)
    _flush_timer.daemon = False
    _flush_timer.start()


def _schedule_flush() -> None:
    with _state_lock:
        _schedule_flush_locked()


def _flush_now() -> None:
    global _flush_in_flight
    with _state_lock:
        if _flush_in_flight:
            return
        _flush_in_flight = True
        _cancel_flush_timer_locked()
    try:
        if not _proj_auth_started:
            return
        _proj_auth_event.wait()
        # Prefer an explicit session (configure param / env); fall back to proj_auth.
        effective_session = _override_session or _session
        if not _proj_auth_ok or not effective_session:
            with _state_lock:
                _batch.clear()
            return
        live_session = effective_session
        while True:
            with _state_lock:
                if not _batch:
                    return
                slice_ = _batch[:BATCH_MAX_SIZE]
            for p in slice_:
                p["session"] = live_session
            sent = _send_batch(slice_)
            if not sent:
                # Best-effort semantics: drop the slice we attempted, keep any later logs so the next
                # flush can retry with a fresh socket.
                with _state_lock:
                    del _batch[: len(slice_)]
                    if _batch:
                        _schedule_flush_locked()
                return
            with _state_lock:
                del _batch[: len(slice_)]
    finally:
        with _state_lock:
            _flush_in_flight = False


def _enqueue(payload: Dict[str, Any]) -> None:
    _start_proj_auth_once()
    should_flush = False
    should_schedule = False
    with _state_lock:
        was_empty = len(_batch) == 0
        _batch.append(payload)
        if len(_batch) >= BATCH_MAX_SIZE:
            should_flush = True
        elif was_empty:
            should_schedule = True
    if should_flush:
        threading.Thread(target=_flush_now, daemon=False).start()
    elif should_schedule:
        _schedule_flush()


# ---- public entry points --------------------------------------------------


def _reset_proj_auth_state_locked() -> None:
    global _session, _styles, _proj_auth_started, _proj_auth_ok, _local_session_id
    global _warned_missing_user_secret
    _session = None
    _styles = None
    _proj_auth_started = False
    _proj_auth_ok = False
    _local_session_id = None
    _warned_missing_user_secret = False
    _proj_auth_event.clear()


def _reset_batch_state_locked() -> None:
    global _batch, _flush_in_flight
    _batch = []
    _cancel_flush_timer_locked()
    _flush_in_flight = False


def close_aura_log_socket() -> None:
    """Flush any buffered logs, close the cached WebSocket, drop cached state."""
    if _proj_auth_started and _project_token:
        _proj_auth_event.wait(timeout=10)
        _flush_now()
    with _state_lock:
        _reset_batch_state_locked()
    _close_ws_connection()


def _auto_init_from_env_once() -> None:
    """Zero-config convenience: on first log without configure(), pull creds from env."""
    global _auto_init_attempted
    if _auto_init_attempted or _project_token:
        return
    _auto_init_attempted = True
    token = get_resolved_project_token() or ""
    if not token:
        return
    secret = get_resolved_user_secret() or ""
    Auralogger.configure(token, secret)


def aura_log(
    type: str,
    message: str,
    location: Optional[str] = None,
    data: Any = None,
) -> None:
    """Print a styled log line locally and, when configured, queue it for the WebSocket."""
    _auto_init_from_env_once()
    payload: Dict[str, Any] = {
        "type": _normalize_type(type),
        "message": "" if message is None else str(message),
        "session": _override_session or _session or _get_or_create_local_session(),
        "created_at": _iso_timestamp_utc(),
    }
    loc = _normalize_location(location)
    if loc is not None:
        payload["location"] = loc
    data_str = _maybe_data(data)
    if data_str is not None:
        payload["data"] = data_str

    try:
        print_log(payload, _styles if _styles is not None else [])
    except Exception as e:
        print(f"auralogger: failed to print log: {e}", file=sys.stderr)

    if not _project_token:
        return

    _enqueue(payload)


class Auralogger:
    """Logger wrapper: configure, sync, log, close socket.

    Encrypted flow (default): ``configure(project_token, user_secret, session=...)``
    Non-encrypted flow:        ``configure(project_token, session=..., enc=False)``

    Session precedence: explicit ``session`` arg → ``AURALOGGER_PROJECT_SESSION`` env → ``proj_auth``.
    """

    @staticmethod
    def _apply_runtime_config(
        project_token: str,
        user_secret: str,
        session: str = "",
        enc: bool = True,
    ) -> None:
        global _project_token, _user_secret, _encrypted, _override_session
        with _state_lock:
            _project_token = project_token or None
            _user_secret = user_secret or None
            _encrypted = enc
            _reset_proj_auth_state_locked()
            _reset_batch_state_locked()
            _override_session = (
                session.strip() if isinstance(session, str) and session.strip() else None
            )

    @staticmethod
    def configure(
        project_token: Optional[str] = None,
        user_secret: Optional[str] = None,
        session: Optional[str] = None,
        enc: bool = True,
    ) -> None:
        # configure-time env fallback is a convenience for zero-arg callers.
        # The log path itself never reads env — once configured, that's the single source.
        token = (
            project_token.strip()
            if isinstance(project_token, str)
            else (get_resolved_project_token() or "")
        )
        secret = (
            user_secret.strip()
            if isinstance(user_secret, str)
            else (get_resolved_user_secret() or "")
        )
        # Session precedence: explicit arg → env → proj_auth (resolved later).
        sess = (
            session.strip()
            if isinstance(session, str)
            else (get_resolved_session() or "")
        )
        if not token:
            Auralogger._apply_runtime_config("", "", sess, enc)
            print(
                "auralogger: configure called with empty project token; continuing in local-only mode.",
                file=sys.stderr,
            )
            return
        Auralogger._apply_runtime_config(token, secret, sess, enc)
        # Run proj_auth synchronously so session/styles are ready for the first log.
        global _proj_auth_started, _proj_auth_ok
        try:
            raw = fetch_proj_auth_payload(token)
        except ValueError as e:
            print(
                f"auralogger: proj_auth failed during configure ({e}); local-only logging.",
                file=sys.stderr,
            )
            with _state_lock:
                # Do not permanently disable the logger. Mirror the runtime worker:
                # allow future log() calls to retry proj_auth instead of being stuck.
                _proj_auth_started = False
                _proj_auth_ok = False
                _proj_auth_event.clear()
            return
        with _state_lock:
            ok = _apply_proj_auth_payload(raw)
            if ok:
                _proj_auth_started = True
                _proj_auth_ok = True
                _proj_auth_event.set()
            else:
                # Bad/partial response: keep local-only mode, but allow future retries.
                _proj_auth_started = False
                _proj_auth_ok = False
                _proj_auth_event.clear()
        if not ok:
            print(
                "auralogger: proj_auth response missing project id or session; local-only logging.",
                file=sys.stderr,
            )

    @staticmethod
    def sync_from_secret(
        project_token: str,
        user_secret: Optional[str] = None,
        session: Optional[str] = None,
    ) -> None:
        """Eagerly run proj_auth. Mirrors node ``AuraServer.syncFromSecret``: when a user
        secret is supplied, route over the encrypted ``/create_log`` ingest path; without
        a secret, use the open ``/create_browser_logs`` path. The server's ``encrypted``
        flag is informational only — the WS route is driven by secret presence.

        ``session`` precedence: explicit arg → env → proj_auth response."""
        trimmed = project_token.strip()
        if not trimmed:
            print(
                "auralogger: sync_from_secret called with empty project token; local-only logging.",
                file=sys.stderr,
            )
            return
        try:
            raw = fetch_proj_auth_payload(trimmed)
        except ValueError as e:
            print(
                f"auralogger: proj_auth failed during sync_from_secret ({e}); local-only logging.",
                file=sys.stderr,
            )
            return
        secret = user_secret.strip() if isinstance(user_secret, str) else ""
        sess = (
            session.strip()
            if isinstance(session, str)
            else (get_resolved_session() or "")
        )
        enc = bool(secret)
        Auralogger._apply_runtime_config(trimmed, secret, sess, enc)
        # Install the already-fetched payload so we don't re-call proj_auth.
        global _proj_auth_started, _proj_auth_ok
        with _state_lock:
            ok = _apply_proj_auth_payload(raw)
            _proj_auth_started = True
            _proj_auth_ok = ok
            _proj_auth_event.set()
        if not ok:
            print(
                "auralogger: proj_auth response missing project id or session; local-only logging.",
                file=sys.stderr,
            )

    @staticmethod
    def log(
        type: str,
        message: str,
        location: Optional[str] = None,
        data: Any = None,
    ) -> None:
        aura_log(type, message, location, data)

    @staticmethod
    def close_socket(timeout_ms: int = 1000) -> None:
        _ = timeout_ms
        close_aura_log_socket()


atexit.register(close_aura_log_socket)
