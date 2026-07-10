"""Regression tests for source-value normalization used before dbt modeling."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "ingestion"))

from load_ncei_events import parse_damage, parse_timestamp
from fetch_preliminary_tornado_reports import parse_timestamp as parse_lsr_timestamp


class NceiNormalizationTests(unittest.TestCase):
    def test_two_digit_historical_year_uses_1900s(self) -> None:
        self.assertEqual(parse_timestamp("05-Apr-68 14:30:00"), "1968-04-05T14:30:00")

    def test_modern_two_digit_year_uses_2000s(self) -> None:
        self.assertEqual(parse_timestamp("05-Apr-07 14:30:00"), "2007-04-05T14:30:00")

    def test_invalid_timestamp_returns_none(self) -> None:
        self.assertIsNone(parse_timestamp("not a timestamp"))

    def test_damage_suffixes_and_unknown_values(self) -> None:
        self.assertEqual(parse_damage("1.5K"), 1500.0)
        self.assertEqual(parse_damage("2M"), 2_000_000.0)
        self.assertIsNone(parse_damage("UNK"))

    def test_lsr_timestamp_normalizes_to_utc_naive(self) -> None:
        self.assertEqual(
            parse_lsr_timestamp("2026-04-01T01:46:00Z").isoformat(),
            "2026-04-01T01:46:00",
        )

    def test_lsr_compact_timestamp_normalizes(self) -> None:
        self.assertEqual(
            parse_lsr_timestamp("202604021535").isoformat(),
            "2026-04-02T15:35:00",
        )


if __name__ == "__main__":
    unittest.main()
