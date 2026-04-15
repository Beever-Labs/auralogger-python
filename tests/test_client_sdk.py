from __future__ import annotations

import unittest
from unittest.mock import patch

from auralogger.client.client_log import (
    AuraClient,
    ClientLogInputs,
    auralog,
    client_log,
    close_client_log_socket,
)


class _FakeSocket:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.closed = False

    def send(self, body: str) -> None:
        self.sent.append(body)

    def close(self) -> None:
        self.closed = True


class AuraClientSdkTests(unittest.TestCase):
    def test_configure_rejects_empty_token(self) -> None:
        with self.assertRaises(ValueError):
            AuraClient.configure("   ")

    def test_sync_from_secret_validates_required_fields(self) -> None:
        with patch(
            "auralogger.client.client_log.fetch_proj_auth_payload",
            return_value={"project_id": "p1", "session": ""},
        ):
            with self.assertRaises(ValueError):
                AuraClient.sync_from_secret("cipher-token")

    def test_log_delegates_to_client_log_function(self) -> None:
        with patch("auralogger.client.client_log.client_log") as mocked:
            AuraClient.log("info", "hello", "tests/client", {"k": 1})
        mocked.assert_called_once_with("info", "hello", "tests/client", {"k": 1})

    def test_auralog_uses_typed_inputs(self) -> None:
        with patch("auralogger.client.client_log.AuraClient.log") as mocked:
            auralog(
                ClientLogInputs(
                    type="warn",
                    message="typed input",
                    location="tests/client",
                    data={"ok": True},
                )
            )
        mocked.assert_called_once_with("warn", "typed input", "tests/client", {"ok": True})

    def test_client_log_sends_when_runtime_is_hydrated(self) -> None:
        ws = _FakeSocket()
        with patch(
            "auralogger.client.client_log._resolve_project_token_runtime",
            return_value="ptok",
        ), patch(
            "auralogger.client.client_log._merged_runtime_for_send",
            return_value={"project_id": "pid", "session": "sess", "styles": []},
        ), patch(
            "auralogger.client.client_log._ensure_ws",
            return_value=ws,
        ), patch("auralogger.client.client_log.print_log"), patch(
            "auralogger.client.client_log._schedule_socket_idle_close"
        ):
            client_log("info", "hello", "tests/client", {"x": 1})

        self.assertEqual(len(ws.sent), 1)

    def test_close_socket_delegates(self) -> None:
        with patch("auralogger.client.client_log.close_client_log_socket") as mocked:
            AuraClient.close_socket()
        mocked.assert_called_once_with()

    def test_close_client_log_socket_closes_ws(self) -> None:
        ws = _FakeSocket()
        with patch("auralogger.client.client_log._ws", ws), patch(
            "auralogger.client.client_log._bound_url", "wss://x"
        ):
            close_client_log_socket()
        self.assertTrue(ws.closed)


if __name__ == "__main__":
    unittest.main()
