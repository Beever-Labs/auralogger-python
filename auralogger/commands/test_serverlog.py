"""`auralogger test-serverlog` - send a short server logger burst."""

from __future__ import annotations

import time

from auralogger.aura_log import AuraServer, aura_log, close_aura_log_socket
from auralogger.cli_auth import resolve_project_token_for_init, resolve_user_secret_for_init


def run_test_serverlog() -> None:
    project_token = resolve_project_token_for_init()
    user_secret = resolve_user_secret_for_init()
    AuraServer.sync_from_secret(project_token, user_secret)

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
