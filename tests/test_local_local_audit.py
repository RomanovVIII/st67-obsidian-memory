"""Scoped CLI regressions; all fixtures are isolated and contain no live data."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "skills/obsidian-memory/scripts/link_audit.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("scoped_link_audit", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LocalAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write("index.md", "# Index\n- [[index]]\n- [[cards/service]]\n")
        self.write("cards/service.md", "# Service\nConfirmed fact.\n")

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def run_audit(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), str(self.root), "--json", "--strict-exit", *args],
            capture_output=True, text=True, encoding="utf-8",
        )

    def report(self, *args):
        result = self.run_audit(*args)
        self.assertIn(result.returncode, (0, 1), result.stderr)
        return result, json.loads(result.stdout)

    def config(self, **extra):
        self.write("obsidian-memory.config.json", json.dumps({"schema_version": 2, **extra}))

    def test_new_card_requires_index_registration(self):
        self.write("cards/new.md", "# New\n")
        result, report = self.report("--changed", "cards/new.md")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["MISSING_FROM_INDEX"], ["cards/new.md"])
        self.assertEqual(report["AUDIT_SCOPE"]["mode"], "local")

    def test_move_checks_old_backlinks_and_new_registration(self):
        (self.root / "cards/service.md").rename(self.root / "cards/renamed.md")
        self.write("cards/client.md", "[[cards/service]]\n[[unrelated-missing]]\n")
        _, report = self.report("--changed", "cards/renamed.md", "--removed", "cards/service.md")
        self.assertEqual(report["BROKEN_WIKI_LINKS"], ["cards/client.md -> BROKEN_WIKILINK_LINE_1", "index.md -> BROKEN_WIKILINK_LINE_3"])
        self.assertEqual(report["MISSING_FROM_INDEX"], ["cards/renamed.md"])
        self.assertEqual(report["STALE_INDEX_ENTRIES"], ["index.md -> STALE_INDEX_ENTRY_LINE_3"])

    def test_deleted_attachment_checks_wiki_and_markdown_embeds(self):
        self.write("cards/client.md", "![[assets/proof.png]]\n![proof](../assets/proof.png)\n![[other.png]]\n")
        _, report = self.report("--removed", "assets/proof.png")
        self.assertEqual(report["BROKEN_WIKI_EMBEDS"], ["cards/client.md -> BROKEN_WIKI_EMBED_LINE_1"])
        self.assertEqual(report["BROKEN_MARKDOWN_ATTACHMENTS"], ["cards/client.md -> BROKEN_MARKDOWN_ATTACHMENT_LINE_2"])

    def test_new_duplicate_name_affects_existing_short_link(self):
        self.write("other/service.md", "# Another\n")
        self.write("clients/client.md", "[[service]]\n[[missing]]\n")
        _, report = self.report("--changed", "other/service.md")
        self.assertTrue(any(item["source"] == "clients/client.md" for item in report["AMBIGUOUS_WIKI_LINKS"]))
        self.assertEqual(len(report["DUPLICATE_MANAGED_FILENAMES"]), 1)
        self.assertEqual(report["BROKEN_WIKI_LINKS"], [])

    def test_removed_short_link_does_not_silently_retarget(self):
        (self.root / "cards/service.md").unlink()
        self.write("other/service.md", "# Another\n")
        self.write("cards/client.md", "[[service]]\n")
        _, report = self.report("--removed", "cards/service.md")
        self.assertTrue(any(item["kind"] == "WIKI_TARGET_CHANGED_AFTER_REMOVAL" for item in report["STRICT_PROBLEMS"]))

    def test_duplicate_index_entry_only_for_touched_target(self):
        self.write("index.md", "[[index]]\n[[cards/service]]\n[[cards/service]]\n[[bad]]\n[[bad]]\n")
        _, report = self.report("--changed", "cards/service.md")
        self.assertEqual([item["target"] for item in report["INDEX_POLICY_FINDINGS"]], ["cards/service.md"])
        self.assertEqual(report["BROKEN_WIKI_LINKS"], [])

    def test_unrelated_errors_do_not_affect_exit_and_are_not_reported(self):
        self.write("cards/unrelated.md", "[[missing]]\nTBD_noise\n")
        result, report = self.report("--changed", "cards/service.md")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["STRICT_PROBLEM_COUNT"], 0)
        self.assertEqual(report["TBD_REFERENCES"], [])
        self.assertEqual(report["MISSING_FROM_INDEX"], [])
        full, _ = self.report()
        self.assertEqual(full.returncode, 1)

    def test_changed_document_outgoing_links_are_checked(self):
        self.write("cards/service.md", "[[missing]]\n![proof](missing.png)\nTBD_confirm\n")
        _, report = self.report("--changed", "cards/service.md")
        self.assertEqual(report["BROKEN_WIKI_LINKS"], ["cards/service.md -> BROKEN_WIKILINK_LINE_1"])
        self.assertEqual(report["TBD_REFERENCES"], ["cards/service.md -> TBD_REFERENCE_LINE_3"])

    def test_section_and_lifecycle_policy_apply_to_touched_card(self):
        self.write("cards/TMP-0001.md", "# Card\n")
        self.write("index.md", "# Index\n## Wrong\n[[cards/TMP-0001]]\n")
        self.config(index_section_rules=[{"heading": "Cards", "path_prefixes": ["cards"], "lifecycle_codes": []}],
                    disallowed_lifecycle_codes=[{"code": "TMP", "path_prefixes": ["cards"]}])
        _, report = self.report("--changed", "cards/TMP-0001.md")
        self.assertIn("INDEX_SECTION_MISMATCH", [item["kind"] for item in report["INDEX_POLICY_FINDINGS"]])
        self.assertTrue(report["DISALLOWED_LIFECYCLE_CODE_FINDINGS"])

    def test_v1_config_and_repeatable_paths_remain_supported(self):
        self.write("cards/second.md", "# Second\n")
        self.write("root.md", "[[root]]\n[[cards/service]]\n[[cards/second]]\n")
        self.write("obsidian-memory.config.json", json.dumps({"schema_version": 1, "index": "root.md", "excluded_folders": ["index.md"]}))
        result, report = self.report("--changed", "cards/service.md", "--changed", "cards/second.md", "--removed", "old.md", "--removed", "old.png")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(report["AUDIT_SCOPE"]["changed"]), 2)
        self.assertEqual(len(report["AUDIT_SCOPE"]["removed"]), 2)

    def test_compare_roots_only_report_touched_names(self):
        with tempfile.TemporaryDirectory() as other:
            Path(other, "service.md").write_text("[[primary-only]]\n", encoding="utf-8")
            Path(other, "untouched.md").write_text("# Other\n", encoding="utf-8")
            self.write("cards/untouched.md", "# Same name\n")
            _, report = self.report("--changed", "cards/service.md", "--compare-root", other)
            self.assertEqual(len(report["DUPLICATE_MANAGED_FILENAMES"]), 1)
            self.assertEqual("DUPLICATE_MANAGED_FILENAME", report["DUPLICATE_MANAGED_FILENAMES"][0]["kind"])
            self.assertEqual(report["BROKEN_WIKI_LINKS"], [])

    def test_invalid_paths_and_wrong_existence_return_two(self):
        for flag, value in [("--changed", "missing.md"), ("--removed", "cards/service.md"),
                            ("--changed", "cards"), ("--removed", "cards"),
                            ("--changed", "../outside.md"), ("--removed", "/outside.md"),
                            ("--changed", str(self.root / "cards/service.md")),
                            ("--removed", "C:/outside.md"), ("--removed", "C:outside.md"),
                            ("--removed", ".")]:
            with self.subTest(flag=flag, value=value):
                self.assertEqual(self.run_audit(flag, value).returncode, 2)

    def test_excluded_and_overlapping_paths_return_two(self):
        self.config(excluded_paths=["excluded"])
        self.write("excluded/secret.md", "# Private\n")
        for args in [("--changed", "excluded/secret.md"), ("--removed", "excluded/old.md"),
                     ("--changed", "cards/service.md", "--removed", "cards/service.md")]:
            self.assertEqual(self.run_audit(*args).returncode, 2)

    def test_no_implicit_network_or_writes(self):
        self.write("cards/service.md", "https://example.invalid/status\n")
        before = {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        with patch.object(module, "check_url", side_effect=AssertionError("network attempted")):
            report = module.audit(self.root, "index.md", {}, False, changed_paths=["cards/service.md"])
        self.assertEqual(report["URLS_CHECKED"], 0)
        after = {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_explicit_urls_only_check_selected_document(self):
        self.write("cards/service.md", "https://example.invalid/selected\n")
        self.write("cards/unrelated.md", "https://example.invalid/unrelated\n")
        config = module.validate_config({"schema_version": 1, "url": {"classes": [{"name": "test", "url_patterns": [".*"], "check": True}]}})
        def successful(item, timeout):
            return {**item, "reachable": True, "error": "", "status": 200}
        with patch.object(module, "check_url", side_effect=successful) as check:
            report = module.audit(self.root, "index.md", config, True, changed_paths=["cards/service.md"])
        self.assertEqual(check.call_count, 1)
        self.assertEqual(report["URLS_FOUND"], 1)

    def test_index_template_registers_maintenance_rule_once(self):
        templates = SCRIPT.parents[1] / "references/file-templates.md"
        block = templates.read_text(encoding="utf-8").split("```markdown", 1)[1].split("```", 1)[0]
        block = block.replace("<memory_root>", "demo").replace("<procedure_owner>", "rules")
        self.write("index.md", block)
        self.write("log.md", "# Log\n")
        self.write("rules/demo_maintenance_rules.md", "# Rules\n")
        self.write("rules/demo_link_workflow.md", "# Links\n")
        self.write("rules/demo_question_and_plan_lifecycle.md", "# Lifecycle\n")
        _, report = self.report()
        self.assertFalse(any(item["kind"] == "DUPLICATE_INDEX_ENTRY" for item in report["INDEX_POLICY_FINDINGS"]))

    def test_unrelated_required_path_and_policies_are_suppressed(self):
        self.config(required_paths=["missing/rule.md"], legacy_markers=["OLD_STATE"],
                    forbidden_path_patterns=["forbidden/"],
                    disallowed_lifecycle_codes=[{"code": "HND", "path_prefixes": ["other"]}],
                    index_section_rules=[{"heading": "Other", "path_prefixes": ["other"], "lifecycle_codes": []}])
        self.write("other/HND-0001.md", "[[forbidden/missing]]\nOLD_STATE\n")
        self.write("todo.md", "[[other/HND-0001]]\n")
        result, report = self.report("--changed", "cards/service.md")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["STRICT_PROBLEM_COUNT"], 0)

    def test_unchanged_todo_only_checks_entry_to_touched_target(self):
        self.config(disallowed_lifecycle_codes=[{"code": "HND", "path_prefixes": ["cards"]}])
        self.write("todo.md", "[[cards/service|HND-0001]]\n[[cards/unrelated|HND-0002]]\n")
        self.write("cards/unrelated.md", "# Other\n")
        _, report = self.report("--changed", "cards/service.md")
        self.assertEqual([item["target"] for item in report["DISALLOWED_LIFECYCLE_CODE_FINDINGS"]], ["HND-0001"])

    def test_lifecycle_label_on_unrelated_link_in_same_line_is_excluded(self):
        self.config(disallowed_lifecycle_codes=[{"code": "HND", "path_prefixes": ["cards"]}])
        self.write("cards/unrelated.md", "# Other\n")
        self.write("todo.md", "[[cards/service]] and [[cards/unrelated|HND-0002]]\n")
        result, report = self.report("--changed", "cards/service.md")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["DISALLOWED_LIFECYCLE_CODE_FINDINGS"], [])

    def test_attachment_change_only_checks_affected_table_alias(self):
        self.write("assets/proof.png", "fake image fixture")
        self.write("cards/client.md", "| Proof | Other |\n| --- | --- |\n| ![[assets/proof.png|100]] | [[missing|bad]] |\n")
        _, report = self.report("--changed", "assets/proof.png")
        self.assertEqual(len(report["UNESCAPED_WIKI_ALIASES_IN_TABLE"]), 1)
        self.assertEqual(report["UNESCAPED_WIKI_ALIASES_IN_TABLE"][0]["source"], "cards/client.md")
        self.assertIn("Line 3", report["UNESCAPED_WIKI_ALIASES_IN_TABLE"][0]["message"])
        self.assertEqual(report["BROKEN_WIKI_LINKS"], [])

    def test_symlink_paths_cannot_escape_or_enter_excluded_scope(self):
        def directory_link(link, target):
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError as error:
                if sys.platform != "win32":
                    self.skipTest(f"symlink unavailable: {error}")
                # Windows junctions exercise the same resolve boundary without
                # requiring the symbolic-link privilege. Both paths are fixtures.
                quote = lambda value: "'" + str(value).replace("'", "''") + "'"
                command = "New-Item -ItemType Junction -Path " + quote(link) + " -Target " + quote(target) + " -ErrorAction Stop | Out-Null"
                created = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True)
                if created.returncode:
                    self.skipTest("directory links unavailable in this environment")

        with tempfile.TemporaryDirectory() as other:
            Path(other, "outside.md").write_text("# Outside\n", encoding="utf-8")
            directory_link(self.root / "outside-link", Path(other))
            self.assertEqual(self.run_audit("--changed", "outside-link/outside.md").returncode, 2)
            self.assertEqual(self.run_audit("--removed", "outside-link/old.md").returncode, 2)
            self.config(excluded_paths=["private"])
            self.write("private/secret.md", "# Private\n")
            directory_link(self.root / "private-link", self.root / "private")
            self.assertEqual(self.run_audit("--changed", "private-link/secret.md").returncode, 2)


if __name__ == "__main__":
    unittest.main()
