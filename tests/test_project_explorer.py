import importlib.util
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("project_explorer", PROJECT_ROOT / "scripts" / "publish_project_explorer.py")
project_explorer = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(project_explorer)


class ProjectExplorerTests(unittest.TestCase):
    def test_build_artifact_exposes_public_files_and_dbt_relationships(self):
        manifest = {
            "metadata": {"project_name": "south_alabama_tornado_watch", "dbt_version": "1.11.12"},
            "sources": {"source.south_alabama_tornado_watch.raw.ncei_tornado_events": {"package_name": "south_alabama_tornado_watch", "name": "ncei_tornado_events", "description": "Confirmed source", "columns": {}}},
            "nodes": {
                "model.south_alabama_tornado_watch.src_ncei__tornado_events": {"package_name": "south_alabama_tornado_watch", "resource_type": "model", "name": "src_ncei__tornado_events", "path": "src/src_ncei__tornado_events.sql", "original_file_path": "models/src/src_ncei__tornado_events.sql", "description": "Typed source", "columns": {}, "depends_on": {"nodes": ["source.south_alabama_tornado_watch.raw.ncei_tornado_events"]}},
                "test.south_alabama_tornado_watch.not_null_src": {"package_name": "south_alabama_tornado_watch", "resource_type": "test", "name": "not_null_src_ncei__tornado_events_event_id", "depends_on": {"nodes": ["model.south_alabama_tornado_watch.src_ncei__tornado_events"]}},
            },
        }
        catalog = {"nodes": {"model.south_alabama_tornado_watch.src_ncei__tornado_events": {"metadata": {"schema": "src", "name": "src_ncei__tornado_events"}}}}
        results = {"results": [{"unique_id": "model.south_alabama_tornado_watch.src_ncei__tornado_events", "status": "success"}, {"unique_id": "test.south_alabama_tornado_watch.not_null_src", "status": "pass"}]}
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "models/src/src_ncei__tornado_events.sql"
            source.parent.mkdir(parents=True)
            source.write_text("select 1 as event_id\n", encoding="utf-8")
            artifact = project_explorer.build_artifact(manifest, catalog, results, root)

        self.assertEqual(artifact["schemaVersion"], "1.0")
        self.assertEqual(artifact["summary"]["modelCount"], 1)
        self.assertEqual(artifact["summary"]["passingTestCount"], 1)
        self.assertEqual(artifact["files"][0]["path"], "models/src/src_ncei__tornado_events.sql")
        model = next(node for node in artifact["nodes"] if node["resourceType"] == "model")
        self.assertEqual(model["relation"], "src.src_ncei__tornado_events")
        self.assertEqual(model["tests"][0]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
