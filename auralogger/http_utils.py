"""HTTP error body extraction (mirrors node/src/http-utils.ts)."""

import json
from typing import Any


def parse_error_body(status: int, content_type: str, body_raw: bytes) -> str:
    ct = content_type or ""
    if "application/json" not in ct.lower():
        return f"Request failed with status {status}."

    body: Any
    try:
        body = json.loads(body_raw.decode("utf8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return f"Request failed with status {status}."

    if (
        body is not None
        and isinstance(body, dict)
        and isinstance(body.get("error"), str)
        and body["error"].strip()
    ):
        return str(body["error"]).strip()

    return f"Request failed with status {status}."
