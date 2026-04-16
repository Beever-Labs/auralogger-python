"""In-process CLI session memory — parity with node/src/cli/utility/cli-personality-state.ts."""

from __future__ import annotations

from typing import Dict

_consecutive_failures = 0
_attempt_count_by_command: Dict[str, int] = {}
_success_count_by_command: Dict[str, int] = {}


def note_command_dispatch(command: str) -> None:
    _attempt_count_by_command[command] = _attempt_count_by_command.get(command, 0) + 1


def get_command_attempt_count(command: str) -> int:
    return _attempt_count_by_command.get(command, 0)


def record_cli_success(command: str) -> None:
    global _consecutive_failures
    _consecutive_failures = 0
    _success_count_by_command[command] = _success_count_by_command.get(command, 0) + 1


def record_cli_failure() -> None:
    global _consecutive_failures
    _consecutive_failures += 1


def get_consecutive_failures() -> int:
    return _consecutive_failures


def get_successful_run_count(command: str) -> int:
    return _success_count_by_command.get(command, 0)


def get_total_successful_commands() -> int:
    return sum(_success_count_by_command.values())
