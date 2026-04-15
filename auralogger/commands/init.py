"""`auralogger init` (mirrors node/src/cli/services/init.ts essentials)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, cast

from auralogger.cli_auth import resolve_project_token_for_init, resolve_user_secret_for_init
from auralogger.env_config import (
    ENV_NEXT_PUBLIC_PROJECT_TOKEN,
    ENV_PROJECT_SESSION,
    ENV_PROJECT_TOKEN,
    ENV_USER_SECRET,
    ENV_VITE_PROJECT_TOKEN,
    format_dotenv_line,
    get_resolved_project_token,
    get_resolved_session,
)
from auralogger.log_styles import build_style_entries_from_api
from auralogger.proj_auth import fetch_proj_auth_payload


def _user_secret_explicitly_in_env() -> bool:
    v = os.environ.get(ENV_USER_SECRET)
    return isinstance(v, str) and bool(v.strip())


def build_init_payload(
    auth_response: Dict[str, Any], project_token: str
) -> Dict[str, Any]:
    styles_raw = auth_response.get("styles")
    api_rows = styles_raw if isinstance(styles_raw, list) else []
    return {
        "project_token": project_token,
        "project_id": auth_response.get("project_id"),
        "session": auth_response.get("session"),
        "styles": build_style_entries_from_api(api_rows),
    }


def print_copy_paste_env_block(
    payload: Dict[str, Any],
    project_token_was_in_env: bool,
    user_secret_was_in_env: bool,
    session_was_in_env: bool,
    user_secret: str,
) -> None:
    session = payload.get("session")
    session_str = session.strip() if isinstance(session, str) else ""

    print()
    print("Copy-paste env block")
    print(
        "   Up to five lines when everything is new: project token, user secret, session, "
        "then the same token for Next and Vite. Project id + DevTools styles come from "
        "proj_auth — no .env lines for those."
    )
    print()

    lines: List[str] = []
    if not project_token_was_in_env:
        pt = payload.get("project_token")
        tok = pt if isinstance(pt, str) else ""
        lines.append(format_dotenv_line(ENV_PROJECT_TOKEN, tok))
    if not user_secret_was_in_env:
        lines.append(format_dotenv_line(ENV_USER_SECRET, user_secret))
    if not session_was_in_env and session_str:
        lines.append(format_dotenv_line(ENV_PROJECT_SESSION, session_str))
    if not project_token_was_in_env:
        pt = payload.get("project_token")
        tok = pt if isinstance(pt, str) else ""
        lines.append(format_dotenv_line(ENV_NEXT_PUBLIC_PROJECT_TOKEN, tok))
        lines.append(format_dotenv_line(ENV_VITE_PROJECT_TOKEN, tok))

    for line in lines:
        print(line)

    if project_token_was_in_env:
        print()
        print(
            f"   Token already in env — if your client cannot read it, add "
            f"{ENV_NEXT_PUBLIC_PROJECT_TOKEN} and {ENV_VITE_PROJECT_TOKEN} with the same "
            "ciphertext."
        )

    if project_token_was_in_env or user_secret_was_in_env or session_was_in_env:
        print()
        if project_token_was_in_env:
            print(
                "   Project token was already set — server/Next/Vite token lines omitted above."
            )
        if user_secret_was_in_env:
            print(f"   {ENV_USER_SECRET} was already set — omitted above.")
        if session_was_in_env:
            print(f"   {ENV_PROJECT_SESSION} was already set — omitted above.")
    print()


def run_init() -> None:
    project_token_was_in_env = get_resolved_project_token() is not None
    user_secret_was_in_env = _user_secret_explicitly_in_env()
    session_was_in_env = get_resolved_session() is not None

    project_token = resolve_project_token_for_init()
    user_secret = resolve_user_secret_for_init()

    raw = fetch_proj_auth_payload(project_token)
    payload = build_init_payload(cast(Dict[str, Any], raw), project_token)

    print()
    print(
        "Add these variables to your environment (for example, paste into a .env file "
        "that your runner loads, or set them in your host dashboard)."
    )
    print(
        "The auralogger library only reads os.environ — use the CLI (or your framework) "
        "to load .env files."
    )
    print("Add .env to .gitignore if you store secrets there.")

    print_copy_paste_env_block(
        payload,
        project_token_was_in_env,
        user_secret_was_in_env,
        session_was_in_env,
        user_secret,
    )

    print(
        'Auralogger init finished. After the variables are set, run: auralogger server-check'
    )
