"""Regression tests for HTTP/WS URL and header shapes (Node parity)."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from auralogger.utils.backend_origin import (
    build_create_browser_logs_url,
    build_proj_auth_url,
    build_project_logs_url,
)


class TestBackendUrls(unittest.TestCase):
    def test_proj_auth_path_encodes_token(self) -> None:
        url = build_proj_auth_url("https://auralogger.com", "ab/c d")
        self.assertIn("/api/ab%2Fc%20d/proj_auth", url)
        self.assertTrue(url.startswith("https://auralogger.com"))

    def test_logs_path_encodes_token(self) -> None:
        url = build_project_logs_url("https://auralogger.com", "tok")
        self.assertEqual(url, "https://auralogger.com/api/tok/logs")

    def test_create_browser_logs_path_encodes_token(self) -> None:
        url = build_create_browser_logs_url("wss://api.auralogger.com", "ab/c d")
        self.assertEqual(url, "wss://api.auralogger.com/ab%2Fc%20d/create_browser_logs")


class TestGetLogsPost(unittest.TestCase):
    def test_post_logs_uses_user_secret_headers(self) -> None:
        from auralogger.cli.get_logs import _post_logs

        captured: dict = {}

        class FakeResp:
            status = 200
            headers = {"content-type": "application/json"}

            def read(self) -> bytes:
                return b'{"logs":[]}'

            def __enter__(self) -> FakeResp:
                return self

            def __exit__(self, *args: object) -> None:
                return None

        def fake_urlopen(req: object) -> FakeResp:
            captured["req"] = req
            return FakeResp()

        with patch("urllib.request.urlopen", fake_urlopen):
            body, nf = _post_logs(
                "https://auralogger.com",
                "my-token",
                "user-sec-xyz",
                [],
            )

        self.assertEqual(body, {"logs": []})
        self.assertFalse(nf)
        req = captured["req"]
        hdrs = {k.lower(): v for k, v in req.header_items()}
        self.assertEqual(hdrs.get("secret"), "user-sec-xyz")
        self.assertEqual(hdrs.get("user_secret"), "user-sec-xyz")
        self.assertIn("/api/my-token/logs", req.full_url)


class TestProjAuthFetch(unittest.TestCase):
    def test_fetch_no_auth_header(self) -> None:
        from auralogger.server.proj_auth import fetch_proj_auth_payload

        captured: dict = {}

        class FakeResp:
            status = 200
            headers = {"content-type": "application/json"}

            def read(self) -> bytes:
                return json.dumps(
                    {"project_id": "p1", "session": "s1", "styles": []}
                ).encode("utf8")

            def __enter__(self) -> FakeResp:
                return self

            def __exit__(self, *args: object) -> None:
                return None

        def fake_urlopen(req: object) -> FakeResp:
            captured["req"] = req
            return FakeResp()

        with patch("urllib.request.urlopen", fake_urlopen):
            out = fetch_proj_auth_payload("cipher")

        self.assertEqual(out.get("session"), "s1")
        req = captured["req"]
        hdrs = {k.lower(): v for k, v in req.header_items()}
        self.assertNotIn("secret", hdrs)
        self.assertIn("/proj_auth", req.full_url)


if __name__ == "__main__":
    unittest.main()
