import io
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from auralogger import cli


class CliUnknownCommandTests(unittest.TestCase):
    def test_unknown_command_prints_help_and_exits_one(self) -> None:
        stderr = io.StringIO()

        with patch("auralogger.cli.load_cli_env_files"), patch(
            "sys.argv", ["auralogger", "wat"]
        ), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as exit_ctx:
                cli.main()

        self.assertEqual(exit_ctx.exception.code, 1)
        output = stderr.getvalue()
        self.assertIn("Unknown command: wat", output)
        self.assertIn("Valid commands:", output)
        self.assertIn("Usage:", output)
        self.assertIn("auralogger get-logs [filters...]", output)


if __name__ == "__main__":
    unittest.main()
