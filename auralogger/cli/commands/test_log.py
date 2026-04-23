"""`auralogger test-log` — sends 5 test logs via the non-encrypted browser route."""

from __future__ import annotations

import time

from auralogger.cli.aside_pools import (
    CLIENT_CHECK_START_PETER_ASIDES,
    CLIENT_CHECK_SUCCESS_ASIDES,
    pick_aside,
)
from auralogger.cli.cli_auth import resolve_project_token_for_init
from auralogger.cli.cli_load_env import ensure_utf8_stdio
from auralogger.cli.cli_style import bold_hex, bold_white, dim, green, hex_color, white
from auralogger.cli.cli_tone import maybe_print_generic_spice, print_aside
from auralogger.server.aura_log import auralogger, aura_log, close_aura_log_socket


def run_test_log() -> None:
    ensure_utf8_stdio()
    print(
        bold_hex("#79c0ff", "🧪 ")
        + white("Firing the ")
        + bold_white("index")
        + white(" auralogger client — 5 test logs, no-auth browser route."),
    )
    print(dim("   (Forces the non-encrypted create_browser_logs socket — no user secret needed.)"))
    a = pick_aside(CLIENT_CHECK_START_PETER_ASIDES)
    print_aside(a["emoji"], a["line"])
    print()

    project_token = resolve_project_token_for_init()
    auralogger._apply_runtime_config(project_token, "", enc=False)

    test_logs = [
        ("info",  "test-log suite started",                 "cli/test-log", {"source": "auralogger-cli", "env": "test"}),
        ("warn",  "localStorage quota nearing limit",       "cli/test-log", {"usedKB": 4800, "limitKB": 5120}),
        ("error", "unhandled promise rejection in fetch",   "cli/test-log", {"url": "/api/data", "reason": "NetworkError: Failed to fetch"}),
        ("debug", "component render cycle complete",        "cli/test-log", {"component": "Dashboard", "renderMs": 34}),
        ("info",  "test-log suite finished",                "cli/test-log", {"logsEmitted": 5}),
    ]
    for log_type, message, location, data in test_logs:
        aura_log(log_type, message, location, data)
        time.sleep(0.15)

    time.sleep(0.8)
    close_aura_log_socket()
    print()
    print(
        green("✅ ")
        + white("Index client burst sent. Spy with ")
        + hex_color("#79c0ff", "auralogger get-logs -maxcount 20")
        + white(" when curious."),
    )
    a = pick_aside(CLIENT_CHECK_SUCCESS_ASIDES)
    print_aside(a["emoji"], a["line"])
    maybe_print_generic_spice()
