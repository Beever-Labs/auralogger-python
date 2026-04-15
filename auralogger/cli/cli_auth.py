"""Interactive + env resolution for CLI commands (mirrors node init token/user prompts)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, cast

from auralogger.server.proj_auth import fetch_proj_auth_payload
from auralogger.utils.env_config import ENV_PROJECT_TOKEN
from auralogger.utils.env_config import (
    ENV_USER_SECRET,
    get_resolved_project_token,
    get_resolved_user_secret,
)


@dataclass(frozen=True)
class CliProjectContext:
    project_token: str
    user_secret: str
    project_id: str
    project_name: str
    session: str


def prompt_for_project_token() -> str:
    entered = input(f"Paste {ENV_PROJECT_TOKEN} (your project token): ")
    token = entered.strip()
    if not token:
        raise ValueError("Project token cannot be empty.")
    return token


def prompt_for_user_secret() -> str:
    entered = input(f"Paste {ENV_USER_SECRET} (your user secret): ")
    secret = entered.strip()
    if not secret:
        raise ValueError("User secret cannot be empty.")
    return secret


def resolve_project_token_for_init() -> str:
    t = get_resolved_project_token()
    if t:
        return t
    return prompt_for_project_token()


def resolve_user_secret_for_init() -> str:
    s = get_resolved_user_secret()
    if s:
        return s
    return prompt_for_user_secret()


def resolve_project_context_for_cli_checks() -> CliProjectContext:
    project_token = resolve_project_token_for_init()
    user_secret = resolve_user_secret_for_init()
    raw = fetch_proj_auth_payload(project_token)
    auth = cast(Dict[str, Any], raw)

    project_id_raw = auth.get("project_id")
    project_id = project_id_raw.strip() if isinstance(project_id_raw, str) else ""
    project_name_raw = auth.get("project_name")
    project_name = project_name_raw.strip() if isinstance(project_name_raw, str) else ""
    session_raw = auth.get("session")
    session = session_raw.strip() if isinstance(session_raw, str) else ""
    if not project_id or not session:
        raise ValueError(
            f"{ENV_PROJECT_TOKEN} looks invalid, or proj_auth did not return project_id/session."
        )

    return CliProjectContext(
        project_token=project_token,
        user_secret=user_secret,
        project_id=project_id,
        project_name=project_name,
        session=session,
    )
