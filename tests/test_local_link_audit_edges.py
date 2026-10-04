from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "skills/obsidian-memory/scripts/link_audit.py"
sys.path.insert(0, str(SCRIPT.parent))


class LinkAuditEdgeTests(unittest.TestCase):
    def run_audit(self, root: Path) -> dict[str, object]:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), str(root), "--json"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_normal_wiki_alias_outside_table_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "index.md").write_text("- [[index]]\n- [[Page|Alias]]\n", encoding="utf-8")
            (root / "Page.md").write_text("# Page\n", encoding="utf-8")

            report = self.run_audit(root)

            self.assertEqual(report["BROKEN_WIKI_LINKS"], [])
            self.assertEqual(report["STRICT_PROBLEM_COUNT"], 0)

    def test_escaped_wiki_alias_inside_table_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "index.md").write_text(
                "- [[index]]\n- [[Page]]\n- [[Table]]\n", encoding="utf-8"
            )
            (root / "Page.md").write_text("# Page\n", encoding="utf-8")
            (root / "Table.md").write_text(
                "| Link |\n| --- |\n| [[Page\\|Alias]] |\n", encoding="utf-8"
            )

            report = self.run_audit(root)

            self.assertEqual(report["BROKEN_WIKI_LINKS"], [])
            self.assertEqual(report["UNESCAPED_WIKI_ALIASES_IN_TABLE"], [])
            self.assertEqual(report["STRICT_PROBLEM_COUNT"], 0)

    def test_unescaped_wiki_alias_inside_table_is_strict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "index.md").write_text(
                "- [[index]]\n- [[Page]]\n- [[Table]]\n", encoding="utf-8"
            )
            (root / "Page.md").write_text("# Page\n", encoding="utf-8")
            (root / "Table.md").write_text(
                "| Link |\n| --- |\n| [[Page|Alias]] |\n", encoding="utf-8"
            )

            report = self.run_audit(root)
            kinds = {item["kind"] for item in report["STRICT_PROBLEMS"]}

            self.assertIn("UNESCAPED_WIKI_ALIAS_IN_TABLE", kinds)
            self.assertEqual(report["BROKEN_WIKI_LINKS"], [])

    def test_escaped_image_embed_size_inside_table_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "index.md").write_text("- [[index]]\n- [[Table]]\n", encoding="utf-8")
            (root / "Table.md").write_text(
                "| Image |\n| --- |\n| ![[image.png\\|200]] |\n", encoding="utf-8"
            )
            (root / "image.png").write_bytes(b"not-a-real-image")

            report = self.run_audit(root)

            self.assertEqual(report["BROKEN_WIKI_EMBEDS"], [])
            self.assertEqual(report["UNESCAPED_WIKI_ALIASES_IN_TABLE"], [])
            self.assertEqual(report["STRICT_PROBLEM_COUNT"], 0)
    def test_missing_active_entry_still_reports_disallowed_lifecycle_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "index.md").write_text(
                "- [[docs_agent/HND-9000]]\n", encoding="utf-8"
            )
            config = {
                "schema_version": 2,
                "base_id": "edge",
                "scope": "project-memory",
                "index_path": "index.md",
                "required_paths": [],
                "excluded_paths": [],
                "known_top_level_folders": [],
                "rules_roots": [],
                "lifecycle_codes": ["HND"],
                "legacy_markers": [],
                "historical_source_patterns": [],
                "disallowed_lifecycle_codes": [
                    {"code": "HND", "path_prefixes": ["docs_agent"]}
                ],
                "forbidden_path_patterns": [],
                "index_section_rules": [],
                "url": {"classes": []},
            }
            (root / "obsidian-memory.config.json").write_text(
                json.dumps(config), encoding="utf-8"
            )

            completed = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            report = json.loads(completed.stdout)
            rendered = json.dumps(report["STRICT_PROBLEMS"])

            self.assertIn("DISALLOWED_LIFECYCLE_CODE", rendered)
            self.assertIn("HND-9000", rendered)


if __name__ == "__main__":
    unittest.main()
