"""Terminal log rendering (mirrors node/src/log-print.ts; ANSI RGB instead of chalk)."""

import sys
from datetime import datetime, timezone
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


def _format_created_at_time_only(created_at: Any) -> str:
    if created_at is None or created_at == "":
        return ""
    if isinstance(created_at, datetime):
        d = created_at
    else:
        s = str(created_at)
        try:
            # Accept "Z" suffix and timezone offsets, then normalize to UTC time-of-day.
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return s
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    d = d.astimezone(timezone.utc)
    return d.strftime("%H:%M:%S")


def print_log(log: Mapping[str, Any], config_styles: Any) -> None:
    type_raw = log.get("type")
    type_str = type_raw if isinstance(type_raw, str) else ""
    spec = resolve_log_style_spec(type_str, config_styles)

    created = _format_created_at_time_only(log.get("created_at"))
    icon = spec.get("icon", "")
    type_disp = log.get("type")
    loc = log.get("location")

    line1 = " ".join(
        (
            _dim(_rgb(str(created), spec.get("time-color"))),
            _rgb(str(loc), spec.get("location-color")),
        )
    )
    line1 = line1.replace(" ", "    ", 1)
    msg = log.get("message")
    icon_and_type = " ".join(
        p
        for p in (
            str(icon).strip(),
            _rgb(str(type_disp if type_disp is not None else ""), spec.get("type-color")),
        )
        if p.strip()
    )
    message_line = " ".join(
        (
            icon_and_type,
            _rgb(str(msg if msg is not None else ""), spec.get("message-color")),
        )
    ).strip()

    data = log.get("data")
    parts = [line1, message_line]
    if data is not None and str(data).strip():
        parts.append(_dim(_rgb(str(data), spec.get("text-color"))))
    _print_stdout_line("\n".join(parts))
