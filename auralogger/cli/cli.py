"""CLI entrypoint for `auralogger` — parity with node/src/cli/bin/auralogger.ts."""

import random
import sys
from typing import List, TextIO

from auralogger.cli.aside_pools import (
    BIN_UNKNOWN_COMMAND_TEMPLATES,
    BIN_USAGE_ASIDES,
    BIN_USAGE_LEGENDARY_ASIDES,
    BIN_USAGE_RARE_MULTI_ASIDES,
    CLI_VETERAN_USAGE_ASIDES,
    DEFAULT_SILENCE_ASIDE_CHANCE,
    ENV_SETUP_RECOVERY_ASIDES,
    WOLVERINE_NUDGE_ASIDES,
    classify_error_for_aside,
    format_aside_template,
    pick_adaptive_fatal_aside,
    pick_aside,
    pick_tiered_aside,
)
from auralogger.cli.cli_load_env import ensure_utf8_stdio, load_cli_env_files
from auralogger.cli.cli_personality_state import (
    get_consecutive_failures,
    get_total_successful_commands,
    note_command_dispatch,
    record_cli_failure,
    record_cli_success,
)
from auralogger.cli.cli_style import bold, bold_hex, dim, hex_color, red, red_bold, white
from auralogger.cli.cli_tone import maybe_print_generic_spice, print_aside, print_aside_maybe
from auralogger.cli.commands.get_logs_cmd import run_get_logs_command
from auralogger.cli.commands.init import run_init
from auralogger.cli.commands.server_check import run_server_check
from auralogger.cli.commands.test_serverlog import run_test_serverlog

KNOWN_COMMANDS = {
    "init",
    "get-logs",
    "server-check",
    "test-serverlog",
}


def print_usage(stream: TextIO = sys.stdout) -> None:
    print("", file=stream)
    print(
        bold_hex("#ffa657", "✨ Auralogger CLI") + dim(" — pick a command:"),
        file=stream,
    )
    print(
        hex_color("#7ee787", "  init") + dim("           wire up secrets + copy-paste server config"),
        file=stream,
    )
    print(
        hex_color("#7ee787", "  server-check") + dim("    make sure the server logger can talk"),
        file=stream,
    )
    print(
        hex_color("#7ee787", "  test-serverlog") + dim("  five fake server logs, just for kicks"),
        file=stream,
    )
    print(
        hex_color("#7ee787", "  get-logs") + dim("       hunt past logs (filters optional)"),
        file=stream,
    )
    print("", file=stream)
    print(
        dim("Docs live on npm: auralogger-cli — filter cheat sheet is there."),
        file=stream,
    )
    veteran = get_total_successful_commands() >= 4 and random.random() < 0.28
    if veteran:
        a = pick_aside(CLI_VETERAN_USAGE_ASIDES)
    else:
        a = pick_tiered_aside(
            {
                "common": BIN_USAGE_ASIDES,
                "rare": BIN_USAGE_RARE_MULTI_ASIDES,
                "legendary": BIN_USAGE_LEGENDARY_ASIDES,
            }
        )
    print_aside_maybe(a["emoji"], a["line"], DEFAULT_SILENCE_ASIDE_CHANCE)
    print("", file=stream)


def main() -> None:
    ensure_utf8_stdio()
    load_cli_env_files()

    args: List[str] = sys.argv[1:]
    command = args[0] if args else None

    if not command:
        print_usage()
        return

    if command not in KNOWN_COMMANDS:
        record_cli_failure()
        print(
            red("🤔 Hmm, never heard of ") + bold(command) + red("."),
            file=sys.stderr,
        )
        t = pick_aside(BIN_UNKNOWN_COMMAND_TEMPLATES)
        print_aside_maybe(
            t["emoji"],
            format_aside_template(t["line"], {"cmd": command}),
            DEFAULT_SILENCE_ASIDE_CHANCE,
        )
        print_usage(sys.stderr)
        sys.exit(1)

    note_command_dispatch(command)

    if command == "init":
        run_init()
        record_cli_success(command)
        return

    if command == "get-logs":
        run_get_logs_command(args)
        record_cli_success(command)
        return

    if command == "server-check":
        run_server_check()
        record_cli_success(command)
        return

    if command == "test-serverlog":
        run_test_serverlog()
        record_cli_success(command)
        return


def _entrypoint() -> None:
    ensure_utf8_stdio()
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        record_cli_failure()
        message = str(exc) if isinstance(exc, Exception) else repr(exc)
        print("", file=sys.stderr)
        print(red_bold("💥 That didn't work."), file=sys.stderr)
        print(dim("   ") + white(message), file=sys.stderr)
        fails = get_consecutive_failures()
        if fails >= 2 and random.random() < 0.45:
            n = pick_aside(WOLVERINE_NUDGE_ASIDES)
            print_aside(n["emoji"], n["line"])
        aside = pick_adaptive_fatal_aside(fails, message)
        print_aside_maybe(aside["emoji"], aside["line"], 0.08)
        err_kind = classify_error_for_aside(message)
        if err_kind in ("network", "auth-env") and random.random() < 0.42:
            e = pick_aside(ENV_SETUP_RECOVERY_ASIDES)
            print_aside(e["emoji"], e["line"])
        maybe_print_generic_spice()
        sys.exit(1)


if __name__ == "__main__":
    _entrypoint()
