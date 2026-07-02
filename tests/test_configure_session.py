from __future__ import annotations

import importlib
import unittest
from unittest.mock import patch

from auralogger import Auralogger

aura_log_module = importlib.import_module("auralogger.server.aura_log")

_PROJ_AUTH_RAW = {"project_id": "p1", "session": "proj-auth-sess", "styles": []}


class ConfigureSessionPrecedenceTests(unittest.TestCase):
    """session precedence: explicit arg → env → proj_auth response."""

    def tearDown(self) -> None:
        # Reset runtime state so tests stay independent.
        Auralogger._apply_runtime_config("", "", "", True)

    def test_explicit_session_arg_wins(self) -> None:
        with patch.dict(
            "os.environ",
            {"AURALOGGER_PROJECT_SESSION": "env-sess"},
            clear=False,
        ), patch(
            "auralogger.server.aura_log.fetch_proj_auth_payload",
            return_value=dict(_PROJ_AUTH_RAW),
        ):
            Auralogger.configure("cipher-token", "secret-123", session="explicit-sess")
        self.assertEqual(aura_log_module._override_session, "explicit-sess")

    def test_env_session_used_when_no_arg(self) -> None:
        with patch.dict(
            "os.environ",
            {"AURALOGGER_PROJECT_SESSION": "env-sess"},
            clear=False,
        ), patch(
            "auralogger.server.aura_log.fetch_proj_auth_payload",
            return_value=dict(_PROJ_AUTH_RAW),
        ):
            Auralogger.configure("cipher-token", "secret-123")
        self.assertEqual(aura_log_module._override_session, "env-sess")

    def test_falls_back_to_proj_auth_when_no_arg_or_env(self) -> None:
        # Blank out every env session variant so only proj_auth can supply one.
        with patch.dict(
            "os.environ",
            {
                "AURALOGGER_PROJECT_SESSION": "",
                "NEXT_PUBLIC_AURALOGGER_PROJECT_SESSION": "",
                "VITE_AURALOGGER_PROJECT_SESSION": "",
            },
            clear=False,
        ), patch(
            "auralogger.server.aura_log.fetch_proj_auth_payload",
            return_value=dict(_PROJ_AUTH_RAW),
        ):
            Auralogger.configure("cipher-token", "secret-123")
        self.assertIsNone(aura_log_module._override_session)
        self.assertEqual(aura_log_module._session, "proj-auth-sess")

    def test_console_echo_uses_override_session(self) -> None:
        captured = {}

        def fake_print_log(payload, styles):  # noqa: ANN001
            captured["session"] = payload.get("session")

        with patch.dict(
            "os.environ",
            {"AURALOGGER_PROJECT_SESSION": "env-sess"},
            clear=False,
        ), patch(
            "auralogger.server.aura_log.fetch_proj_auth_payload",
            return_value=dict(_PROJ_AUTH_RAW),
        ), patch(
            "auralogger.server.aura_log.print_log", side_effect=fake_print_log
        ), patch(
            "auralogger.server.aura_log._enqueue"
        ):
            Auralogger.configure("cipher-token", "secret-123", session="explicit-sess")
            Auralogger.log("info", "hello", "tests/session")

        self.assertEqual(captured["session"], "explicit-sess")


if __name__ == "__main__":
    unittest.main()
