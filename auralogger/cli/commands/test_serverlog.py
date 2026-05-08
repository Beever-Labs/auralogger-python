"""`auralogger test-serverlog` — parity with node/src/cli/services/test-logger.ts (server)."""

from __future__ import annotations

import time

from auralogger.cli.aside_pools import pick_aside, pick_test_serverlog_success_aside, TEST_SERVERLOG_START_BANNER_ASIDES
from auralogger.cli.cli_auth import resolve_project_token_for_init, resolve_user_secret_for_init
from auralogger.cli.cli_load_env import ensure_utf8_stdio
from auralogger.cli.cli_style import bold_hex, bold_white, dim, green, hex_color, white
from auralogger.cli.cli_tone import maybe_print_generic_spice, print_aside
from auralogger.server.aura_log import Auralogger, aura_log, close_aura_log_socket


def run_test_serverlog() -> None:
    ensure_utf8_stdio()
    print(
        bold_hex("#79c0ff", "🧪 ")
        + white("Firing the ")
        + bold_white("server")
        + white(" logger — 5 peppy test logs incoming."),
    )
    a = pick_aside(TEST_SERVERLOG_START_BANNER_ASIDES)
    print_aside(a["emoji"], a["line"])
    print()

    project_token = resolve_project_token_for_init()
    user_secret = resolve_user_secret_for_init()
    Auralogger.configure(project_token, user_secret)

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
    print()
    print(
        green("✅ ")
        + white("Server burst sent. Peek with ")
        + hex_color("#79c0ff", "auralogger get-logs -maxcount 20")
        + white(" if the dashboard’s shy."),
    )
    a = pick_test_serverlog_success_aside()
    print_aside(a["emoji"], a["line"])
    maybe_print_generic_spice()
