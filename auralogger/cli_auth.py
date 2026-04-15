"""Interactive + env resolution for CLI commands (mirrors node init token/user prompts)."""

from __future__ import annotations

from auralogger.env_config import (
    ENV_PROJECT_TOKEN,
    ENV_USER_SECRET,
    get_resolved_project_token,
    get_resolved_user_secret,
)


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
