from __future__ import annotations

import unittest
from unittest.mock import patch

from auralogger import (
    AuraClient,
    AuraServer,
    ClientLogInputs,
    auralog,
    fetch_proj_auth_config,
    fetch_proj_auth_payload,
)


class PublicApiNamingTests(unittest.TestCase):
    def test_fetch_proj_auth_config_delegates_to_payload_fetch(self) -> None:
        expected = {"project_id": "p1", "session": "s1", "styles": []}
        with patch(
            "auralogger.proj_auth.fetch_proj_auth_payload", return_value=expected
        ) as mocked:
            out = fetch_proj_auth_config("cipher-token")
        mocked.assert_called_once_with("cipher-token")
        self.assertEqual(out, expected)

    def test_fetch_proj_auth_payload_still_exported(self) -> None:
        self.assertTrue(callable(fetch_proj_auth_payload))

    def test_aura_server_log_delegates_to_aura_log(self) -> None:
        with patch("auralogger.aura_log.aura_log") as mocked:
            AuraServer.log("info", "hello", "tests/public-api", {"k": 1})
        mocked.assert_called_once_with("info", "hello", "tests/public-api", {"k": 1})

    def test_aura_server_close_socket_delegates(self) -> None:
        with patch("auralogger.aura_log.close_aura_log_socket") as mocked:
            AuraServer.close_socket()
        mocked.assert_called_once_with()

    def test_sync_from_secret_validates_required_fields(self) -> None:
        with patch(
            "auralogger.aura_log.fetch_proj_auth_payload",
            return_value={"project_id": "p1", "session": ""},
        ):
            with self.assertRaises(ValueError):
                AuraServer.sync_from_secret("cipher-token")

    def test_aura_client_log_delegates_to_client_log(self) -> None:
        with patch("auralogger.client.client_log.client_log") as mocked:
            AuraClient.log("info", "hello", "tests/public-api", {"k": 1})
        mocked.assert_called_once_with("info", "hello", "tests/public-api", {"k": 1})

    def test_client_auralog_uses_model_fields(self) -> None:
        with patch("auralogger.client.client_log.AuraClient.log") as mocked:
            auralog(
                ClientLogInputs(
                    type="info",
                    message="hello",
                    location="tests/public-api",
                    data={"k": 1},
                )
            )
        mocked.assert_called_once_with("info", "hello", "tests/public-api", {"k": 1})


if __name__ == "__main__":
    unittest.main()
