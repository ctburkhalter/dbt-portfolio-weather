"""Regression tests for source-value normalization used before dbt modeling."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "ingestion"))

from load_ncei_events import parse_cz_timezone_offset, parse_damage, parse_timestamp
from fetch_preliminary_tornado_reports import parse_timestamp as parse_lsr_timestamp
from refresh_recent_ncei import latest_filename


class NceiNormalizationTests(unittest.TestCase):
    def test_two_digit_historical_year_uses_1900s(self) -> None:
        # Default offset applies because no CZ_TIMEZONE is given (see the
        # offset-parsing tests below for the representative timezone codes).
        self.assertEqual(parse_timestamp("05-Apr-68 14:30:00"), "1968-04-05T14:30:00-06:00")

    def test_modern_two_digit_year_uses_2000s(self) -> None:
        self.assertEqual(parse_timestamp("05-Apr-07 14:30:00", "EST-5"), "2007-04-05T14:30:00-05:00")

    def test_invalid_timestamp_returns_none(self) -> None:
        self.assertIsNone(parse_timestamp("not a timestamp", "CST-6"))

    def test_timestamp_keeps_local_wall_clock_unshifted(self) -> None:
        # The offset is appended, not used to shift the parsed clock reading.
        for cz_timezone, expected_offset in (("CST-6", "-06:00"), ("EST-5", "-05:00"), ("MST-7", "-07:00")):
            with self.subTest(cz_timezone=cz_timezone):
                self.assertEqual(
                    parse_timestamp("26-MAR-23 17:15:00", cz_timezone),
                    f"2023-03-26T17:15:00{expected_offset}",
                )

    def test_damage_suffixes_and_unknown_values(self) -> None:
        self.assertEqual(parse_damage("1.5K"), 1500.0)
        self.assertEqual(parse_damage("2M"), 2_000_000.0)
        self.assertIsNone(parse_damage("UNK"))

    def test_damage_billion_suffix(self) -> None:
        # NCEI's baseline includes seven B-suffixed rows (Tuscaloosa 2011,
        # Moore OK 2013, and others); these parsed to None before this fix.
        self.assertEqual(parse_damage("1.50B"), 1_500_000_000.0)
        self.assertEqual(parse_damage("2.00B"), 2_000_000_000.0)

    def test_lsr_timestamp_normalizes_to_utc_with_offset(self) -> None:
        self.assertEqual(
            parse_lsr_timestamp("2026-04-01T01:46:00Z").isoformat(),
            "2026-04-01T01:46:00+00:00",
        )

    def test_lsr_compact_timestamp_normalizes(self) -> None:
        self.assertEqual(
            parse_lsr_timestamp("202604021535").isoformat(),
            "2026-04-02T15:35:00+00:00",
        )


class CzTimezoneOffsetTests(unittest.TestCase):
    def test_modern_explicit_offset_form(self) -> None:
        # The form NCEI uses from roughly the 2010s onward.
        self.assertEqual(parse_cz_timezone_offset("CST-6"), "-06:00")
        self.assertEqual(parse_cz_timezone_offset("EST-5"), "-05:00")
        self.assertEqual(parse_cz_timezone_offset("MST-7"), "-07:00")
        self.assertEqual(parse_cz_timezone_offset("PST-8"), "-08:00")

    def test_historical_bare_abbreviation_form(self) -> None:
        # Verified against a real 1955 NCEI file, which has no "-N" suffix.
        self.assertEqual(parse_cz_timezone_offset("CST"), "-06:00")
        self.assertEqual(parse_cz_timezone_offset("EST"), "-05:00")

    def test_daylight_labeled_bare_abbreviation_form(self) -> None:
        # A full pass over the committed 1950-2024 baseline found about 0.2%
        # of rows use a daylight-time-labeled bare abbreviation rather than
        # the zone's standard-time offset; these get their own correct offset
        # rather than falling through to the CST default.
        self.assertEqual(parse_cz_timezone_offset("CDT"), "-05:00")
        self.assertEqual(parse_cz_timezone_offset("EDT"), "-04:00")
        self.assertEqual(parse_cz_timezone_offset("MDT"), "-06:00")

    def test_missing_or_unrecognized_defaults_to_cst(self) -> None:
        self.assertEqual(parse_cz_timezone_offset(None), "-06:00")
        self.assertEqual(parse_cz_timezone_offset(""), "-06:00")
        self.assertEqual(parse_cz_timezone_offset("GARBAGE"), "-06:00")


class NceiFileDiscoveryTests(unittest.TestCase):
    def test_finds_newest_correction_for_a_published_year(self) -> None:
        index = (
            "StormEvents_details-ftp_v1.0_d2023_c20230815.csv.gz "
            "StormEvents_details-ftp_v1.0_d2023_c20260323.csv.gz "
            "StormEvents_details-ftp_v1.0_d2024_c20250110.csv.gz"
        )
        self.assertEqual(latest_filename(index, 2023), "StormEvents_details-ftp_v1.0_d2023_c20260323.csv.gz")

    def test_returns_none_for_a_year_not_yet_published(self) -> None:
        # Simulates the January window: the index lists 2024 and 2025 files
        # but nothing for 2026 yet.
        index = (
            "StormEvents_details-ftp_v1.0_d2024_c20250110.csv.gz "
            "StormEvents_details-ftp_v1.0_d2025_c20260102.csv.gz"
        )
        self.assertIsNone(latest_filename(index, 2026))


if __name__ == "__main__":
    unittest.main()
