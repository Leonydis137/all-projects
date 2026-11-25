"""Regression tests for the repository's catalog-driven project runner."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "projects.sh"


class ProjectRunnerTests(unittest.TestCase):
    def run_catalog(self, projects: list[dict], command: str = "test", target: str = "all"):
        with tempfile.TemporaryDirectory(prefix=".project-runner-test-", dir=ROOT) as temporary:
            catalog = Path(temporary) / "projects.json"
            catalog.write_text(json.dumps({"projects": projects}), encoding="utf-8")
            environment = os.environ.copy()
            environment["PROJECTS_CATALOG"] = str(catalog)
            return subprocess.run(
                ["bash", str(RUNNER), command, target],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

    def make_project(self, base: Path, name: str, with_index: bool = True) -> dict:
        directory = base / name
        directory.mkdir()
        if with_index:
            (directory / "index.html").write_text("<!doctype html><title>Test</title>", encoding="utf-8")
        return {"path": name, "kind": "static", "dir": directory.relative_to(ROOT).as_posix()}

    def test_runs_multiple_projects_after_changing_working_directory(self):
        with tempfile.TemporaryDirectory(prefix=".project-runner-fixture-", dir=ROOT) as temporary:
            base = Path(temporary)
            projects = [
                self.make_project(base, "first"),
                self.make_project(base, "second"),
            ]
            result = self.run_catalog(projects)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OK: static entry point exists", result.stdout)
        self.assertIn("==> test first (static)", result.stdout)
        self.assertIn("==> test second (static)", result.stdout)

    def test_continues_after_failure_and_reports_aggregate_status(self):
        with tempfile.TemporaryDirectory(prefix=".project-runner-fixture-", dir=ROOT) as temporary:
            base = Path(temporary)
            projects = [
                self.make_project(base, "missing-entry", with_index=False),
                self.make_project(base, "valid-entry"),
            ]
            result = self.run_catalog(projects)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAILED: missing-entry", result.stderr)
        self.assertIn("==> test valid-entry (static)", result.stdout)
        self.assertIn("OK: static entry point exists", result.stdout)
        self.assertIn("1 project operation(s) failed.", result.stderr)

    def test_rejects_catalog_directory_symlink_escape(self):
        with tempfile.TemporaryDirectory(prefix=".project-runner-fixture-", dir=ROOT) as temporary:
            base = Path(temporary)
            outside = Path(tempfile.mkdtemp(prefix="project-runner-outside-"))
            try:
                link = base / "outside-link"
                link.symlink_to(outside, target_is_directory=True)
                project = {
                    "path": "outside",
                    "kind": "static",
                    "dir": link.relative_to(ROOT).as_posix(),
                }
                result = self.run_catalog([project], command="list")
            finally:
                link.unlink(missing_ok=True)
                outside.rmdir()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("escapes repository root", result.stderr)

    def test_unknown_project_target_fails_without_running_any_project(self):
        with tempfile.TemporaryDirectory(prefix=".project-runner-fixture-", dir=ROOT) as temporary:
            project = self.make_project(Path(temporary), "known")
            result = self.run_catalog([project], target="not-in-catalog")
        self.assertEqual(result.returncode, 2)
        self.assertIn("no catalog entry matches 'not-in-catalog'", result.stderr)


if __name__ == "__main__":
    unittest.main()
