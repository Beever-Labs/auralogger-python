"""`auralogger test-clientlog` - send browser-ingest log burst over one socket."""

from __future__ import annotations

import time
from auralogger.client.client_log import AuraClient, close_client_log_socket
from auralogger.cli.cli_auth import resolve_project_token_for_init


def run_test_clientlog() -> None:
    project_token = resolve_project_token_for_init()
    AuraClient.sync_from_secret(project_token)
    print("Sending 5 client test logs via browser ingest route...")

    try:
        for i in range(1, 6):
            AuraClient.log(
                "info",
                f"test-clientlog log {i}/5",
                "cli/test-clientlog",
                {"i": i, "kind": "test-clientlog"},
            )
            time.sleep(0.15)
    finally:
        close_client_log_socket()

    print("Client burst complete. Try: auralogger get-logs -maxcount 20")
