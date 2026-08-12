#!/usr/bin/env python3
"""Behavior and CLI contracts for the onboarding structure audit."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "obsidian-memory"
SCRIPT = SKILL_ROOT / "scripts" / "structure_audit.py"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from structure_audit import STRICT_COUNTERS, audit


class CleanProject:
    """Build a literal clean onboarding project for real filesystem tests."""

    def __init__(self, root: Path, code: str = "DEMO") -> None:
        self.root = root
        self.code = code
        self.wiki = root / "wiki_demo"
        self.entries: dict[str, str] = {}

    @staticmethod
    def frontmatter(
        title: str,
        *,
        code: str | None = None,
        document_type: str | None = None,
    ) -> str:
        lines = [
            "---",
            f'title: "{title}"',
        ]
        if code is not None:
            lines.append(f'code: "{code}"')
        lines.extend(
            [
                'created: "2026-08-12"',
                'updated: "2026-08-12"',
                'status: "active"',
            ]
        )
        if document_type is not None:
            lines.append(f'type: "{document_type}"')
        lines.extend(["tags:", "  - demo", "---", ""])
        return "\n".join(lines)

    def write(self, relative: str, text: str) -> Path:
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def add_folder_entry(self, relative: str, title: str) -> None:
        self.entries[relative] = (
            f"- `{relative}` — {title}. Назначение: хранить {title.lower()}. "
            f"Состав: постоянные материалы раздела."
        )

    def add_file_entry(self, relative: str, title: str) -> None:
        self.entries[relative] = (
            f"- [[{relative}|{title}]] — Назначение: хранить {title.lower()}. "
            f"Состав: подтверждённые сведения документа."
        )

    def render_index(self, *, reverse: bool = False) -> None:
        ordered = sorted(
            self.entries,
            key=lambda value: unicodedata.normalize("NFC", value).casefold(),
            reverse=reverse,
        )
        body = "\n".join(self.entries[path] for path in ordered)
        text = (
            self.frontmatter("Demo index")
            + "# Demo\n\n## Состав базы\n\n"
            + body
            + "\n"
        )
        self.write(f"wiki_demo/index_{self.code}.md", text)

    def build(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.write("AGENTS.md", "# Demo project\n")
        for folder, title in (
            ("entities/", "Сущности"),
            ("inbox/", "Входящие"),
            ("incidents/", "Инциденты"),
            ("logs/", "Журнал"),
            ("rules/", "Правила"),
        ):
            (self.wiki / folder).mkdir(parents=True, exist_ok=True)
            self.add_folder_entry(folder, title)

        singleton_files = (
            (f"decisions_{self.code}.md", "Решения"),
            (f"index_{self.code}.md", "Главный индекс"),
            (f"todo_{self.code}.md", "Задачи"),
        )
        for relative, title in singleton_files:
            if not relative.startswith("index_"):
                self.write(
                    f"wiki_demo/{relative}",
                    self.frontmatter(title) + f"# {title}\n",
                )
            self.add_file_entry(relative, title)

        numbered_files = (
            (
                f"logs/0001_LOG-{self.code}_2026-08.md",
                "Журнал августа",
                f"LOG-{self.code}-0001",
                "log",
            ),
            (
                f"rules/0001_RUL-{self.code}-database-maintenance.md",
                "Ведение базы",
                f"RUL-{self.code}-0001",
                "rule",
            ),
            (
                f"rules/0002_RUL-{self.code}-link-workflow.md",
                "Проверка связей",
                f"RUL-{self.code}-0002",
                "rule",
            ),
        )
        for relative, title, document_code, document_type in numbered_files:
            self.write(
                f"wiki_demo/{relative}",
                self.frontmatter(
                    title,
                    code=document_code,
                    document_type=document_type,
                )
                + f"# {title}\n",
            )
            self.add_file_entry(relative, title)
        self.render_index()


class StructureAuditTests(unittest.TestCase):
    def test_empty_project_inventory_is_valid_and_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            project.mkdir()

            result = audit(project)

            self.assertEqual(result["PROJECT_MD_FILES"], 0)
            self.assertEqual(result["WIKI_CANDIDATES"], [])
            self.assertEqual(result["OBSIDIAN_VAULTS"], [])
            self.assertEqual(result["SENSITIVE_CANDIDATES"], [])

    def test_inventory_reports_multiple_wiki_and_vault_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            for name in ("wiki_alpha", "wiki_beta"):
                (project / name / ".obsidian").mkdir(parents=True)

            result = audit(project)

            self.assertEqual(
                result["WIKI_CANDIDATES"],
                ["wiki_alpha/", "wiki_beta/"],
            )
            self.assertEqual(
                result["OBSIDIAN_VAULTS"],
                ["wiki_alpha/", "wiki_beta/"],
            )

    def test_clean_onboarding_structure_has_no_strict_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CleanProject(Path(temp_dir) / "project")
            fixture.build()

            result = audit(
                fixture.root,
                wiki_root=fixture.wiki,
                code="DEMO",
                current_month="2026-08",
            )

            self.assertEqual(result["PROJECT_MD_FILES"], 7)
            for counter in STRICT_COUNTERS:
                self.assertEqual(result[counter], [], msg=counter)

    def test_inventory_reports_candidates_without_exposing_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            fixture = CleanProject(project)
            fixture.build()
            (fixture.wiki / ".obsidian").mkdir()
            secret_value = "example-private-value-67"
            fixture.write("notes.md", f"api_key: {secret_value}\n")

            result = audit(project)

            self.assertEqual(result["PROJECT_MD_FILES"], 8)
            self.assertEqual(result["WIKI_CANDIDATES"], ["wiki_demo/"])
            self.assertEqual(result["OBSIDIAN_VAULTS"], ["wiki_demo/"])
            rendered = "\n".join(result["SENSITIVE_CANDIDATES"])
            self.assertIn("notes.md -> SECRET_ASSIGNMENT", rendered)
            self.assertNotIn(secret_value, rendered)

    def test_reports_missing_required_objects_and_current_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            wiki = project / "wiki_demo"
            wiki.mkdir(parents=True)

            result = audit(
                project,
                wiki_root=wiki,
                code="DEMO",
                current_month="2026-08",
            )

            self.assertIn("AGENTS.md", result["MISSING_REQUIRED_OBJECTS"])
            self.assertIn("index_DEMO.md", result["MISSING_REQUIRED_OBJECTS"])
            self.assertEqual(result["MISSING_CURRENT_LOG"], ["2026-08"])

    def test_reports_frontmatter_duplicate_and_missing_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CleanProject(Path(temp_dir) / "project")
            fixture.build()
            fixture.write(
                "wiki_demo/todo_DEMO.md",
                "---\ntitle: Demo\ncreated: 2026-08-12\nupdated: 2026-08-12\n"
                "status: active\nstatus: closed\ntags:\n  - demo\n---\n# Todo\n",
            )

            result = audit(
                fixture.root,
                wiki_root=fixture.wiki,
                code="DEMO",
                current_month="2026-08",
            )

            rendered = "\n".join(result["FRONTMATTER_VIOLATIONS"])
            self.assertIn("todo_DEMO.md -> duplicate key: status", rendered)

    def test_reports_empty_inline_tags(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CleanProject(Path(temp_dir) / "project")
            fixture.build()
            fixture.write(
                "wiki_demo/todo_DEMO.md",
                "---\ntitle: Demo\ncreated: 2026-08-12\nupdated: 2026-08-12\n"
                "status: active\ntags: []\n---\n# Todo\n",
            )

            result = audit(
                fixture.root,
                wiki_root=fixture.wiki,
                code="DEMO",
                current_month="2026-08",
            )

            self.assertIn(
                "todo_DEMO.md -> empty key: tags",
                result["FRONTMATTER_VIOLATIONS"],
            )

    def test_confirmed_optional_section_accepts_numbered_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CleanProject(Path(temp_dir) / "project")
            fixture.build()
            (fixture.wiki / "plans").mkdir()
            fixture.add_folder_entry("plans/", "Планы")
            relative = "plans/0001_PLAN-DEMO-next-step.md"
            fixture.write(
                f"wiki_demo/{relative}",
                fixture.frontmatter(
                    "Next step",
                    code="PLAN-DEMO-0001",
                    document_type="plan",
                )
                + "# Next step\n",
            )
            fixture.add_file_entry(relative, "Next step")
            fixture.render_index()

            result = audit(
                fixture.root,
                wiki_root=fixture.wiki,
                code="DEMO",
                current_month="2026-08",
            )

            self.assertEqual(result["NAMING_VIOLATIONS"], [])
            self.assertEqual(result["FRONTMATTER_VIOLATIONS"], [])

    def test_reports_secondary_index_naming_and_numbering_violations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CleanProject(Path(temp_dir) / "project")
            fixture.build()
            fixture.write(
                "wiki_demo/entities/index_entities.md",
                fixture.frontmatter("Extra index") + "# Extra\n",
            )
            fixture.write(
                "wiki_demo/entities/bad-name.md",
                fixture.frontmatter("Bad name") + "# Bad\n",
            )
            relative = "rules/0004_RUL-DEMO-extra-rule.md"
            fixture.write(
                f"wiki_demo/{relative}",
                fixture.frontmatter(
                    "Extra rule",
                    code="RUL-DEMO-0004",
                    document_type="rule",
                )
                + "# Extra\n",
            )

            result = audit(
                fixture.root,
                wiki_root=fixture.wiki,
                code="DEMO",
                current_month="2026-08",
            )

            self.assertIn("entities/index_entities.md", result["EXTRA_INDEX_FILES"])
            self.assertIn("entities/bad-name.md", result["NAMING_VIOLATIONS"])
            self.assertIn("RUL -> expected 0003, found 0004", result["NUMBERING_VIOLATIONS"])

    def test_reports_index_format_coverage_stale_entries_and_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CleanProject(Path(temp_dir) / "project")
            fixture.build()
            fixture.entries.pop("entities/")
            fixture.entries["ghost.md"] = (
                "- [[ghost.md|Ghost]] — Назначение: ничего. Состав: ничего."
            )
            fixture.entries["todo_DEMO.md"] = "- [[todo_DEMO.md|Задачи]] — без полей"
            fixture.render_index(reverse=True)

            result = audit(
                fixture.root,
                wiki_root=fixture.wiki,
                code="DEMO",
                current_month="2026-08",
            )

            self.assertIn("entities/", result["MISSING_FROM_INDEX"])
            self.assertTrue(
                any(
                    finding.startswith(
                        "index_DEMO.md -> STALE_INDEX_ENTRY_LINE_"
                    )
                    for finding in result["STALE_INDEX_ENTRIES"]
                )
            )
            self.assertNotIn(
                "ghost.md",
                "\n".join(result["STALE_INDEX_ENTRIES"]),
            )
            self.assertTrue(
                any(
                    finding.startswith(
                        "index_DEMO.md -> UNRECOGNIZED_ENTRY_LINE_"
                    )
                    for finding in result["INDEX_FORMAT_VIOLATIONS"]
                )
            )
            self.assertTrue(result["INDEX_ORDER_VIOLATIONS"])

    def test_unrecognized_index_line_is_reported_without_its_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CleanProject(Path(temp_dir) / "project")
            fixture.build()
            secret_value = "example-private-index-value-67"
            fixture.write(
                "wiki_demo/index_DEMO.md",
                fixture.frontmatter("Demo index")
                + "# Demo\n\n## Состав базы\n\n"
                + f"- token: {secret_value}\n"
                + f"- [[{secret_value}|Hidden]] — malformed\n",
            )

            result = audit(
                fixture.root,
                wiki_root=fixture.wiki,
                code="DEMO",
                current_month="2026-08",
            )

            rendered = "\n".join(result["INDEX_FORMAT_VIOLATIONS"])
            self.assertIn(
                "index_DEMO.md -> UNRECOGNIZED_ENTRY_LINE_13",
                rendered,
            )
            self.assertIn(
                "index_DEMO.md -> UNRECOGNIZED_ENTRY_LINE_14",
                rendered,
            )
            self.assertNotIn(secret_value, rendered)

    def test_stale_index_entry_is_reported_without_its_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CleanProject(Path(temp_dir) / "project")
            fixture.build()
            secret_target = "example-private-stale-index-value-67.md"
            fixture.entries[secret_target] = (
                f"- [[{secret_target}|Hidden]] — Назначение: hidden. "
                "Состав: hidden."
            )
            fixture.render_index()

            result = audit(
                fixture.root,
                wiki_root=fixture.wiki,
                code="DEMO",
                current_month="2026-08",
            )

            rendered = "\n".join(result["STALE_INDEX_ENTRIES"])
            self.assertRegex(
                rendered,
                r"^index_DEMO\.md -> STALE_INDEX_ENTRY_LINE_\d+$",
            )
            self.assertNotIn(secret_target, rendered)

    def test_reports_duplicate_database_composition_section(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CleanProject(Path(temp_dir) / "project")
            fixture.build()
            index = fixture.wiki / "index_DEMO.md"
            index.write_text(
                index.read_text(encoding="utf-8")
                + "\n## Состав базы\n\n- [[ghost.md|Ghost]] — "
                "Назначение: duplicate. Состав: duplicate.\n",
                encoding="utf-8",
            )

            result = audit(
                fixture.root,
                wiki_root=fixture.wiki,
                code="DEMO",
                current_month="2026-08",
            )

            self.assertIn(
                "index_DEMO.md -> duplicate section: ## Состав базы",
                result["INDEX_FORMAT_VIOLATIONS"],
            )

    def test_inbox_and_obsidian_contents_are_excluded_from_index_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CleanProject(Path(temp_dir) / "project")
            fixture.build()
            fixture.write("wiki_demo/inbox/raw.md", "Unverified\n")
            fixture.write("wiki_demo/.obsidian/plugin-notes.md", "Local config\n")

            result = audit(
                fixture.root,
                wiki_root=fixture.wiki,
                code="DEMO",
                current_month="2026-08",
            )

            self.assertNotIn("inbox/raw.md", result["MISSING_FROM_INDEX"])
            self.assertNotIn(".obsidian/plugin-notes.md", result["MISSING_FROM_INDEX"])

    def test_unicode_equivalent_index_path_matches_physical_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CleanProject(Path(temp_dir) / "project")
            fixture.build()
            nfd_slug = unicodedata.normalize("NFD", "café")
            physical = f"entities/0001_DOC-DEMO-{nfd_slug}.md"
            indexed = "entities/0001_DOC-DEMO-café.md"
            fixture.write(
                f"wiki_demo/{physical}",
                fixture.frontmatter(
                    "Café",
                    code="DOC-DEMO-0001",
                    document_type="entity",
                )
                + "# Café\n",
            )
            fixture.add_file_entry(indexed, "Café")
            fixture.render_index()

            result = audit(
                fixture.root,
                wiki_root=fixture.wiki,
                code="DEMO",
                current_month="2026-08",
            )

            self.assertNotIn(indexed, result["MISSING_FROM_INDEX"])
            self.assertNotIn(indexed, result["STALE_INDEX_ENTRIES"])

    def test_audit_does_not_modify_project_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CleanProject(Path(temp_dir) / "project")
            fixture.build()

            before = {
                path.relative_to(fixture.root).as_posix(): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in fixture.root.rglob("*")
                if path.is_file()
            }
            audit(
                fixture.root,
                wiki_root=fixture.wiki,
                code="DEMO",
                current_month="2026-08",
            )
            after = {
                path.relative_to(fixture.root).as_posix(): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in fixture.root.rglob("*")
                if path.is_file()
            }

            self.assertEqual(after, before)

    def test_external_file_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            project = base / "project"
            project.mkdir()
            outside = base / "private.md"
            outside.write_text("private\n", encoding="utf-8")
            linked = project / "linked.md"
            try:
                linked.symlink_to(outside)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlinks are unavailable: {exc}")

            with self.assertRaisesRegex(ValueError, "unsafe path outside project"):
                audit(project)

    def test_internal_file_symlink_remains_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            project.mkdir()
            source = project / "source.md"
            source.write_text("# Source\n", encoding="utf-8")
            linked = project / "linked.md"
            try:
                linked.symlink_to(source)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlinks are unavailable: {exc}")

            result = audit(project)

            self.assertEqual(result["PROJECT_MD_FILES"], 2)

    def test_existing_agents_file_remains_byte_for_byte_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CleanProject(Path(temp_dir) / "project")
            fixture.build()
            agents = fixture.write(
                "AGENTS.md",
                "# Existing instructions\n\nPreserve this exact content.\n",
            )
            before = agents.read_bytes()

            audit(
                fixture.root,
                wiki_root=fixture.wiki,
                code="DEMO",
                current_month="2026-08",
            )

            self.assertEqual(agents.read_bytes(), before)

    def test_required_files_reject_directories_with_the_same_names(self) -> None:
        file_paths = (
            "AGENTS.md",
            "wiki_demo/decisions_DEMO.md",
            "wiki_demo/index_DEMO.md",
            "wiki_demo/todo_DEMO.md",
            "wiki_demo/rules/0001_RUL-DEMO-database-maintenance.md",
            "wiki_demo/rules/0002_RUL-DEMO-link-workflow.md",
        )
        for relative in file_paths:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temp_dir:
                fixture = CleanProject(Path(temp_dir) / "project")
                fixture.build()
                target = fixture.root / relative
                target.unlink()
                target.mkdir()

                result = audit(
                    fixture.root,
                    wiki_root=fixture.wiki,
                    code="DEMO",
                    current_month="2026-08",
                )

                expected = relative.removeprefix("wiki_demo/")
                self.assertIn(expected, result["MISSING_REQUIRED_OBJECTS"])

    def test_required_directories_reject_files_with_the_same_names(self) -> None:
        for relative in ("entities", "inbox", "incidents", "logs", "rules"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temp_dir:
                fixture = CleanProject(Path(temp_dir) / "project")
                fixture.build()
                target = fixture.wiki / relative
                shutil.rmtree(target)
                target.write_text("not a directory\n", encoding="utf-8")

                result = audit(
                    fixture.root,
                    wiki_root=fixture.wiki,
                    code="DEMO",
                    current_month="2026-08",
                )

                self.assertIn(f"{relative}/", result["MISSING_REQUIRED_OBJECTS"])


class StructureAuditCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_inventory_returns_zero_and_stable_counters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CleanProject(Path(temp_dir) / "project")
            fixture.build()

            result = self.run_cli(str(fixture.root))

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            for counter in (
                "PROJECT_MD_FILES",
                "WIKI_CANDIDATES",
                "OBSIDIAN_VAULTS",
                "SENSITIVE_CANDIDATES",
            ):
                self.assertRegex(result.stdout, rf"(?m)^{counter}=\d+$")
            self.assertEqual(result.stderr, "")

    def test_clean_validation_returns_zero_in_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CleanProject(Path(temp_dir) / "project")
            fixture.build()

            result = self.run_cli(
                str(fixture.root),
                "--wiki-root",
                str(fixture.wiki),
                "--code",
                "DEMO",
                "--strict-exit",
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            for counter in STRICT_COUNTERS:
                self.assertIn(f"{counter}=0\n", result.stdout)

    def test_structural_problem_returns_one_in_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            wiki = project / "wiki_demo"
            wiki.mkdir(parents=True)

            result = self.run_cli(
                str(project),
                "--wiki-root",
                str(wiki),
                "--code",
                "DEMO",
                "--strict-exit",
            )

            self.assertEqual(result.returncode, 1)
            self.assertRegex(result.stdout, r"(?m)^MISSING_REQUIRED_OBJECTS=[1-9]\d*$")

    def test_invalid_input_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            project.mkdir()

            bad_code = self.run_cli(
                str(project),
                "--wiki-root",
                str(project),
                "--code",
                "1bad",
            )
            unpaired = self.run_cli(str(project), "--code", "DEMO")

            self.assertEqual(bad_code.returncode, 2)
            self.assertIn("ERROR: invalid project code", bad_code.stderr)
            self.assertEqual(unpaired.returncode, 2)
            self.assertIn(
                "ERROR: --wiki-root and --code must be provided together",
                unpaired.stderr,
            )

    def test_missing_project_error_does_not_echo_the_input_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "private-project-name"

            result = self.run_cli(str(missing))

            self.assertEqual(result.returncode, 2)
            self.assertEqual(
                result.stderr,
                "ERROR: project root is not a directory\n",
            )
            self.assertNotIn(str(missing), result.stderr)

    def test_help_lists_stable_options(self) -> None:
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        for option in ("--wiki-root", "--code", "--strict-exit"):
            self.assertIn(option, result.stdout)


if __name__ == "__main__":
    unittest.main()
