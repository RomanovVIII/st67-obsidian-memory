from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "skills/obsidian-memory/scripts/link_audit.py"
sys.path.insert(0, str(SCRIPT.parent))


class LinkAuditTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str = "") -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_config(self, root: Path, config: dict) -> None:
        self.write(
            root,
            "obsidian-memory.config.json",
            json.dumps(config, ensure_ascii=False, indent=2),
        )

    def run_audit(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(root), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def run_json(self, root: Path, *args: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        completed = self.run_audit(root, *args, "--json")
        report = json.loads(completed.stdout) if completed.stdout else {}
        return completed, report

    def kinds(self, report: dict, section: str = "STRICT_PROBLEMS") -> list[str]:
        return [item["kind"] for item in report.get(section, [])]

    def tree_state(self, root: Path) -> dict[str, str]:
        state: dict[str, str] = {}
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
            relative = path.relative_to(root).as_posix()
            if path.is_dir():
                state[f"dir:{relative}"] = ""
            else:
                state[f"file:{relative}"] = hashlib.sha256(path.read_bytes()).hexdigest()
        return state

    def v2_config(self, **overrides: object) -> dict:
        config: dict = {
            "schema_version": 2,
            "base_id": "test-vault",
            "scope": "project-memory",
            "index_path": "index.md",
            "required_paths": [],
            "excluded_paths": [],
            "known_top_level_folders": [],
            "rules_roots": [],
            "lifecycle_codes": ["TODO", "PLN", "HND"],
            "legacy_markers": [],
            "historical_source_patterns": [],
            "disallowed_lifecycle_codes": [],
            "forbidden_path_patterns": [],
            "index_section_rules": [],
            "url": {"timeout_seconds": 1, "workers": 1, "classes": []},
        }
        config.update(overrides)
        return config

    def test_v1_config_remains_compatible_and_index_override_wins(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "index.md", "# Current\n\n- [[note]]\n")
            self.write(root, "legacy-index.md", "# Legacy\n")
            self.write(root, "note.md", "# Note\n")
            self.write(root, "excluded/ignored.md", "[[missing]]\n")
            self.write_config(
                root,
                {
                    "schema_version": 1,
                    "index": "legacy-index.md",
                    "required_paths": ["note.md"],
                    "excluded_folders": ["excluded"],
                    "known_top_level_folders": ["excluded"],
                    "rules_roots": [],
                    "lifecycle_codes": [],
                    "legacy_markers": [],
                    "historical_source_patterns": [],
                    "url": {"classes": []},
                },
            )

            completed, report = self.run_json(root, "--index", "index.md")

            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertNotIn("BROKEN_WIKI_LINK", self.kinds(report))
            self.assertNotIn("note.md", report["MISSING_FROM_INDEX"])

    def test_schema_v2_accepts_all_supported_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "index.md", "# Index\n\n- [[index]]\n")
            self.write_config(root, self.v2_config(required_paths=["index.md"]))

            completed, report = self.run_json(root)

            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual(0, report["STRICT_PROBLEM_COUNT"])

    def test_schema_v2_rejects_unknown_keys_and_invalid_shapes(self) -> None:
        invalid_configs = [
            self.v2_config(unexpected=True),
            self.v2_config(base_id=7),
            self.v2_config(scope=[]),
            self.v2_config(disallowed_lifecycle_codes=[{"code": "HND", "path_prefixes": [], "extra": 1}]),
            self.v2_config(index_section_rules=[{"heading": "Plans", "path_prefixes": [], "lifecycle_codes": [], "extra": 1}]),
            self.v2_config(url={"classes": [], "unexpected": True}),
        ]
        for config in invalid_configs:
            with self.subTest(config=config), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self.write(root, "index.md", "# Index\n")
                self.write_config(root, config)

                completed = self.run_audit(root)

                self.assertEqual(2, completed.returncode)
                self.assertIn("invalid config", completed.stderr)

    def test_schema_v2_rejects_path_traversal_in_every_path_field(self) -> None:
        invalid_overrides = [
            {"index_path": "../index.md"},
            {"required_paths": ["../required"]},
            {"excluded_paths": ["../excluded"]},
            {"known_top_level_folders": ["../known"]},
            {"rules_roots": ["../rules"]},
            {"disallowed_lifecycle_codes": [{"code": "HND", "path_prefixes": ["../local"]}]},
            {"index_section_rules": [{"heading": "Plans", "path_prefixes": ["../plans"], "lifecycle_codes": []}]},
        ]
        for overrides in invalid_overrides:
            with self.subTest(overrides=overrides), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self.write(root, "index.md", "# Index\n")
                self.write_config(root, self.v2_config(**overrides))

                completed = self.run_audit(root)

                self.assertEqual(2, completed.returncode)
                self.assertIn("must stay inside", completed.stderr)

    def test_source_relative_wiki_link_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "index.md", "- [[folder/source]]\n- [[folder/target]]\n")
            self.write(root, "folder/source.md", "[[target]]\n")
            self.write(root, "folder/target.md", "# Target\n")

            _, report = self.run_json(root)

            self.assertNotIn("BROKEN_WIKI_LINK", self.kinds(report))

    def test_unique_case_insensitive_basename_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "index.md", "- [[source]]\n- [[folder/Note]]\n")
            self.write(root, "source.md", "[[NOTE]]\n")
            self.write(root, "folder/Note.md", "# Note\n")

            _, report = self.run_json(root)

            self.assertNotIn("BROKEN_WIKI_LINK", self.kinds(report))

    def test_ambiguous_wiki_link_is_strict_and_candidates_are_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "index.md", "- [[source]]\n- [[a/Note]]\n- [[b/note]]\n")
            self.write(root, "source.md", "[[note]]\n")
            self.write(root, "b/note.md", "# B\n")
            self.write(root, "a/Note.md", "# A\n")

            _, report = self.run_json(root)

            ambiguous = [item for item in report["STRICT_PROBLEMS"] if item["kind"] == "AMBIGUOUS_WIKI_LINK"]
            self.assertEqual(1, len(ambiguous))
            self.assertIn("Line", ambiguous[0]["message"])
            self.assertEqual(1, len(report["DUPLICATE_MANAGED_FILENAMES"]))

    def test_explicit_root_relative_link_wins_despite_duplicate_basenames(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "index.md", "- [[source]]\n- [[a/note]]\n- [[b/note]]\n")
            self.write(root, "source.md", "[[a/note]]\n")
            self.write(root, "a/note.md", "# A\n")
            self.write(root, "b/note.md", "# B\n")

            _, report = self.run_json(root)

            self.assertNotIn("AMBIGUOUS_WIKI_LINK", self.kinds(report))
            self.assertNotIn("BROKEN_WIKI_LINK", self.kinds(report))

    def test_duplicate_managed_filenames_within_primary_root_are_strict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "index.md", "- [[a/Topic]]\n- [[b/topic]]\n")
            self.write(root, "a/Topic.md", "# A\n")
            self.write(root, "b/topic.md", "# B\n")

            _, report = self.run_json(root)

            self.assertIn("DUPLICATE_MANAGED_FILENAME", self.kinds(report))

    def test_compare_root_detects_duplicate_filenames_without_cross_root_link_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "primary"
            compare = base / "compare"
            self.write(root, "index.md", "- [[local]]\n")
            self.write(root, "local.md", "[[remote-only]]\n")
            self.write(compare, "nested/LOCAL.md", "# Duplicate\n")
            self.write(compare, "remote-only.md", "# Must not resolve primary links\n")

            _, report = self.run_json(root, "--compare-root", str(compare))

            self.assertIn("DUPLICATE_MANAGED_FILENAME", self.kinds(report))
            self.assertIn("BROKEN_WIKI_LINK", self.kinds(report))

    def test_obsidian_files_are_excluded_only_from_filename_uniqueness(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "index.md", "- [[note]]\n")
            self.write(root, "note.md", "# Managed\n")
            self.write(root, ".obsidian/plugins/example/note.md", "# Tool owned\n")

            _, report = self.run_json(root)

            self.assertNotIn("DUPLICATE_MANAGED_FILENAME", self.kinds(report))

    def test_index_heading_rules_report_mismatch_missing_heading_and_duplicate_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(
                root,
                "index.md",
                "# Plans\n\n- [[wiki/todo/TODO-0001]]\n- [[wiki/todo/TODO-0001]]\n\n"
                "# Todos\n\n- [[wiki/plans/PLN-0001]]\n",
            )
            self.write(root, "wiki/todo/TODO-0001.md", "# Todo\n")
            self.write(root, "wiki/plans/PLN-0001.md", "# Plan\n")
            self.write_config(
                root,
                self.v2_config(
                    index_section_rules=[
                        {"heading": "Plans", "path_prefixes": ["wiki/plans"], "lifecycle_codes": ["PLN"]},
                        {"heading": "Todos", "path_prefixes": ["wiki/todo"], "lifecycle_codes": ["TODO"]},
                        {"heading": "Research", "path_prefixes": ["wiki/research"], "lifecycle_codes": []},
                    ]
                ),
            )

            _, report = self.run_json(root)
            kinds = self.kinds(report)

            self.assertIn("INDEX_SECTION_MISMATCH", kinds)
            self.assertIn("MISSING_INDEX_SECTION", kinds)
            self.assertIn("DUPLICATE_INDEX_ENTRY", kinds)

    def test_disallowed_lifecycle_code_is_scoped_to_configured_paths_and_active_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(
                root,
                "index.md",
                "- [[docs_agent/HND-0001]]\n- [[wiki/HND-0002]]\n- [[wiki/todo]]\n",
            )
            self.write(root, "docs_agent/HND-0001.md", "# Local handoff\n")
            self.write(root, "docs_agent/record.md", "# Record\n")
            self.write(root, "wiki/HND-0002.md", "# Allowed elsewhere\n")
            self.write(root, "wiki/todo.md", "- [[docs_agent/record|HND-0003 waiting]]\n\nHND-0009 prose outside prefix\n")
            self.write_config(
                root,
                self.v2_config(
                    disallowed_lifecycle_codes=[
                        {"code": "HND", "path_prefixes": ["docs_agent"]}
                    ]
                ),
            )

            _, report = self.run_json(root)
            matches = [item for item in report["STRICT_PROBLEMS"] if item["kind"] == "DISALLOWED_LIFECYCLE_CODE"]
            rendered = json.dumps(matches, ensure_ascii=False)

            self.assertIn("HND-0001", rendered)
            self.assertIn("HND-0003", rendered)
            self.assertNotIn("HND-0002", rendered)
            self.assertNotIn("HND-0009", rendered)

    def test_forbidden_routes_are_strict_when_active_advisory_when_historical_and_ignore_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "index.md", "- [[active]]\n- [[archive/old]]\n")
            self.write(
                root,
                "active.md",
                "[legacy](legacy/routes/linked.md)\n"
                "Plain route: legacy/routes/plain.md\n"
                "`legacy/routes/inline.md`\n"
                "```text\nlegacy/routes/fenced.md\n```\n",
            )
            self.write(root, "archive/old.md", "Historical route: legacy/routes/history.md\n")
            self.write_config(
                root,
                self.v2_config(
                    historical_source_patterns=["^archive/"],
                    forbidden_path_patterns=["legacy/routes/[A-Za-z0-9_.-]+"],
                ),
            )

            _, report = self.run_json(root)
            strict = [item for item in report["STRICT_PROBLEMS"] if item["kind"] == "FORBIDDEN_PATH_PATTERN"]
            advisory = [item for item in report["ADVISORY_FINDINGS"] if item["kind"] == "FORBIDDEN_PATH_PATTERN_HISTORICAL"]
            rendered = json.dumps(strict + advisory, ensure_ascii=False)

            self.assertEqual(2, len(strict))
            self.assertEqual(1, len(advisory))
            self.assertNotIn("inline", rendered)
            self.assertNotIn("fenced", rendered)

    def test_markdown_attachments_resolve_relative_to_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "index.md", "- [[notes/page]]\n")
            self.write(root, "assets/picture.png", "image")
            self.write(
                root,
                "notes/page.md",
                "![present](../assets/picture.png)\n![missing](../assets/missing.png)\n",
            )

            _, report = self.run_json(root)

            self.assertEqual(
                ["notes/page.md -> BROKEN_MARKDOWN_ATTACHMENT_LINE_2"],
                report["BROKEN_MARKDOWN_ATTACHMENTS"],
            )

    def test_default_and_compare_root_audits_preserve_tree_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "primary"
            compare = base / "compare"
            self.write(root, "index.md", "- [[note]]\n")
            self.write(root, "note.md", "# Note\n")
            self.write(compare, "other.md", "# Other\n")
            before_primary = self.tree_state(root)
            before_compare = self.tree_state(compare)

            first = self.run_audit(root)
            second = self.run_audit(root, "--compare-root", str(compare))

            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual(0, second.returncode, second.stderr)
            self.assertEqual(before_primary, self.tree_state(root))
            self.assertEqual(before_compare, self.tree_state(compare))

    def test_json_out_is_the_only_write_opt_in_and_is_confined_to_primary_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "primary"
            outside = base / "outside.json"
            self.write(root, "index.md", "- [[index]]\n")

            rejected = self.run_audit(root, "--json-out", str(outside))
            accepted = self.run_audit(root, "--json-out", "reports/audit.json")

            self.assertEqual(2, rejected.returncode)
            self.assertFalse(outside.exists())
            self.assertEqual(0, accepted.returncode, accepted.stderr)
            self.assertTrue((root / "reports/audit.json").is_file())

    def test_exit_codes_are_zero_for_reports_one_for_strict_exit_and_two_for_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "root"
            self.write(root, "index.md", "[[missing]]\n")

            report_only = self.run_audit(root)
            strict = self.run_audit(root, "--strict-exit")
            invalid_root = self.run_audit(base / "does-not-exist")
            usage = subprocess.run(
                [sys.executable, str(SCRIPT)], text=True, capture_output=True, check=False
            )

            self.assertEqual(0, report_only.returncode)
            self.assertEqual(1, strict.returncode)
            self.assertEqual(2, invalid_root.returncode)
            self.assertEqual(2, usage.returncode)


if __name__ == "__main__":
    unittest.main()
