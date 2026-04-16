"""Terminal log rendering (mirrors node/src/log-print.ts; ANSI RGB instead of chalk)."""

import sys
from typing import Any, Mapping

from auralogger.cli.log_styles import resolve_log_style_spec


def _rgb(text: str, rgb: Any) -> str:
    if (
        isinstance(rgb, list)
        and len(rgb) == 3
        and all(isinstance(x, (int, float)) for x in rgb)
    ):
        r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return f"\033[38;2;{r};{g};{b}m{text}\033[0m"
    return text


def _dim(text: str) -> str:
    return f"\033[2m{text}\033[0m"


def _print_stdout_line(parts: str) -> None:
    """Avoid UnicodeEncodeError on Windows consoles that default to a legacy code page."""
    try:
        print(parts)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        sys.stdout.buffer.write(parts.encode(enc, errors="replace") + b"\n")


def print_log(log: Mapping[str, Any], config_styles: Any) -> None:
    type_raw = log.get("type")
    type_str = type_raw if isinstance(type_raw, str) else ""
    spec = resolve_log_style_spec(type_str, config_styles)

    created = log.get("created_at")
    icon = spec.get("icon", "")
    type_disp = log.get("type")
    loc = log.get("location")

    line1 = " ".join(
        (
            _dim(_rgb(str(created), spec.get("time-color"))),
            str(icon),
            _dim(_rgb(str(type_disp), spec.get("type-color"))),
            _rgb(str(loc), spec.get("location-color")),
        )
    )
    _print_stdout_line(line1)

    msg = log.get("message")
    _print_stdout_line(_rgb(str(msg if msg is not None else ""), spec.get("message-color")))

    data = log.get("data")
    if data is not None and str(data).strip():
        _print_stdout_line(_dim(_rgb(str(data), spec.get("text-color"))))
