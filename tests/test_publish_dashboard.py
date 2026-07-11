import importlib.util
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publish_dashboard", PROJECT_ROOT / "scripts" / "publish_dashboard.py")
publisher = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(publisher)


class DashboardPublisherTests(unittest.TestCase):
    def test_canonical_relation_requires_successful_contracted_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            results = root / "run_results.json"
            manifest.write_text(json.dumps({"nodes": {publisher.MODEL_ID: {"relation_name": '"db"."ci_marts"."fct_tornado_events"', "config": {"enabled": True}}}}))
            results.write_text(json.dumps({"results": [{"unique_id": publisher.MODEL_ID, "status": "success"}]}))
            self.assertEqual(publisher.canonical_relation(manifest, results), '"db"."ci_marts"."fct_tornado_events"')

    def test_v2_event_retains_native_id_and_adds_global_key(self):
        row = {column: None for column in publisher.EVENT_COLUMNS}
        row.update({
            "event_key": "ncei_storm_events:123", "event_id": "123",
            "occurred_at": datetime(2026, 4, 1, 14, 30), "occurred_at_utc_offset": "-05:00",
            "state": "AL", "is_alabama": True, "is_dixie_cohort": True,
            "is_tornado_cohort": False, "record_status": "confirmed",
            "source_system": "ncei_storm_events", "is_surveyed_track": False,
        })
        event = publisher.event_payload(row)
        self.assertEqual(event["eventKey"], "ncei_storm_events:123")
        self.assertEqual(event["eventId"], "123")
        self.assertEqual(event["regionIds"], ["alabama", "dixie"])
        self.assertEqual(event["occurredAt"], "2026-04-01T14:30:00-05:00")


if __name__ == "__main__":
    unittest.main()
