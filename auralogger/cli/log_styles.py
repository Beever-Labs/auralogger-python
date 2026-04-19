"""Log style specs and config normalization (mirrors node/src/log-styles.ts)."""

import json
from typing import Any, Dict, List, cast

DEFAULT_LOG_STYLE_SPEC: Dict[str, Any] = {
    "icon": "🔹",
    "type-color": [200, 160, 255],
    "background": [0, 0, 0],
    "borderColor": [255, 255, 255],
    "location-color": [63, 102, 191],
    "time-color": [210, 200, 255],
    "message-color": [220, 200, 255],
    "text-color": [250, 245, 255],
}

BUILTIN_TYPE_STYLE_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "ERROR": {
        "icon": "❌",
        "type-color": [255, 80, 80],
        "message-color": [255, 140, 140],
        "text-color": [255, 255, 255],
        "time-color": [200, 200, 200],
    },
    "FAIL": {
        "icon": "💥",
        "type-color": [255, 40, 120],
        "message-color": [255, 120, 180],
        "text-color": [255, 255, 255],
        "time-color": [200, 200, 200],
    },
    "SUCCESS": {
        "icon": "✅",
        "type-color": [0, 255, 200],
        "message-color": [150, 255, 230],
        "text-color": [245, 255, 250],
        "time-color": [200, 255, 230],
    },
    "PASS": {
        "icon": "✔️",
        "type-color": [0, 255, 160],
        "message-color": [140, 255, 210],
        "text-color": [245, 255, 250],
        "time-color": [200, 255, 220],
    },
    "WARNING": {
        "icon": "⚠️",
        "type-color": [255, 220, 0],
        "message-color": [255, 240, 120],
        "text-color": [255, 255, 255],
        "time-color": [255, 230, 150],
    },
    "INFO": {
        "icon": "ℹ️",
        "type-color": [80, 200, 255],
        "message-color": [160, 230, 255],
        "text-color": [245, 250, 255],
        "time-color": [180, 220, 255],
    },
    "DEFAULT": {
        "icon": "🔹",
        "type-color": [200, 160, 255],
        "message-color": [220, 200, 255],
        "text-color": [250, 245, 255],
        "time-color": [210, 200, 255],
    },
}


def clone_default_spec() -> Dict[str, Any]:
    return cast(Dict[str, Any], json.loads(json.dumps(DEFAULT_LOG_STYLE_SPEC)))


def clone_builtin_style_map() -> Dict[str, Dict[str, Any]]:
    return {
        log_type: {**clone_default_spec(), **spec}
        for log_type, spec in BUILTIN_TYPE_STYLE_OVERRIDES.items()
    }


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
    by_type: Dict[str, Any] = clone_builtin_style_map()
    by_type["default"] = clone_default_spec()

    if not isinstance(entries, list):
        return by_type

    for item in entries:
        if not is_plain_object(item):
            continue
        for k, v in cast(Dict[str, Any], item).items():
            if is_plain_object(v):
                by_type[k] = v
                by_type[k.upper()] = v

    if "default" not in by_type:
        by_type["default"] = clone_default_spec()

    return by_type


def resolve_log_style_spec(log_type: str, config_styles: object = None) -> Dict[str, Any]:
    style_map = style_map_from_config_entries(config_styles)
    base_raw = style_map.get("default")
    base: Dict[str, Any] = (
        cast(Dict[str, Any], base_raw).copy()
        if is_plain_object(base_raw)
        else clone_default_spec()
    )
    t = log_type.strip() if isinstance(log_type, str) else ""
    specific = (
        style_map.get(t)
        or style_map.get(t.upper())
        or style_map.get(t.lower())
        or style_map.get("DEFAULT")
    )
    if not is_plain_object(specific):
        return base
    merged = base.copy()
    merged.update(cast(Dict[str, Any], specific))
    return merged
