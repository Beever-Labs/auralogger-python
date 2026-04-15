from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from auralogger.cli.cli_load_env import load_cli_env_files


class TestCliLoadEnv(unittest.TestCase):
    def test_cwd_env_overrides_inherited_env(self) -> None:
        key = "AURALOGGER_PROJECT_TOKEN"
        original = os.environ.get(key)
        os.environ[key] = "global-token"

        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                (root / ".env").write_text(f'{key}="project-token"\n', encoding="utf8")
                load_cli_env_files(str(root))
                self.assertEqual(os.environ.get(key), "project-token")
        finally:
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original


if __name__ == "__main__":
    unittest.main()
