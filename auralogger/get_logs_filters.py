"""Filter normalization for POST /api/{project_token}/logs (mirrors node get-logs-filters)."""

import math
from typing import Any, Dict, List

from auralogger.parser import ParsedFilter

MAX_MAXCOUNT = 100

# Alias for callers documenting expected log API filter shape.
ApiLogFilter = Dict[str, Any]


def _default_op_for_field(field: str) -> str:
    if field.startswith("data."):
        return "eq"
    if field in ("order", "maxcount", "skip"):
        return "eq"
    if field == "message":
        return "contains"
    if field == "location":
        return "in"
    if field == "time":
        return "since"
    if field == "type":
        return "in"
    raise ValueError(f"Unknown filter field: {field}")


def _allowed_ops_for_field(field: str) -> List[str]:
    if field.startswith("data."):
        return ["eq"]
    if field == "type":
        return ["in", "not-in"]
    if field == "message":
        return ["contains", "not-contains"]
    if field == "location":
        return ["in", "not-in"]
    if field == "time":
        return ["since", "from-to"]
    if field in ("order", "maxcount", "skip"):
        return ["eq"]
    return []


def normalize_and_validate_filters(parsed: List[ParsedFilter]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for filt in parsed:
        default_op = _default_op_for_field(filt.field)
        allowed = _allowed_ops_for_field(filt.field)
        if not allowed:
            raise ValueError(f"Unknown filter field: {filt.field}")

        resolved_op = filt.op if filt.op is not None else default_op
        if resolved_op not in allowed:
            raise ValueError(
                f"Invalid op '{resolved_op}' for field '{filt.field}'. "
                f"Allowed: {', '.join(allowed)}"
            )

        value: Any = filt.value
        if filt.field == "maxcount" and isinstance(value, (int, float)):
            if isinstance(value, float) and not math.isfinite(value):
                pass
            else:
                value = min(max(0, int(math.floor(float(value)))), MAX_MAXCOUNT)
        if filt.field == "skip" and isinstance(value, (int, float)):
            if not (isinstance(value, float) and not math.isfinite(value)):
                value = max(0, int(math.floor(float(value))))

        api: Dict[str, Any] = {"field": filt.field, "value": value}
        if resolved_op != default_op:
            api["op"] = resolved_op
        result.append(api)

    return result
