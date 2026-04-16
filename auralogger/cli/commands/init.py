"""`auralogger init` — parity with node/src/cli/services/init.ts (Python snippets)."""

from __future__ import annotations

from typing import Any, Dict, List, cast

from auralogger.cli.aside_pools import (
    INIT_ALREADY_LOKI_ASIDES,
    INIT_ALREADY_STEVE_ASIDES,
    INIT_ALREADY_STRANGE_ASIDES,
    INIT_CURTAIN_TONY_ASIDES,
    INIT_REPEAT_INTENT_ASIDES,
    INIT_SESSION_TONY_ASIDES,
    INIT_SNIPPET_DEADPOOL_ASIDES,
    INIT_SNIPPET_PETER_ASIDES,
    INIT_SNIPPET_THOR_ASIDES,
    INIT_SNIPPET_WOLVERINE_ASIDES,
    INIT_STRANGE_TOKEN_ASIDES,
    INIT_WELCOME_ASIDES,
    pick_aside,
)
from auralogger.cli.cli_auth import resolve_project_token_for_init, resolve_user_secret_for_init
from auralogger.cli.cli_load_env import ensure_utf8_stdio
from auralogger.cli.cli_personality_state import get_command_attempt_count
from auralogger.cli.cli_style import (
    bold_gray,
    bold_hex,
    bold_white,
    dim,
    gray,
    hex_color,
    white,
)
from auralogger.cli.cli_tone import maybe_print_generic_spice, print_aside, print_aside_maybe
from auralogger.cli.log_styles import build_style_entries_from_api
from auralogger.server.proj_auth import fetch_proj_auth_payload
from auralogger.utils.env_config import (
    ENV_NEXT_PUBLIC_PROJECT_TOKEN,
    ENV_PROJECT_SESSION,
    ENV_PROJECT_TOKEN,
    ENV_USER_SECRET,
    ENV_VITE_PROJECT_TOKEN,
    format_dotenv_line,
    get_resolved_project_token,
    get_resolved_session,
    get_resolved_user_secret,
    is_full_runtime_env_configured,
)

_KW = "#ff7b72"
_VAL = "#7ee787"


def _syntax_python_line(line: str) -> str:
    s = line.rstrip("\n")
    if s.startswith("import "):
        return hex_color(_KW, "import") + hex_color(_VAL, " " + s[7:])
    if s.startswith("from "):
        idx = s.find(" import ")
        if idx != -1:
            mid = s[5:idx]
            tail = s[idx + len(" import ") :]
            return (
                hex_color(_KW, "from")
                + hex_color(_VAL, " " + mid)
                + hex_color(_KW, " import")
                + hex_color(_VAL, " " + tail)
            )
        return hex_color(_KW, "from") + hex_color(_VAL, " " + s[5:])
    if s.startswith("class "):
        return hex_color(_KW, "class") + hex_color(_VAL, " " + s[6:])
    if s.startswith("def "):
        return hex_color(_KW, "def") + hex_color(_VAL, " " + s[4:])
    return hex_color(_VAL, s)


def _print_python_code_story(title: str, snippet: str) -> None:
    print(bold_hex("#d2a8ff", "  📋 ") + bold_white(title))
    print()
    for line in snippet.split("\n"):
        print("  " + _syntax_python_line(line))
    print()


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
    print(bold_hex("#79c0ff", "📋 ") + bold_white("Copy-paste env block"))
    print(
        dim(
            "   Up to five lines when everything’s new: server token, user secret, session, "
            "then the same token for Next and Vite. Project id + DevTools styles come from "
            "proj_auth — no .env lines for those."
        )
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
        print(hex_color("#8b949e", line))

    if project_token_was_in_env:
        print()
        print(
            dim(
                f"   Token already in env — if your client can’t read it, add "
                f"{ENV_NEXT_PUBLIC_PROJECT_TOKEN} and {ENV_VITE_PROJECT_TOKEN} with the same "
                "ciphertext."
            )
        )

    if project_token_was_in_env or user_secret_was_in_env or session_was_in_env:
        print()
        if project_token_was_in_env:
            print(
                dim("   ")
                + white("Project token")
                + dim(" was already set — server/Next/Vite token lines omitted above.")
            )
        if user_secret_was_in_env:
            print(
                dim("   ")
                + white(ENV_USER_SECRET)
                + dim(" was already set — omitted above.")
            )
        if session_was_in_env:
            print(
                dim("   ")
                + white(ENV_PROJECT_SESSION)
                + dim(" was already set — omitted above.")
            )
    print()


def _build_server_integration_snippet() -> str:
    return "\n".join(
        [
            "import os",
            "from typing import Any, Dict, Literal, Optional",
            "from pydantic import BaseModel, Field",
            "from auralogger import AuraServer",
            "",
            "class LogInputs(BaseModel):",
            "    type: Literal['debug', 'info', 'warn', 'error'] = 'info'",
            "    message: str = Field(..., min_length=1)",
            "    location: Optional[str] = None",
            "    data: Optional[Dict[str, Any]] = None",
            "",
            "def configure_auralogger() -> None:",
            "    project_token = os.environ.get('AURALOGGER_PROJECT_TOKEN', '').strip()",
            "    user_secret = os.environ.get('AURALOGGER_USER_SECRET', '').strip()",
            "    if not project_token or not user_secret:",
            "        raise RuntimeError('Missing Auralogger server env variables')",
            "    AuraServer.sync_from_secret(project_token, user_secret)",
            "",
            "def auralog(loginputs: LogInputs) -> None:",
            "    AuraServer.log(",
            "        loginputs.type,",
            "        loginputs.message,",
            "        loginputs.location,",
            "        loginputs.data,",
            "    )",
        ]
    )


def _build_client_integration_snippet() -> str:
    return "\n".join(
        [
            "from typing import Any, Dict, Literal, Optional",
            "from pydantic import BaseModel, Field",
            "from auralogger.client import AuraClient",
            "",
            "class ClientLogInputs(BaseModel):",
            "    type: Literal['debug', 'info', 'warn', 'error'] = 'info'",
            "    message: str = Field(..., min_length=1)",
            "    location: Optional[str] = None",
            "    data: Optional[Dict[str, Any]] = None",
            "",
            "def configure_client_logger(project_token: str) -> None:",
            "    AuraClient.sync_from_secret(project_token)",
            "",
            "def auralog(loginputs: ClientLogInputs) -> None:",
            "    AuraClient.log(",
            "        loginputs.type,",
            "        loginputs.message,",
            "        loginputs.location,",
            "        loginputs.data,",
            "    )",
        ]
    )


def print_two_auralog_explainer() -> None:
    print()
    print(
        bold_hex("#d2a8ff", "  🧭 ")
        + white("Split the stack: ")
        + bold_white("Auralog")
        + white(" (browser) vs ")
        + bold_white("AuraLog")
        + white(" (server) — ")
        + bold_white("two files")
        + dim(", zero crossover episodes.")
    )
    print(
        gray("     ")
        + hex_color("#ffa657", "🎨 ")
        + bold_white("Browser / frontend")
        + gray(" — React, Vue, Next client, whatever ships to users. Want ")
        + white("pretty DevTools logs")
        + gray("? This side. ")
        + dim("Project token only — never the user secret.")
    )
    print(
        gray("     ")
        + hex_color("#79c0ff", "🧱 ")
        + bold_white("Server / backend / CLI")
        + gray(" — APIs, workers, scripts, anything that never touches a phone screen. ")
        + white("User secret only lives here.")
    )
    print()


def print_init_helper_snippets_with_character_voices() -> None:
    a = pick_aside(INIT_SNIPPET_PETER_ASIDES)
    print_aside(a["emoji"], a["line"])
    _print_python_code_story(
        "Client-side Auralog — auralogger.client",
        _build_client_integration_snippet(),
    )
    a = pick_aside(INIT_SNIPPET_DEADPOOL_ASIDES)
    print_aside(a["emoji"], a["line"])
    a = pick_aside(INIT_SNIPPET_WOLVERINE_ASIDES)
    print_aside(a["emoji"], a["line"])
    a = pick_aside(INIT_SNIPPET_THOR_ASIDES)
    print_aside(a["emoji"], a["line"])
    _print_python_code_story(
        "Server-side AuraLog — auralogger (AuraServer)",
        _build_server_integration_snippet(),
    )
    print(
        dim(
            "   If your frontend runtime is JavaScript/TypeScript, use the Node package "
            "auralogger-cli/client instead."
        )
    )
    print()


def print_post_init_summary(
    payload: Dict[str, Any],
    project_token_was_already_in_env: bool,
    user_secret_was_already_in_env: bool,
    session_was_already_in_env: bool,
    user_secret: str,
) -> None:
    print()
    a = pick_aside(INIT_SESSION_TONY_ASIDES)
    print_aside(a["emoji"], a["line"])

    print_copy_paste_env_block(
        payload,
        project_token_was_already_in_env,
        user_secret_was_already_in_env,
        session_was_already_in_env,
        user_secret,
    )

    print()
    print_two_auralog_explainer()
    print_init_helper_snippets_with_character_voices()

    print(
        bold_hex("#f85149", "🙅 ")
        + white("Never put ")
        + bold_white(ENV_USER_SECRET)
        + white(" in frontend bundles — only the ")
        + bold_white("server")
        + white(" AuraLog file gets that.")
    )
    print(
        gray("   The ")
        + bold_gray("client")
        + gray(
            " Auralog uses project token only; proj_auth uses the token in the URL path."
        )
    )
    print()


def print_init_welcome_banner() -> None:
    print()
    print(
        bold_white("Auralogger init")
        + dim(" — client pretty-logs + server secrets, coming right up.")
    )
    a = pick_aside(INIT_WELCOME_ASIDES)
    print_aside(a["emoji"], a["line"])
    print()


def print_already_configured_success() -> None:
    print()
    print(
        bold_hex("#ffa657", "🎉 ")
        + white("Plot twist — this shell already has token, user secret, and session.")
    )
    print(
        gray(
            "   Drop-in helpers below — client reads the project token from your bundler; "
            "server uses token + user secret; id/styles can hydrate via proj_auth."
        )
    )
    a = pick_aside(INIT_ALREADY_STRANGE_ASIDES)
    print_aside(a["emoji"], a["line"])
    print()
    print_two_auralog_explainer()
    print_init_helper_snippets_with_character_voices()
    print(
        dim("   Need a fresh session from the API? Unset ")
        + white(ENV_PROJECT_SESSION)
        + dim(", then ")
        + hex_color("#79c0ff", "auralogger init")
        + dim(" again.")
    )
    a = pick_aside(INIT_ALREADY_LOKI_ASIDES)
    print_aside(a["emoji"], a["line"])
    print(
        dim("   Victory lap for the server pipe: ")
        + hex_color("#79c0ff", "auralogger server-check")
    )
    a = pick_aside(INIT_ALREADY_STEVE_ASIDES)
    print_aside(a["emoji"], a["line"])
    print(
        dim(
            "   If your frontend runtime is JavaScript/TypeScript, use the Node package "
            "auralogger-cli/client instead."
        )
    )
    print()


def run_init() -> None:
    ensure_utf8_stdio()
    if get_command_attempt_count("init") >= 2:
        a = pick_aside(INIT_REPEAT_INTENT_ASIDES)
        print_aside_maybe(a["emoji"], a["line"], 0.12)

    has_project_token = get_resolved_project_token() is not None
    project_token_was_in_env = has_project_token
    has_user_secret = get_resolved_user_secret() is not None
    user_secret_was_in_env = has_user_secret
    has_session = get_resolved_session() is not None
    session_was_in_env = has_session

    if is_full_runtime_env_configured():
        print_already_configured_success()
        maybe_print_generic_spice()
        return

    print_init_welcome_banner()

    if has_project_token and not has_session:
        print(
            dim("🔎 ")
            + white("Spotted a project token in env — grabbing the rest from home base…")
        )
        a = pick_aside(INIT_STRANGE_TOKEN_ASIDES)
        print_aside(a["emoji"], a["line"])

    project_token = resolve_project_token_for_init()
    user_secret = resolve_user_secret_for_init()

    raw = fetch_proj_auth_payload(project_token)
    payload = build_init_payload(cast(Dict[str, Any], raw), project_token)

    print_post_init_summary(
        payload,
        project_token_was_in_env,
        user_secret_was_in_env,
        session_was_in_env,
        user_secret,
    )
    print(
        hex_color("#ffa657", "🎬 ")
        + dim("Curtain call: ")
        + hex_color("#79c0ff", "auralogger server-check")
        + dim(" when the server pipe should flex too.")
    )
    a = pick_aside(INIT_CURTAIN_TONY_ASIDES)
    print_aside(a["emoji"], a["line"])
    print("")
    maybe_print_generic_spice()
