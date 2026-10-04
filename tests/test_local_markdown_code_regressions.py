from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "skills/obsidian-memory/scripts/link_audit.py"
sys.path.insert(0, str(SCRIPT.parent))


class MarkdownCodeRegressionTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def run_forbidden_targets(self, body: str) -> set[str]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "index.md", "- [[notes]]\n")
            self.write(root, "notes.md", body)
            config = {
                "schema_version": 2,
                "index_path": "index.md",
                "required_paths": [],
                "excluded_paths": [],
                "known_top_level_folders": [],
                "rules_roots": [],
                "lifecycle_codes": [],
                "legacy_markers": [],
                "historical_source_patterns": [],
                "disallowed_lifecycle_codes": [],
                "forbidden_path_patterns": ["legacy/routes/[A-Za-z0-9_.-]+"],
                "index_section_rules": [],
                "url": {"classes": []},
            }
            self.write(root, "obsidian-memory.config.json", json.dumps(config))
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            report = json.loads(completed.stdout)
            return {
                item["source"] + " -> " + item["message"]
                for item in report["STRICT_PROBLEMS"]
                if item["kind"] == "FORBIDDEN_PATH_PATTERN"
            }

    def test_tilde_fence_is_ignored_and_route_after_fence_is_active(self) -> None:
        targets = self.run_forbidden_targets(
            "~~~text\n"
            "Route: legacy/routes/tilde-fenced.md\n"
            "~~~\n"
            "Route: legacy/routes/active-after-tilde.md\n"
        )

        self.assertEqual({"notes.md -> Line 4: forbidden route-like reference."}, targets)

    def test_variable_backtick_inline_and_fence_are_ignored_but_link_remains_active(self) -> None:
        targets = self.run_forbidden_targets(
            "``legacy/routes/double-inline.md``\n"
            "````markdown\n"
            "Route: legacy/routes/four-fenced.md\n"
            "````\n"
            "[active](legacy/routes/active-link.md)\n"
        )

        self.assertEqual({"notes.md -> Line 5: forbidden route-like reference."}, targets)


if __name__ == "__main__":
    unittest.main()
