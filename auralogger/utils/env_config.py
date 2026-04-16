"""Read Auralogger settings from os.environ only (library / runtime path; no file I/O)."""

from __future__ import annotations

import json
import os
from typing import Any, List, Optional, Sequence

# Primary keys (mirrors node/src/utils/env-config.ts)
ENV_PROJECT_TOKEN = "AURALOGGER_PROJECT_TOKEN"
ENV_NEXT_PUBLIC_PROJECT_TOKEN = "NEXT_PUBLIC_AURALOGGER_PROJECT_TOKEN"
ENV_VITE_PROJECT_TOKEN = "VITE_AURALOGGER_PROJECT_TOKEN"
ENV_USER_SECRET = "AURALOGGER_USER_SECRET"

ENV_PROJECT_ID = "AURALOGGER_PROJECT_ID"
ENV_NEXT_PUBLIC_PROJECT_ID = "NEXT_PUBLIC_AURALOGGER_PROJECT_ID"
ENV_VITE_PROJECT_ID = "VITE_AURALOGGER_PROJECT_ID"

ENV_PROJECT_SESSION = "AURALOGGER_PROJECT_SESSION"
ENV_NEXT_PUBLIC_PROJECT_SESSION = "NEXT_PUBLIC_AURALOGGER_PROJECT_SESSION"
ENV_VITE_PROJECT_SESSION = "VITE_AURALOGGER_PROJECT_SESSION"

ENV_PROJECT_STYLES = "AURALOGGER_PROJECT_STYLES"
ENV_NEXT_PUBLIC_PROJECT_STYLES = "NEXT_PUBLIC_AURALOGGER_PROJECT_STYLES"
ENV_VITE_PROJECT_STYLES = "VITE_AURALOGGER_PROJECT_STYLES"


def _trim_env(key: str) -> Optional[str]:
    v = os.environ.get(key)
    if not isinstance(v, str):
        return None
    t = v.strip()
    return t if t else None


def _trim_env_any(keys: Sequence[str]) -> Optional[str]:
    for k in keys:
        v = _trim_env(k)
        if v:
            return v
    return None


def get_resolved_project_token() -> Optional[str]:
    return _trim_env_any(
        (ENV_PROJECT_TOKEN, ENV_NEXT_PUBLIC_PROJECT_TOKEN, ENV_VITE_PROJECT_TOKEN)
    )


def get_resolved_user_secret() -> Optional[str]:
    return _trim_env(ENV_USER_SECRET)


def get_resolved_project_id() -> Optional[str]:
    return _trim_env_any(
        (ENV_PROJECT_ID, ENV_NEXT_PUBLIC_PROJECT_ID, ENV_VITE_PROJECT_ID)
    )


def get_resolved_session() -> Optional[str]:
    return _trim_env_any(
        (ENV_PROJECT_SESSION, ENV_NEXT_PUBLIC_PROJECT_SESSION, ENV_VITE_PROJECT_SESSION)
    )


def try_parse_resolved_styles() -> Optional[List[Any]]:
    raw = _trim_env_any(
        (ENV_PROJECT_STYLES, ENV_NEXT_PUBLIC_PROJECT_STYLES, ENV_VITE_PROJECT_STYLES)
    )
    if raw is None:
        return None
    try:
        parsed: object = json.loads(raw)
        if not isinstance(parsed, list):
            return None
        return parsed
    except (json.JSONDecodeError, TypeError):
        return None


def parse_resolved_styles_or_throw() -> List[Any]:
    raw = _trim_env_any(
        (ENV_PROJECT_STYLES, ENV_NEXT_PUBLIC_PROJECT_STYLES, ENV_VITE_PROJECT_STYLES)
    )
    if raw is None:
        raise ValueError(
            f"Set {ENV_PROJECT_STYLES} (or {ENV_NEXT_PUBLIC_PROJECT_STYLES} / "
            f'{ENV_VITE_PROJECT_STYLES}) in the environment. Run "auralogger init" '
            "and add the lines it prints, or rely on a get-logs run that fetches styles."
        )
    try:
        parsed: object = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError(
                f"{ENV_PROJECT_STYLES} must be a JSON array (same shape as from "
                'auralogger init).'
            )
        return parsed
    except json.JSONDecodeError as e:
        raise ValueError(
            f"{ENV_PROJECT_STYLES} is not valid JSON. Run \"auralogger init\" to refresh."
        ) from e


def require_project_token_for_cli() -> str:
    t = get_resolved_project_token()
    if not t:
        raise ValueError(
            f"Missing {ENV_PROJECT_TOKEN} (or {ENV_NEXT_PUBLIC_PROJECT_TOKEN} / "
            f"{ENV_VITE_PROJECT_TOKEN}) — add it to .env or run auralogger init."
        )
    return t


def require_user_secret_for_cli() -> str:
    s = get_resolved_user_secret()
    if not s:
        raise ValueError(
            f"Missing {ENV_USER_SECRET} — add it to .env or run auralogger init."
        )
    return s


def require_project_id_for_cli() -> str:
    pid = get_resolved_project_id()
    if not pid:
        raise ValueError(
            f"No project id in this shell — set {ENV_PROJECT_ID} or run auralogger init."
        )
    return pid


def is_full_runtime_env_configured() -> bool:
    """True when project token, user secret, and session are set (id/styles may hydrate)."""
    return bool(
        get_resolved_project_token()
        and get_resolved_user_secret()
        and get_resolved_session()
    )


def format_dotenv_line(key: str, value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )
    return f'{key}="{escaped}"'
