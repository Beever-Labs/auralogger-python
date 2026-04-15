"""Log style specs and config normalization (mirrors node/src/log-styles.ts)."""

import json
from typing import Any, Dict, List, cast

DEFAULT_LOG_STYLE_SPEC: Dict[str, Any] = {
    "icon": "🗒️",
    "type-color": [23, 230, 154],
    "background": [0, 0, 0],
    "borderColor": [255, 255, 255],
    "location-color": [63, 102, 191],
    "time-color": [129, 68, 235],
    "message-color": [235, 68, 210],
    "text-color": [255, 255, 255],
}


def clone_default_spec() -> Dict[str, Any]:
    return cast(Dict[str, Any], json.loads(json.dumps(DEFAULT_LOG_STYLE_SPEC)))


def is_plain_object(value: object) -> bool:
    return isinstance(value, dict)


def _importance_key(row: object) -> float:
    if not is_plain_object(row):
        return 0.0
    v = cast(Dict[str, Any], row).get("importance")
    try:
        return float(v if v is not None else 0)
    except (TypeError, ValueError):
        return 0.0


def build_style_entries_from_api(rows: object) -> List[Dict[str, Any]]:
    """Build style entries for ``AURALOGGER_PROJECT_STYLES`` (JSON env) after init."""
    map_obj: Dict[str, Any] = {"default": clone_default_spec()}
    list_rows = rows if isinstance(rows, list) else []
    sorted_rows = sorted(list_rows, key=_importance_key)

    for row in sorted_rows:
        if not is_plain_object(row):
            continue
        r = cast(Dict[str, Any], row)
        t_raw = r.get("type")
        t = t_raw.strip() if isinstance(t_raw, str) else ""
        if not t:
            continue

        inner_styles = r.get("styles")
        inner: Dict[str, Any] = inner_styles if is_plain_object(inner_styles) else {}

        if t == "default":
            cast(Dict[str, Any], map_obj["default"]).update(inner)
        elif inner:
            map_obj[t] = inner

    return [{k: v} for k, v in map_obj.items()]


def style_map_from_config_entries(entries: object) -> Dict[str, Any]:
    by_type: Dict[str, Any] = {}

    if not isinstance(entries, list):
        by_type["default"] = clone_default_spec()
        return by_type

    for item in entries:
        if not is_plain_object(item):
            continue
        for k, v in cast(Dict[str, Any], item).items():
            if is_plain_object(v):
                by_type[k] = v

    if "default" not in by_type:
        by_type["default"] = clone_default_spec()

    return by_type


def resolve_log_style_spec(log_type: str, config_styles: object) -> Dict[str, Any]:
    style_map = style_map_from_config_entries(config_styles)
    base_raw = style_map.get("default")
    base: Dict[str, Any] = (
        cast(Dict[str, Any], base_raw).copy()
        if is_plain_object(base_raw)
        else clone_default_spec()
    )
    t = log_type.strip() if isinstance(log_type, str) and log_type.strip() else "unknown"
    specific = style_map.get(t)
    if not is_plain_object(specific):
        return base
    merged = base.copy()
    merged.update(cast(Dict[str, Any], specific))
    return merged
