"""
Load `.env` / `.env.local` from cwd into os.environ.

Used only by the `auralogger` CLI entrypoint — not imported by `aura_log`, so library
code stays free of filesystem env loading (same split as the Node package).
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


def load_cli_env_files(cwd: Optional[str] = None) -> None:
    base = Path(cwd or os.getcwd())
    verbose = os.environ.get("DOTENV_CONFIG_QUIET") == "false"
    # CLI commands are project-scoped: cwd .env should win over inherited shell vars.
    load_dotenv(base / ".env", override=True, verbose=verbose)
    load_dotenv(base / ".env.local", override=True, verbose=verbose)
