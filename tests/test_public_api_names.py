from __future__ import annotations

import unittest
from unittest.mock import patch

from auralogger import auralogger, fetch_proj_auth_config, fetch_proj_auth_payload


class PublicApiNamingTests(unittest.TestCase):
    def test_fetch_proj_auth_config_delegates_to_payload_fetch(self) -> None:
        expected = {"project_id": "p1", "session": "s1", "styles": []}
        with patch(
            "auralogger.server.proj_auth.fetch_proj_auth_payload", return_value=expected
        ) as mocked:
            out = fetch_proj_auth_config("cipher-token")
        mocked.assert_called_once_with("cipher-token")
        self.assertEqual(out, expected)

    def test_fetch_proj_auth_payload_still_exported(self) -> None:
        self.assertTrue(callable(fetch_proj_auth_payload))

    def test_auralogger_log_delegates_to_aura_log(self) -> None:
        with patch("auralogger.server.aura_log.aura_log") as mocked:
            auralogger.log("info", "hello", "tests/public-api", {"k": 1})
        mocked.assert_called_once_with("info", "hello", "tests/public-api", {"k": 1})

    def test_auralogger_close_socket_delegates(self) -> None:
        with patch("auralogger.server.aura_log.close_aura_log_socket") as mocked:
            auralogger.close_socket()
        mocked.assert_called_once_with()

    def test_configure_reads_env_and_fetches_proj_auth(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "AURALOGGER_PROJECT_TOKEN": "cipher-token",
                "AURALOGGER_USER_SECRET": "secret-123",
            },
            clear=False,
        ), patch(
            "auralogger.server.aura_log.fetch_proj_auth_payload",
            return_value={"project_id": "p1", "session": "s1", "styles": []},
        ) as mocked:
            auralogger.configure()
        mocked.assert_called_once_with("cipher-token")

    def test_sync_from_secret_validates_required_fields(self) -> None:
        with patch(
            "auralogger.server.aura_log.fetch_proj_auth_payload",
            return_value={"project_id": "p1", "session": ""},
        ):
            with self.assertRaises(ValueError):
                auralogger.sync_from_secret("cipher-token", "secret-123")


if __name__ == "__main__":
    unittest.main()
