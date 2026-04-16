from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from auralogger.cli.cli_auth import CliProjectContext, resolve_project_context_for_cli_checks
from auralogger.cli.commands.init import run_init
from auralogger.cli.commands.server_check import run_server_check


class _FakeSocket:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.closed = False

    def send(self, body: str) -> None:
        self.sent.append(body)

    def close(self) -> None:
        self.closed = True


class CliContextResolverTests(unittest.TestCase):
    def test_resolve_project_context_for_cli_checks_success(self) -> None:
        with patch(
            "auralogger.cli.cli_auth.resolve_project_token_for_init", return_value="ptok"
        ), patch(
            "auralogger.cli.cli_auth.resolve_user_secret_for_init", return_value="usec"
        ), patch(
            "auralogger.cli.cli_auth.fetch_proj_auth_payload",
            return_value={"project_id": "pid-1", "project_name": "proj", "session": "sess-1"},
        ):
            ctx = resolve_project_context_for_cli_checks()

        self.assertEqual(
            ctx,
            CliProjectContext(
                project_token="ptok",
                user_secret="usec",
                project_id="pid-1",
                project_name="proj",
                session="sess-1",
            ),
        )

    def test_resolve_project_context_for_cli_checks_validates_required_fields(self) -> None:
        with patch(
            "auralogger.cli.cli_auth.resolve_project_token_for_init", return_value="ptok"
        ), patch(
            "auralogger.cli.cli_auth.resolve_user_secret_for_init", return_value="usec"
        ), patch(
            "auralogger.cli.cli_auth.fetch_proj_auth_payload",
            return_value={"project_id": "pid-1", "session": ""},
        ):
            with self.assertRaises(ValueError):
                resolve_project_context_for_cli_checks()


class CliCommandWiringTests(unittest.TestCase):
    def test_server_check_uses_shared_context_resolver(self) -> None:
        context = CliProjectContext(
            project_token="ptok",
            user_secret="usec",
            project_id="pid-1",
            project_name="proj",
            session="sess-1",
        )
        fake_ws = _FakeSocket()

        with patch(
            "auralogger.cli.commands.server_check.resolve_project_context_for_cli_checks",
            return_value=context,
        ) as resolver, patch(
            "auralogger.cli.commands.server_check.resolve_ws_base_url",
            return_value="wss://api.auralogger.com",
        ), patch(
            "auralogger.cli.commands.server_check.create_connection", return_value=fake_ws
        ) as create_conn:
            run_server_check()

        resolver.assert_called_once_with()
        create_conn.assert_called_once()
        kwargs = create_conn.call_args.kwargs
        self.assertEqual(kwargs["header"], ["Authorization: Bearer usec"])
        self.assertEqual(len(fake_ws.sent), 1)
        self.assertTrue(fake_ws.closed)

class InitParityTests(unittest.TestCase):
    def test_run_init_already_configured_skips_proj_auth(self) -> None:
        output = io.StringIO()
        with patch(
            "auralogger.cli.commands.init.is_full_runtime_env_configured", return_value=True
        ), patch(
            "auralogger.cli.commands.init.fetch_proj_auth_payload"
        ) as fetch_proj_auth, redirect_stdout(output):
            run_init()

        fetch_proj_auth.assert_not_called()
        rendered = output.getvalue()
        self.assertIn("already has token", rendered)
        self.assertIn("auralogger.sync_from_secret", rendered)

    def test_run_init_normal_path_prints_integration_help(self) -> None:
        output = io.StringIO()
        with patch(
            "auralogger.cli.commands.init.is_full_runtime_env_configured", return_value=False
        ), patch(
            "auralogger.cli.commands.init.get_resolved_project_token", return_value=None
        ), patch(
            "auralogger.cli.commands.init.get_resolved_user_secret", return_value=None
        ), patch(
            "auralogger.cli.commands.init.get_resolved_session", return_value=None
        ), patch(
            "auralogger.cli.commands.init.resolve_project_token_for_init", return_value="ptok"
        ), patch(
            "auralogger.cli.commands.init.resolve_user_secret_for_init", return_value="usec"
        ), patch(
            "auralogger.cli.commands.init.fetch_proj_auth_payload",
            return_value={"project_id": "pid-1", "session": "sess-1", "styles": []},
        ), redirect_stdout(output):
            run_init()

        rendered = output.getvalue()
        self.assertIn("Copy-paste env block", rendered)
        self.assertIn("auralogger — configure and log", rendered)


if __name__ == "__main__":
    unittest.main()
