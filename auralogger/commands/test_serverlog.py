"""`auralogger test-serverlog` - send a short server logger burst."""

from __future__ import annotations

import time

from auralogger.aura_log import aura_log, close_aura_log_socket


def run_test_serverlog() -> None:
    print("Sending 5 server test logs (same path as production server logger)...")
    for i in range(1, 6):
        aura_log(
            "info",
            f"test-serverlog log {i}/5",
            "cli/test-serverlog",
            {"i": i, "kind": "test-serverlog"},
        )
        time.sleep(0.15)

    time.sleep(0.8)
    close_aura_log_socket()
    print("Server burst complete. Try: auralogger get-logs -maxcount 20")
