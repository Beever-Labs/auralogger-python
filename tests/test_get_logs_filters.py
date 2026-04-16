"""Tests for get-logs filter normalization (Node parity)."""

from __future__ import annotations

import unittest

from auralogger.cli.get_logs_filters import (
    normalize_and_validate_filters,
    with_default_session_filter,
)
from auralogger.utils.parser import ParsedFilter


class TestGetLogsFilters(unittest.TestCase):
    def test_session_field_eq(self) -> None:
        out = normalize_and_validate_filters(
            [ParsedFilter(field="session", op=None, value=["abc"])]
        )
        self.assertEqual(out, [{"field": "session", "value": ["abc"]}])

    def test_with_default_session_prepends(self) -> None:
        base = normalize_and_validate_filters(
            [ParsedFilter(field="maxcount", op=None, value=10)]
        )
        merged = with_default_session_filter(base, "sess-from-env")
        self.assertEqual(
            merged,
            [
                {"field": "session", "value": ["sess-from-env"]},
                {"field": "maxcount", "value": 10},
            ],
        )

    def test_with_default_session_skips_if_explicit(self) -> None:
        base = normalize_and_validate_filters(
            [
                ParsedFilter(field="session", op=None, value=["user-pick"]),
            ]
        )
        merged = with_default_session_filter(base, "sess-from-env")
        self.assertEqual(
            merged,
            [{"field": "session", "value": ["user-pick"]}],
        )

    def test_with_default_session_no_env(self) -> None:
        base = normalize_and_validate_filters(
            [ParsedFilter(field="maxcount", op=None, value=5)]
        )
        self.assertEqual(with_default_session_filter(base, None), base)
        self.assertEqual(with_default_session_filter(base, ""), base)


if __name__ == "__main__":
    unittest.main()
