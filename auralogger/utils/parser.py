"""Parses `get-logs` argv (mirrors node/src/parser.ts)."""

import json
import math
from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class ParsedFilter:
    field: str
    op: Optional[str]
    value: Any


@dataclass
class ParsedGetLogsCommand:
    filters: List[ParsedFilter]


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    return False


def parse_command(tokens: List[str]) -> ParsedGetLogsCommand:
    if not tokens or tokens[0] != "get-logs":
        raise ValueError("Expected 'get-logs'")

    filters: List[ParsedFilter] = []
    i = 1

    while i < len(tokens):
        field_token = tokens[i]
        if not field_token.startswith("-"):
            raise ValueError(f"Expected field at position {i}")

        field = field_token[1:]
        i += 1

        op: Optional[str] = None
        if i < len(tokens) and tokens[i].startswith("--"):
            op = tokens[i][2:]
            i += 1

        if i >= len(tokens):
            raise ValueError(f"Missing value for field '{field}'")

        value_token = tokens[i]
        try:
            value = json.loads(value_token)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON for field '{field}'") from None

        if field in ("maxcount", "nextpage"):
            if not _is_finite_number(value):
                raise ValueError(
                    f"Field '{field}' expects a JSON number token (e.g. 50)"
                )
        elif not isinstance(value, list):
            raise ValueError(
                f"Field '{field}' expects a JSON array token (e.g. [\"a\"])"
            )

        i += 1
        filters.append(ParsedFilter(field=field, op=op, value=value))

    return ParsedGetLogsCommand(filters=filters)
