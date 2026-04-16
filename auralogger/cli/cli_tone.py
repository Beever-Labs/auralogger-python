"""Terminal tone helpers — parity with node/src/cli/utility/cli-tone.ts."""

from __future__ import annotations

import random

from auralogger.cli.aside_pools import (
    DEFAULT_SILENCE_ASIDE_CHANCE,
    GENERIC_SPICE_DEADPOOL_ASIDES,
    pick_aside,
)
from auralogger.cli.cli_style import dim, italic_hex


def print_aside(emoji: str, line: str) -> None:
    print(dim(f"     {emoji} ") + italic_hex("#8b949e", line))


def print_aside_maybe(
    emoji: str,
    line: str,
    silence_chance: float = DEFAULT_SILENCE_ASIDE_CHANCE,
) -> bool:
    if random.random() < silence_chance:
        return False
    print_aside(emoji, line)
    return True


def maybe_print_generic_spice(chance: float = 0.2) -> None:
    if random.random() >= chance:
        return
    a = pick_aside(GENERIC_SPICE_DEADPOOL_ASIDES)
    print_aside(a["emoji"], a["line"])
