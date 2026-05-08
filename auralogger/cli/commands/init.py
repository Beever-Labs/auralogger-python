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
    INIT_STRANGE_TOKEN_ASIDES,
    INIT_WELCOME_ASIDES,
    pick_aside,
)
from auralogger.cli.cli_auth import resolve_project_token_for_init, resolve_user_secret_for_init
from auralogger.cli.cli_load_env import ensure_utf8_stdio
from auralogger.cli.cli_personality_state import get_command_attempt_count
from auralogger.cli.cli_style import (
    bold_hex,
    bold_white,
    dim,
    hex_color,
    white,
)
from auralogger.cli.cli_tone import maybe_print_generic_spice, print_aside, print_aside_maybe
from auralogger.cli.log_styles import build_style_entries_from_api
from auralogger.server.proj_auth import fetch_proj_auth_payload_for_cli
from auralogger.utils.env_config import (
    ENV_PROJECT_SESSION,
    ENV_PROJECT_TOKEN,
    ENV_USER_SECRET,
    format_dotenv_line,
    is_full_runtime_env_configured,
    get_resolved_project_token,
    get_resolved_session,
    get_resolved_user_secret,
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
    raw_lines = snippet.split("\n")
    margin = "  "
    print(bold_hex("#d2a8ff", margin + "📋 ") + bold_white(title))
    print()
    for line in raw_lines:
        styled = _syntax_python_line(line)
        print(margin + styled)
    print()


def build_init_payload(
    auth_response: Dict[str, Any], project_token: str
) -> Dict[str, Any]:
    styles_raw = auth_response.get("styles")
    api_rows = styles_raw if isinstance(styles_raw, list) else []
    enc = auth_response.get("encrypted")
    if not isinstance(enc, bool):
        enc = auth_response.get("encryption")
    return {
        "project_token": project_token,
        "project_id": auth_response.get("project_id"),
        "session": auth_response.get("session"),
        "styles": build_style_entries_from_api(api_rows),
        "encrypted": enc if isinstance(enc, bool) else True,
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
    encrypted: bool = payload.get("encrypted", True)  # type: ignore[assignment]

    print()
    print(bold_hex("#79c0ff", "📋 ") + bold_white("Copy-paste env block"))
    if encrypted:
        print(
            dim(
                "   Up to three lines when everything’s new: project token, user secret, session."
            )
        )
    else:
        print(
            dim(
                "   No encryption — just your project token and session needed."
            )
        )
    print()

    lines: List[str] = []
    if not project_token_was_in_env:
        pt = payload.get("project_token")
        tok = pt if isinstance(pt, str) else ""
        lines.append(format_dotenv_line(ENV_PROJECT_TOKEN, tok))
    if encrypted and not user_secret_was_in_env and user_secret:
        lines.append(format_dotenv_line(ENV_USER_SECRET, user_secret))
    if not session_was_in_env and session_str:
        lines.append(format_dotenv_line(ENV_PROJECT_SESSION, session_str))

    if lines:
        margin = "  "
        for ln in lines:
            print(margin + hex_color("#8b949e", ln))

    if project_token_was_in_env:
        print()
        print(
            dim(
                "   Token already in env — server-side apps should read "
                f"{ENV_PROJECT_TOKEN} from the environment or your host’s secret store."
            )
        )

    if project_token_was_in_env or (encrypted and user_secret_was_in_env) or session_was_in_env:
        print()
        if project_token_was_in_env:
            print(
                dim("   ")
                + white("Project token")
                + dim(" was already set — token line omitted above.")
            )
        if encrypted and user_secret_was_in_env:
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
            "from auralogger import Auralogger",
            "",
            "_configured = False",
            "",
            "def ensureConfigured() -> None:",
            "    global _configured",
            "    if _configured:",
            "        return",
            "    project_token = os.environ.get('AURALOGGER_PROJECT_TOKEN', '').strip()",
            "    user_secret = os.environ.get('AURALOGGER_USER_SECRET', '').strip()",
            "    # Silent opt-out: missing creds keep local-only logging (no streaming).",
            "    Auralogger.configure(project_token, user_secret)",
            "    _configured = True",
            "",
            "def auralog(",
            "    type: Literal['debug', 'info', 'warn', 'error'],",
            "    message: str,",
            "    location: Optional[str] = None,",
            "    data: Optional[Dict[str, Any]] = None,",
            ") -> None:",
            "    ensureConfigured()",
            "    Auralogger.log(type, message, location, data)",
        ]
    )


def _build_server_usage_snippet() -> str:
    return "\n".join(
        [
            "from your_auralog_file import auralog",
            "",
            "auralog(",
            "    'info',",
            "    'Request completed',",
            "    'api/orders#create',",
            "    {'order_id': 'ord_123', 'status': 201},",
            ")",
            "# expected: [info] Request completed @ api/orders#create {'order_id': 'ord_123', 'status': 201}",
            "",
            "auralog('warn', 'Cache miss')",
            "# expected: [warn] Cache miss",
            "",
            "auralog('error', 'Payment gateway timeout', data={'provider': 'stripe'})",
            "# expected: [error] Payment gateway timeout {'provider': 'stripe'}",
        ]
    )


def _build_no_encrypt_integration_snippet() -> str:
    return "\n".join(
        [
            "import os",
            "from typing import Any, Dict, Literal, Optional",
            "from auralogger import Auralogger",
            "",
            "_configured = False",
            "",
            "def ensureConfigured() -> None:",
            "    global _configured",
            "    if _configured:",
            "        return",
            "    project_token = os.environ.get('AURALOGGER_PROJECT_TOKEN', '').strip()",
            "    # No user secret needed — encryption is disabled for this project.",
            "    Auralogger.configure(project_token)",
            "    _configured = True",
            "",
            "def auralog(",
            "    type: Literal['debug', 'info', 'warn', 'error'],",
            "    message: str,",
            "    location: Optional[str] = None,",
            "    data: Optional[Dict[str, Any]] = None,",
            ") -> None:",
            "    ensureConfigured()",
            "    Auralogger.log(type, message, location, data)",
        ]
    )


def print_init_helper_snippets(encrypted: bool = True) -> None:
    if encrypted:
        _print_python_code_story(
            "Auralogger — configure and log",
            _build_server_integration_snippet(),
        )
        _print_python_code_story(
            "Using your generated auralog helper (server example logs)",
            _build_server_usage_snippet(),
        )
    else:
        _print_python_code_story(
            "Auralogger — centralized logger, no encryption (token only)",
            _build_no_encrypt_integration_snippet(),
        )
        _print_python_code_story(
            "Using your generated auralog helper (example logs)",
            _build_server_usage_snippet(),
        )
    print()


def print_post_init_summary(
    payload: Dict[str, Any],
    project_token_was_already_in_env: bool,
    user_secret_was_already_in_env: bool,
    session_was_already_in_env: bool,
    user_secret: str,
) -> None:
    encrypted: bool = payload.get("encrypted", True)  # type: ignore[assignment]
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

    print_init_helper_snippets(encrypted)


def print_init_welcome_banner() -> None:
    print()
    print(
        bold_white("Auralogger init")
        + dim(" — wire project token, user secret, and session, coming right up.")
    )
    a = pick_aside(INIT_WELCOME_ASIDES)
    print_aside(a["emoji"], a["line"])
    print()


def print_already_configured_success(encrypted: bool = True) -> None:
    print()
    if encrypted:
        print(
            bold_hex("#ffa657", "🎉 ")
            + white("Plot twist — this shell already has token, user secret, and session.")
        )
    else:
        print(
            bold_hex("#ffa657", "🎉 ")
            + white("Already set — this shell has token and session. No encryption, no secret needed.")
        )
    a = pick_aside(INIT_ALREADY_STRANGE_ASIDES)
    print_aside(a["emoji"], a["line"])
    print()
    print_init_helper_snippets(encrypted)
    a = pick_aside(INIT_ALREADY_LOKI_ASIDES)
    print_aside(a["emoji"], a["line"])
    a = pick_aside(INIT_ALREADY_STEVE_ASIDES)
    print_aside(a["emoji"], a["line"])
    print()


def run_init() -> None:
    ensure_utf8_stdio()
    if get_command_attempt_count("init") >= 2:
        a = pick_aside(INIT_REPEAT_INTENT_ASIDES)
        print_aside_maybe(a["emoji"], a["line"], 0.12)

    # Fast-path: token + secret + session already present → skip proj_auth + prompts.
    if is_full_runtime_env_configured():
        print_already_configured_success(True)
        maybe_print_generic_spice()
        return

    has_project_token = get_resolved_project_token() is not None
    project_token_was_in_env = has_project_token
    has_user_secret = get_resolved_user_secret() is not None
    user_secret_was_in_env = has_user_secret
    has_session = get_resolved_session() is not None
    session_was_in_env = has_session

    print_init_welcome_banner()

    if has_project_token and not has_session:
        print(
            dim("🔎 ")
            + white("Spotted a project token in env — grabbing the rest from home base…")
        )
        a = pick_aside(INIT_STRANGE_TOKEN_ASIDES)
        print_aside(a["emoji"], a["line"])

    project_token = resolve_project_token_for_init()

    raw = fetch_proj_auth_payload_for_cli(project_token)
    payload = build_init_payload(cast(Dict[str, Any], raw), project_token)
    encrypted: bool = payload.get("encrypted", True)  # type: ignore[assignment]

    # Already-configured check — for non-encrypted: token + session is enough.
    if not encrypted and has_project_token and has_session:
        print_already_configured_success(False)
        maybe_print_generic_spice()
        return

    # For encrypted: all three must be present.
    if encrypted and has_project_token and has_user_secret and has_session:
        print_already_configured_success(True)
        maybe_print_generic_spice()
        return

    user_secret = ""
    if encrypted:
        user_secret = resolve_user_secret_for_init()

    print_post_init_summary(
        payload,
        project_token_was_in_env,
        user_secret_was_in_env,
        session_was_in_env,
        user_secret,
    )
    if encrypted:
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
