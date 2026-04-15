"""CLI entrypoint for `auralogger` (mirrors node/src/bin/auralogger.ts)."""

import sys
from typing import TextIO

from auralogger.cli_load_env import load_cli_env_files
from auralogger.commands.client_check import run_client_check
from auralogger.commands.get_logs_cmd import run_get_logs_command
from auralogger.commands.init import run_init
from auralogger.commands.server_check import run_server_check
from auralogger.commands.test_clientlog import run_test_clientlog
from auralogger.commands.test_serverlog import run_test_serverlog


def print_usage(stream: TextIO = sys.stdout) -> None:
    print("Usage:", file=stream)
    print("  auralogger init", file=stream)
    print("  auralogger server-check", file=stream)
    print("  auralogger client-check", file=stream)
    print("  auralogger test-serverlog", file=stream)
    print("  auralogger test-clientlog", file=stream)
    print("  auralogger get-logs [filters...]", file=stream)
    print("", file=stream)
    print("See user-docs/commands.md (in the python package source tree) for filter syntax.", file=stream)


def main() -> None:
    load_cli_env_files()

    args = sys.argv[1:]
    command = args[0] if args else None

    if not command:
        print_usage()
        return

    if command == "init":
        run_init()
        return

    if command == "get-logs":
        run_get_logs_command(args)
        return

    if command == "server-check":
        run_server_check()
        return

    if command == "client-check":
        run_client_check()
        return

    if command == "test-serverlog":
        run_test_serverlog()
        return

    if command == "test-clientlog":
        run_test_clientlog()
        return

    print(f"Unknown command: {command}", file=sys.stderr)
    print(
        "Valid commands: init, server-check, client-check, test-serverlog, test-clientlog, get-logs",
        file=sys.stderr,
    )
    print_usage(sys.stderr)
    sys.exit(1)


def _entrypoint() -> None:
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(
            f"auralogger: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    _entrypoint()
