from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "skills/obsidian-memory/scripts/link_audit.py"
sys.path.insert(0, str(SCRIPT.parent))


class ReviewRegressionTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str = "") -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def config(self, **overrides: object) -> dict:
        config: dict = {
            "schema_version": 2,
            "base_id": "review",
            "scope": "project-memory",
            "index_path": "meta/root-index.md",
            "required_paths": [],
            "excluded_paths": [],
            "known_top_level_folders": ["meta", "wiki"],
            "rules_roots": [],
            "lifecycle_codes": ["HND"],
            "legacy_markers": [],
            "historical_source_patterns": [],
            "disallowed_lifecycle_codes": [],
            "forbidden_path_patterns": [],
            "index_section_rules": [],
            "url": {"classes": []},
        }
        config.update(overrides)
        return config

    def run_json(self, root: Path) -> dict:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), str(root), "--json"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        return json.loads(completed.stdout)

    def write_config(self, root: Path, config: dict) -> None:
        self.write(root, "obsidian-memory.config.json", json.dumps(config))

    def test_custom_todo_file_is_scanned_for_disallowed_active_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(
                root,
                "meta/root-index.md",
                "- [[wiki/todo_demo-01]]\n- [[docs_agent/record]]\n",
            )
            self.write(
                root,
                "wiki/todo_demo-01.md",
                "- [[docs_agent/record|HND-0042 waiting]]\n",
            )
            self.write(root, "docs_agent/record.md", "# Record\n")
            self.write_config(
                root,
                self.config(
                    known_top_level_folders=["meta", "wiki", "docs_agent"],
                    disallowed_lifecycle_codes=[
                        {"code": "HND", "path_prefixes": ["docs_agent"]}
                    ],
                ),
            )

            report = self.run_json(root)
            matches = [
                item
                for item in report["STRICT_PROBLEMS"]
                if item["kind"] == "DISALLOWED_LIFECYCLE_CODE"
            ]
            rendered = json.dumps(matches)

            self.assertIn("wiki/todo_demo-01.md", rendered)
            self.assertIn("HND-0042", rendered)

    def test_forbidden_routes_ignore_link_aliases_unrelated_prose_and_yaml_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "meta/root-index.md", "- [[wiki/notes]]\n")
            self.write(
                root,
                "wiki/notes.md",
                "---\nroute: legacy/routes/yaml.md\n---\n"
                "Ordinary prose mentions legacy/routes/prose.md but is not a route.\n"
                "[[safe/page|legacy/routes/wiki-alias.md]]\n"
                "[legacy/routes/markdown-alias.md](safe/page.md)\n",
            )
            self.write_config(
                root,
                self.config(
                    forbidden_path_patterns=["legacy/routes/[A-Za-z0-9_.-]+"]
                ),
            )

            report = self.run_json(root)
            matches = [
                item
                for item in report["STRICT_PROBLEMS"]
                if item["kind"] == "FORBIDDEN_PATH_PATTERN"
            ]

            self.assertEqual([], matches)

    def test_forbidden_routes_scan_parsed_link_targets_and_route_like_plain_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "meta/root-index.md", "- [[wiki/notes]]\n")
            self.write(
                root,
                "wiki/notes.md",
                "[[legacy/routes/wiki-target|safe alias]]\n"
                "[safe alias](legacy/routes/markdown-target.md)\n"
                "Route: legacy/routes/plain.md\n",
            )
            self.write_config(
                root,
                self.config(
                    forbidden_path_patterns=["legacy/routes/[A-Za-z0-9_.-]+"]
                ),
            )

            report = self.run_json(root)
            targets = {
                item["message"]
                for item in report["STRICT_PROBLEMS"]
                if item["kind"] == "FORBIDDEN_PATH_PATTERN"
            }

            self.assertEqual(
                {
                    "Line 1: forbidden route-like reference.",
                    "Line 2: forbidden route-like reference.",
                    "Line 3: forbidden route-like reference.",
                },
                targets,
            )


if __name__ == "__main__":
    unittest.main()
