"""Publish a compact, inspectable dbt project artifact for the portfolio UI."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOTS = ("ingestion", "macros", "models", "seeds", "tests")
PUBLIC_FILES = {
    ".github/workflows/refresh.yml",
    ".github/workflows/ci.yml",
    "dbt_project.yml",
    "profiles.yml",
    "scripts/publish_dashboard.py",
    "scripts/publish_project_explorer.py",
    "docs/METHODOLOGY.md",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_output(*args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=PROJECT_ROOT, text=True).strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def repository_url() -> str:
    configured = os.environ.get("GITHUB_REPOSITORY")
    if configured:
        return f"https://github.com/{configured}"
    remote = git_output("config", "--get", "remote.origin.url")
    if not remote:
        return "https://github.com/ctburkhalter/dbt-portfolio-weather"
    if remote.startswith("git@github.com:"):
        return f"https://github.com/{remote.removeprefix('git@github.com:').removesuffix('.git')}"
    return remote.removesuffix(".git")


def language_for(path: str) -> str:
    return {".py": "python", ".sql": "sql", ".yml": "yaml", ".yaml": "yaml", ".md": "markdown"}.get(Path(path).suffix, "text")


def category_for(path: str) -> str:
    for category in ("staging", "intermediate", "marts"):
        if path.startswith(f"models/{category}/"):
            return category
    if path.startswith("seeds/"):
        return "seeds"
    if path.startswith("ingestion/"):
        return "ingestion"
    if path.startswith("tests/"):
        return "tests"
    if path.startswith("macros/"):
        return "macros"
    return "config"


def public_paths(root: Path) -> list[Path]:
    paths = [root / path for path in PUBLIC_FILES]
    for directory in PUBLIC_ROOTS:
        paths.extend(path for path in (root / directory).rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    return sorted(path for path in paths if path.exists())


def result_statuses(run_results: dict[str, Any]) -> dict[str, str]:
    return {result["unique_id"]: result["status"] for result in run_results.get("results", []) if "unique_id" in result}


def catalog_entry_for(catalog: dict[str, Any], unique_id: str) -> dict[str, Any]:
    return catalog.get("nodes", {}).get(unique_id) or catalog.get("sources", {}).get(unique_id, {})


def relation_for(catalog: dict[str, Any], unique_id: str) -> str | None:
    metadata = catalog_entry_for(catalog, unique_id).get("metadata", {})
    if not metadata.get("schema") or not metadata.get("name"):
        return None
    return f"{metadata['schema']}.{metadata['name']}"


def project_node(unique_id: str, node: dict[str, Any], catalog: dict[str, Any], statuses: dict[str, str], resource_type: str) -> dict[str, Any]:
    # Column names and types come from catalog.json: the actual introspected
    # columns of the built table or view, always complete regardless of
    # models.yml documentation coverage. Descriptions come from
    # manifest.json, which only carries a column entry when a human typed
    # one into models.yml (even a bare `tests:`-only entry, no description
    # required). Sourcing columns from the manifest alone undercounted every
    # model down to whatever fraction of its real columns happened to have a
    # YAML entry (dim_geography showed 0 of its 5 real columns before this
    # fix). Manifest column keys are matched by name against catalog column
    # names; dbt lowercases unquoted identifiers in both, so this matches
    # reliably for this project's unquoted lowercase columns.
    catalog_columns = catalog_entry_for(catalog, unique_id).get("columns", {})
    manifest_columns = node.get("columns", {})
    columns = [
        {
            "name": catalog_column["name"],
            "description": manifest_columns.get(catalog_column["name"], {}).get("description", ""),
            "dataType": catalog_column.get("type"),
        }
        for catalog_column in sorted(catalog_columns.values(), key=lambda column: column.get("index", 0))
    ]
    return {
        "id": unique_id,
        "name": node["name"],
        "resourceType": resource_type,
        "layer": resource_type if resource_type in {"source", "seed", "exposure"} else node.get("path", "").split("/", 1)[0] or "model",
        "path": node.get("original_file_path", ""),
        "description": node.get("description", ""),
        "relation": relation_for(catalog, unique_id),
        "columns": columns,
        "upstream": list(node.get("depends_on", {}).get("nodes", [])) if resource_type != "source" else [],
        "downstream": [],
        "tests": [],
        "buildStatus": statuses.get(unique_id),
        "materialization": node.get("config", {}).get("materialized") if resource_type in {"model", "seed"} else None,
        "contractEnforced": bool(node.get("contract", {}).get("enforced") or node.get("config", {}).get("contract", {}).get("enforced")),
        "owner": node.get("owner") or node.get("config", {}).get("meta", {}).get("owner"),
        "maturity": node.get("maturity") or node.get("config", {}).get("meta", {}).get("maturity"),
        "meta": node.get("config", {}).get("meta", {}),
    }


def build_artifact(manifest: dict[str, Any], catalog: dict[str, Any], run_results: dict[str, Any], root: Path = PROJECT_ROOT) -> dict[str, Any]:
    statuses = result_statuses(run_results)
    project_name = manifest["metadata"]["project_name"]
    nodes: dict[str, dict[str, Any]] = {}
    for unique_id, node in manifest.get("sources", {}).items():
        if node.get("package_name") == project_name:
            nodes[unique_id] = project_node(unique_id, node, catalog, statuses, "source")
    for unique_id, node in manifest.get("nodes", {}).items():
        if node.get("package_name") == project_name and node.get("resource_type") in {"model", "seed"}:
            nodes[unique_id] = project_node(unique_id, node, catalog, statuses, node["resource_type"])
    for unique_id, node in manifest.get("exposures", {}).items():
        if node.get("package_name") == project_name:
            nodes[unique_id] = project_node(unique_id, node, catalog, statuses, "exposure")

    for node in nodes.values():
        node["upstream"] = [unique_id for unique_id in node["upstream"] if unique_id in nodes]
        for upstream_id in node["upstream"]:
            nodes[upstream_id]["downstream"].append(node["id"])

    for unique_id, test in manifest.get("nodes", {}).items():
        if test.get("package_name") != project_name or test.get("resource_type") != "test":
            continue
        summary = {"name": test.get("name", unique_id), "status": statuses.get(unique_id, "not_run")}
        for dependency in test.get("depends_on", {}).get("nodes", []):
            if dependency in nodes:
                nodes[dependency]["tests"].append(summary)

    commit_sha = os.environ.get("GITHUB_SHA") or git_output("rev-parse", "HEAD") or "unknown"
    repo_url = repository_url()
    files = []
    for path in public_paths(root):
        relative_path = path.relative_to(root).as_posix()
        files.append({
            "path": relative_path,
            "category": category_for(relative_path),
            "language": language_for(relative_path),
            "content": path.read_text(encoding="utf-8"),
            "githubUrl": f"{repo_url}/blob/{commit_sha}/{relative_path}",
            "relatedNodeIds": sorted(unique_id for unique_id, node in nodes.items() if node["path"] == relative_path),
        })

    test_results = [status for unique_id, status in statuses.items() if unique_id.startswith("test.")]
    model_results = [status for unique_id, status in statuses.items() if unique_id.startswith("model.")]
    undocumented_public = [
        f"{node['name']}.{column['name']}"
        for node in nodes.values()
        if node["resourceType"] == "model" and node["layer"] == "marts"
        for column in node["columns"]
        if not column["description"]
    ]
    if undocumented_public:
        raise ValueError(f"Public mart columns require descriptions: {', '.join(undocumented_public)}")
    return {
        "schemaVersion": "2.0",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "project": {"name": project_name, "dbtVersion": manifest["metadata"].get("dbt_version", "unknown"), "commitSha": commit_sha, "repositoryUrl": repo_url, "docsPath": "dbt-docs/index.html"},
        "summary": {
            "modelCount": sum(node["resourceType"] == "model" for node in nodes.values()),
            "sourceCount": sum(node["resourceType"] == "source" for node in nodes.values()),
            "seedCount": sum(node["resourceType"] == "seed" for node in nodes.values()),
            "exposureCount": sum(node["resourceType"] == "exposure" for node in nodes.values()),
            "contractedModelCount": sum(node["resourceType"] == "model" and node["contractEnforced"] for node in nodes.values()),
            "documentedColumnCount": sum(bool(column["description"]) for node in nodes.values() for column in node["columns"]),
            "columnCount": sum(len(node["columns"]) for node in nodes.values()),
            "testCount": len(test_results),
            "passingTestCount": sum(status == "pass" for status in test_results),
            "successfulModelCount": sum(status == "success" for status in model_results),
        },
        "files": files,
        "nodes": sorted(nodes.values(), key=lambda node: (node["layer"], node["name"])),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="public/data/v2/dbt-project.json")
    parser.add_argument("--manifest", default="target/manifest.json")
    parser.add_argument("--catalog", default="target/catalog.json")
    parser.add_argument("--run-results")
    args = parser.parse_args()
    run_results_path = Path(args.run_results) if args.run_results else Path("target/build_run_results.json")
    if not run_results_path.exists():
        run_results_path = Path("target/run_results.json")
    artifact = build_artifact(read_json(Path(args.manifest)), read_json(Path(args.catalog)), read_json(run_results_path))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, separators=(",", ":")), encoding="utf-8")
    print(f"Published dbt explorer with {artifact['summary']['modelCount']} models, {artifact['summary']['testCount']} tests, and {len(artifact['files'])} files")


if __name__ == "__main__":
    main()
