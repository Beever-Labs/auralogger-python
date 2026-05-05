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

import asyncio
import os
import time

from dotenv import load_dotenv

TYPES = ("info", "warn", "error", "debug")

_ENV_EXAMPLE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env.example"))
load_dotenv(_ENV_EXAMPLE, override=False)

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


def run_load_test(count: int = 500) -> None:
    """Burst: emit ``count`` logs back-to-back to verify the SDK survives a flood."""
    started = time.monotonic()
    aura_log("info", "load test started", "tests/smoke_aura_log:load", {"count": count})

    for i in range(count):
        aura_log(
            TYPES[i % len(TYPES)],
            f"bulk log {i + 1}/{count}",
            "tests/smoke_aura_log:load",
            {"i": i, "batch": i // 50, "payload": {"a": i, "b": i * 2, "tag": f"t{i % 7}"}},
        )

    elapsed_ms = int((time.monotonic() - started) * 1000)
    aura_log(
        "info",
        "load test finished",
        "tests/smoke_aura_log:load",
        {"count": count, "elapsed_ms": elapsed_ms},
    )
    time.sleep(1.5)
    close_aura_log_socket()
    print(f"smoke_aura_log: load test done ({count} logs in {elapsed_ms} ms).")


async def _fake_io(i: int) -> dict:
    await asyncio.sleep(0.02)
    return {"i": i, "ok": True}


async def _async_caller() -> None:
    """aura_log invoked from inside an async coroutine with awaits before/after."""
    aura_log("info", "async test started", "tests/smoke_aura_log:async", {"phase": "start"})

    for i in range(10):
        result = await _fake_io(i)
        aura_log(
            "debug",
            "async io resolved",
            "tests/smoke_aura_log:async",
            {"result": result, "i": i},
        )

    aura_log("info", "async test finished", "tests/smoke_aura_log:async", {"phase": "end"})


async def _concurrent_caller(parallel: int, per_task: int) -> None:
    """Many independent coroutines emitting logs in parallel."""
    aura_log(
        "info",
        "concurrent async test started",
        "tests/smoke_aura_log:concurrent",
        {"parallel": parallel, "per_task": per_task},
    )

    async def worker(task_id: int) -> None:
        for i in range(per_task):
            await asyncio.sleep(0.005 + (task_id % 5) * 0.001)
            aura_log(
                TYPES[(task_id + i) % len(TYPES)],
                f"task {task_id} log {i}",
                "tests/smoke_aura_log:concurrent",
                {"task_id": task_id, "i": i},
            )

    await asyncio.gather(*(worker(t) for t in range(parallel)))

    aura_log(
        "info",
        "concurrent async test finished",
        "tests/smoke_aura_log:concurrent",
        {"total_logs": parallel * per_task},
    )


def run_async_test() -> None:
    asyncio.run(_async_caller())
    time.sleep(0.8)
    close_aura_log_socket()
    print("smoke_aura_log: async test done.")


def run_concurrent_async_test(parallel: int = 25, per_task: int = 20) -> None:
    asyncio.run(_concurrent_caller(parallel, per_task))
    time.sleep(1.2)
    close_aura_log_socket()
    print(f"smoke_aura_log: concurrent async test done ({parallel * per_task} logs).")


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    if mode == "smoke":
        main()
    elif mode == "load":
        run_load_test(int(sys.argv[2]) if len(sys.argv) > 2 else 500)
    elif mode == "async":
        run_async_test()
    elif mode == "concurrent":
        parallel = int(sys.argv[2]) if len(sys.argv) > 2 else 25
        per_task = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        run_concurrent_async_test(parallel, per_task)
    elif mode == "all":
        main()
        run_load_test()
        run_async_test()
        run_concurrent_async_test()
    else:
        print(f"unknown mode: {mode!r} (use: smoke | load | async | concurrent | all)")
        sys.exit(2)
