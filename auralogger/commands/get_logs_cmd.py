"""CLI entry for `get-logs` (mirrors node dispatch to get-logs)."""

from typing import List

from auralogger.get_logs import run_get_logs


def run_get_logs_command(argv: List[str]) -> None:
    run_get_logs(argv)
