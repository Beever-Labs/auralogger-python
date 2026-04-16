"""Utility exports for host integration and testing helpers."""

from auralogger.utils.backend_origin import (
    build_proj_auth_url,
    build_project_logs_url,
    resolve_api_base_url,
    resolve_ws_base_url,
)
from auralogger.utils.env_config import (
    ENV_NEXT_PUBLIC_PROJECT_TOKEN,
    ENV_PROJECT_ID,
    ENV_PROJECT_SESSION,
    ENV_PROJECT_STYLES,
    ENV_PROJECT_TOKEN,
    ENV_USER_SECRET,
    ENV_VITE_PROJECT_TOKEN,
)
from auralogger.utils.http_utils import parse_error_body

__all__ = [
    "build_proj_auth_url",
    "build_project_logs_url",
    "resolve_api_base_url",
    "resolve_ws_base_url",
    "parse_error_body",
    "ENV_PROJECT_TOKEN",
    "ENV_NEXT_PUBLIC_PROJECT_TOKEN",
    "ENV_VITE_PROJECT_TOKEN",
    "ENV_USER_SECRET",
    "ENV_PROJECT_ID",
    "ENV_PROJECT_SESSION",
    "ENV_PROJECT_STYLES",
]
