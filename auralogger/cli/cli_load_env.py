"""
Load `.env` / `.env.local` from cwd into os.environ.

Used only by the `auralogger` CLI entrypoint — not imported by `aura_log`, so library
code stays free of filesystem env loading (same split as the Node package).
"""

import io
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


def ensure_utf8_stdio() -> None:
    """Match Node/chalk emoji output on Windows (cp1252 default breaks Unicode)."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.StringIO):
            continue
        reconf = getattr(stream, "reconfigure", None)
        if callable(reconf):
            try:
                reconf(encoding="utf-8", errors="replace")
            except (OSError, ValueError, AttributeError, TypeError):
                pass


def _find_project_env_dir(start: Path) -> Optional[Path]:
    """Walk upward from `start` looking for .env / .env.local. Stop at the
    `.git` boundary so we don't pick up env files outside the project."""
    cur = start.resolve()
    while True:
        if (cur / ".env").is_file() or (cur / ".env.local").is_file():
            return cur
        if (cur / ".git").exists():
            return None
        parent = cur.parent
        if parent == cur:
            return None
        cur = parent


def load_cli_env_files(cwd: Optional[str] = None) -> None:
    base = Path(cwd or os.getcwd())
    verbose = os.environ.get("DOTENV_CONFIG_QUIET") == "false"
    # CLI commands are project-scoped: cwd .env should win over inherited shell vars.
    # Walk upward so users who invoke from a subdir still pick up the project-root env.
    env_dir = _find_project_env_dir(base) or base
    load_dotenv(env_dir / ".env", override=True, verbose=verbose)
    load_dotenv(env_dir / ".env.local", override=True, verbose=verbose)
