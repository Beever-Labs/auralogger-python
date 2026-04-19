"""ANSI styling helpers mirroring Node's chalk usage in the CLI."""

from __future__ import annotations

import re

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI SGR sequences so string length matches visible terminal width."""
    return _ANSI_ESCAPE_RE.sub("", text)


def pad_visible(text: str, width: int) -> str:
    """Right-pad text that may contain ANSI codes to a visible column width."""
    n = len(strip_ansi(text))
    if n >= width:
        return text
    return text + " " * (width - n)


def _rgb_fg(r: int, g: int, b: int, text: str) -> str:
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    return f"\033[38;2;{r};{g};{b}m{text}\033[0m"


def _parse_hex(h: str) -> tuple[int, int, int]:
    hx = h.lstrip("#")
    if len(hx) != 6 or not re.fullmatch(r"[0-9a-fA-F]+", hx):
        return (255, 255, 255)
    return int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)


def hex_color(hex_str: str, text: str) -> str:
    r, g, b = _parse_hex(hex_str)
    return _rgb_fg(r, g, b, text)


def bold(text: str) -> str:
    return f"\033[1m{text}\033[0m"


def dim(text: str) -> str:
    return f"\033[2m{text}\033[0m"


def italic(text: str) -> str:
    return f"\033[3m{text}\033[0m"


def bold_hex(hex_str: str, text: str) -> str:
    r, g, b = _parse_hex(hex_str)
    return f"\033[1m\033[38;2;{r};{g};{b}m{text}\033[0m"


def white(text: str) -> str:
    return _rgb_fg(255, 255, 255, text)


def gray(text: str) -> str:
    return _rgb_fg(110, 118, 129, text)


def bold_gray(text: str) -> str:
    return f"\033[1m\033[38;2;{110};{118};{129}m{text}\033[0m"


def green(text: str) -> str:
    return "\033[32m" + text + "\033[0m"


def yellow(text: str) -> str:
    return "\033[33m" + text + "\033[0m"


def red(text: str) -> str:
    return "\033[31m" + text + "\033[0m"


def cyan(text: str) -> str:
    return "\033[96m" + text + "\033[0m"


def bold_white(text: str) -> str:
    return f"\033[1m\033[37m{text}\033[0m"


def red_bold(text: str) -> str:
    return f"\033[1m\033[31m{text}\033[0m"


def italic_hex(hex_str: str, text: str) -> str:
    r, g, b = _parse_hex(hex_str)
    return f"\033[3m\033[38;2;{r};{g};{b}m{text}\033[0m"
