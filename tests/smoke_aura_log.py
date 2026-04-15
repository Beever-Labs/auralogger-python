#!/usr/bin/env python3
"""
Manual smoke test for ``auralogger.aura_log``: styled console output and optional WebSocket ingest.

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
            "message": "Python smoke test started",
            "location": "tests/smoke_aura_log",
            "data": {"phase": "start", "source": "python"},
        },
        {
            "type": "debug",
            "message": "Checking styled console output",
            "location": "tests/smoke_aura_log",
            "data": {"step": 2},
        },
        {
            "type": "warn",
            "message": "Sample warning from Python smoke script",
            "location": "tests/smoke_aura_log",
            "data": {"retryable": True},
        },
        {
            "type": "error",
            "message": "Sample error log (not a real failure)",
            "location": "tests/smoke_aura_log",
            "data": {"code": "E_SMOKE"},
        },
        {
            "type": "info",
            "message": "Python smoke test finished",
            "location": "tests/smoke_aura_log",
            "data": {"phase": "end"},
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
