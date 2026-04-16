"""`auralogger test-clientlog` — parity with node/src/cli/services/test-logger.ts (client)."""

from __future__ import annotations

import time

from auralogger.cli.aside_pools import TEST_CLIENTLOG_START_ASIDES, TEST_CLIENTLOG_SUCCESS_ASIDES, pick_aside
from auralogger.cli.cli_auth import resolve_project_token_for_init
from auralogger.cli.cli_load_env import ensure_utf8_stdio
from auralogger.cli.cli_style import bold_hex, bold_white, dim, green, hex_color, white
from auralogger.cli.cli_tone import maybe_print_generic_spice, print_aside
from auralogger.client.client_log import AuraClient, close_client_log_socket


def run_test_clientlog() -> None:
    ensure_utf8_stdio()
    print(
        bold_hex("#79c0ff", "🧪 ")
        + white("Firing the ")
        + bold_white("client")
        + white(" logger — 5 test logs, browser flavor."),
    )
    print(dim("   (Patches in `ws` so Node can fake a browser here.)"))
    a = pick_aside(TEST_CLIENTLOG_START_ASIDES)
    print_aside(a["emoji"], a["line"])
    print()

    project_token = resolve_project_token_for_init()
    AuraClient.sync_from_secret(project_token)

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

    print()
    print(
        green("✅ ")
        + white("Client burst sent. Spy with ")
        + hex_color("#79c0ff", "auralogger get-logs -maxcount 20")
        + white(" when curious."),
    )
    a = pick_aside(TEST_CLIENTLOG_SUCCESS_ASIDES)
    print_aside(a["emoji"], a["line"])
    maybe_print_generic_spice()
