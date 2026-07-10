"""Regression tests for source-value normalization used before dbt modeling."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "ingestion"))

from load_ncei_events import parse_damage, parse_timestamp


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


if __name__ == "__main__":
    unittest.main()
