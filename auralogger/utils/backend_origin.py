"""API and WebSocket base URL resolution (mirrors node/src/backend-origin.ts)."""

import os
from typing import Final
from urllib.parse import quote

DEFAULT_AURALOGGER_ORIGIN: Final[str] = "https://api.auralogger.com"
DEFAULT_AURALOGGER_WEB_ORIGIN: Final[str] = "https://auralogger.com"


def trim_trailing_slash(url: str) -> str:
    return url.rstrip("/")


def http_origin_to_ws_base(origin: str) -> str:
    trimmed = trim_trailing_slash(origin.strip())
    if trimmed.startswith("https://"):
        return "wss://" + trimmed[len("https://") :]
    if trimmed.startswith("http://"):
        return "ws://" + trimmed[len("http://") :]
    return trimmed


def resolve_api_base_url() -> str:
    from_env = (os.environ.get("AURALOGGER_API_URL") or "").strip()
    if from_env:
        return trim_trailing_slash(from_env)
    return DEFAULT_AURALOGGER_WEB_ORIGIN


def resolve_ws_base_url() -> str:
    from_env = (os.environ.get("AURALOGGER_WS_URL") or "").strip()
    if from_env:
        return trim_trailing_slash(from_env)
    return http_origin_to_ws_base(DEFAULT_AURALOGGER_ORIGIN)


def _encode_path_token(project_token: str) -> str:
    """Match Node ``encodeURIComponent(projectToken.trim())`` for URL path segments."""
    return quote(project_token.strip(), safe="-_.!~*'()")


def build_proj_auth_url(api_base_url: str, project_token: str) -> str:
    """``POST /api/{project_token}/proj_auth`` — token in path only (no ``secret`` header)."""
    base = trim_trailing_slash(api_base_url.strip())
    return f"{base}/api/{_encode_path_token(project_token)}/proj_auth"


def build_project_logs_url(api_base_url: str, project_token: str) -> str:
    """``POST /api/{project_token}/logs`` — headers ``secret`` + ``user_secret`` = user secret."""
    base = trim_trailing_slash(api_base_url.strip())
    return f"{base}/api/{_encode_path_token(project_token)}/logs"
