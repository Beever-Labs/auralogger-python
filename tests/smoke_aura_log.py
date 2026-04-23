#!/usr/bin/env python3
"""
Manual smoke test for ``auralogger.server.aura_log``: styled console output and optional WebSocket ingest.

Run from the ``python/`` directory after install::

    pip install -e .
    python tests/smoke_aura_log.py

With ``AURALOGGER_PROJECT_TOKEN`` and ``AURALOGGER_USER_SECRET`` set (and the API reachable so
``proj_auth`` can supply id/session/styles if they are not in env), logs are also sent over the
WebSocket. Without token/secret, you still see colored lines locally and a one-time note on stderr
about console-only mode.
"""

from __future__ import annotations

import time

from auralogger import aura_log, close_aura_log_socket


def main() -> None:
    samples = [
        {
            "type": "info",
            "message": "smoke test suite started",
            "location": "tests/smoke_aura_log:main",
            "data": {"phase": "start", "source": "python", "env": "test"},
        },
        {
            "type": "debug",
            "message": "request payload parsed successfully",
            "location": "tests/smoke_aura_log:parse",
            "data": {"userId": "usr_42", "action": "login", "duration_ms": 12},
        },
        {
            "type": "warn",
            "message": "rate limit threshold approaching",
            "location": "tests/smoke_aura_log:rate_limiter",
            "data": {"current_rate": 480, "limit": 500, "unit": "req/min"},
        },
        {
            "type": "error",
            "message": "failed to connect to upstream service",
            "location": "tests/smoke_aura_log:upstream",
            "data": {"service": "auth-api", "status_code": 503, "retries": 3},
        },
        {
            "type": "warn",
            "message": "deprecated config key detected",
            "location": "tests/smoke_aura_log:config",
            "data": {"key": "LOG_LEVEL_OVERRIDE", "replacement": "AURALOGGER_LEVEL"},
        },
        {
            "type": "debug",
            "message": "cache hit on session lookup",
            "location": "tests/smoke_aura_log:cache",
            "data": {"session": "sess_99", "hit": True, "ttl_remaining_s": 240},
        },
        {
            "type": "info",
            "message": "smoke test suite finished",
            "location": "tests/smoke_aura_log:main",
            "data": {"phase": "end", "logs_sent": 7},
        },
    ]

    for row in samples:
        aura_log(
            row["type"],
            row["message"],
            row.get("location"),
            row.get("data"),
        )
        time.sleep(0.15)

    time.sleep(0.5)
    close_aura_log_socket()
    print("smoke_aura_log: done.")


if __name__ == "__main__":
    main()
