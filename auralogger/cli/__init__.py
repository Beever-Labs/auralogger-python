"""CLI package. Entrypoint: ``auralogger.cli.cli`` (``main``, ``print_usage``)."""

from __future__ import annotations

from typing import Any

__all__ = ["main", "print_usage"]


def __getattr__(name: str) -> Any:
    if name == "main":
        from auralogger.cli.cli import main

        return main
    if name == "print_usage":
        from auralogger.cli.cli import print_usage

        return print_usage
    # Console scripts may target ``auralogger.cli:_entrypoint`` (older installs / metadata).
    if name == "_entrypoint":
        from auralogger.cli.cli import _entrypoint

        return _entrypoint
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
