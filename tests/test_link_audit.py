#!/usr/bin/env python3
"""Regression tests for the Obsidian memory link audit."""

from __future__ import annotations

import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "obsidian-memory"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from link_audit import audit, normalize_rel


class ProjectVaultAuditTests(unittest.TestCase):
    def write(self, root: Path, relative: str, text: str) -> None:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def test_reports_ambiguous_short_links_inside_current_vault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            self.write(vault, "index.md", "# A\n\n- [[index]]\n- [[a/logs]]\n- [[note]]\n")
            self.write(vault, "a/logs.md", "# A log\n")
            self.write(vault, "b/logs.md", "# B log\n")
            self.write(vault, "note.md", "# Note\n\nSee [[logs]].\n")

            result = audit(vault, "index.md", vault)

            self.assertEqual(
                result["AMBIGUOUS_WIKI_LINKS"],
                ["note.md -> AMBIGUOUS_WIKILINK_LINE_3"],
            )
            self.assertEqual(result["BROKEN_WIKI_LINKS"], [])

    def test_standalone_vault_can_exclude_agents_from_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "project"
            self.write(
                vault,
                "index.md",
                "# Project\n\n- [[index]]\n- [[todo]]\n- [[decisions]]\n",
            )
            self.write(vault, "todo.md", "# TODO\n")
            self.write(vault, "decisions.md", "# Decisions\n")
            self.write(vault, "AGENTS.md", "# Project rules\n")

            result = audit(vault, "index.md", vault, index_exclude=["AGENTS.md"])

            self.assertEqual(result["AMBIGUOUS_WIKI_LINKS"], [])
            self.assertEqual(result["BROKEN_WIKI_LINKS"], [])
            self.assertEqual(result["MISSING_FROM_INDEX"], [])
            self.assertEqual(result["STALE_INDEX_ENTRIES"], [])

    def test_nested_vault_does_not_scan_sibling_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            vault = project / "wiki"
            self.write(vault, "index.md", "# Project\n\n- [[index]]\n- [[products/app]]\n")
            self.write(vault, "products/app.md", "# App\n")
            self.write(project, "sources/app/README.md", "# Source docs\n\n[[missing]]\n")

            result = audit(vault, "index.md", vault)

            self.assertEqual(result["MD_FILES"], 2)
            self.assertEqual(result["BROKEN_WIKI_LINKS"], [])
            self.assertEqual(result["MISSING_FROM_INDEX"], [])

    def test_index_exclusion_does_not_skip_link_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = Path(temp_dir) / "memory"
            self.write(memory, "index.md", "# Index\n\n- [[index]]\n")
            self.write(memory, "temp/draft.md", "# Draft\n\nSee [[missing-page]].\n")

            result = audit(memory, "index.md", memory, index_exclude=["temp/**"])

            self.assertEqual(result["MISSING_FROM_INDEX"], [])
            self.assertEqual(
                result["BROKEN_WIKI_LINKS"],
                ["temp/draft.md -> BROKEN_WIKILINK_LINE_3"],
            )

    def test_broken_wikilink_does_not_expose_its_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            secret_target = "example-private-link-value-67"
            self.write(vault, "index.md", "# Index\n\n- [[index]]\n- [[note]]\n")
            self.write(vault, "note.md", f"# Note\n\nSee [[{secret_target}]].\n")

            result = audit(vault, "index.md", vault)

            rendered = "\n".join(result["BROKEN_WIKI_LINKS"])
            self.assertEqual(rendered, "note.md -> BROKEN_WIKILINK_LINE_3")
            self.assertNotIn(secret_target, rendered)

    def test_markdown_path_outside_vault_is_safe_broken_finding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            vault = base / "vault"
            secret_target = "example-private-outside-value-67.md"
            self.write(base, secret_target, "private\n")
            self.write(vault, "index.md", "# Index\n\n- [[index]]\n- [[note]]\n")
            self.write(
                vault,
                "note.md",
                f"# Note\n\n[Outside](../{secret_target})\n",
            )

            result = audit(vault, "index.md", vault)

            rendered = "\n".join(result["BROKEN_MARKDOWN_LINKS"])
            self.assertEqual(rendered, "note.md -> UNSAFE_MARKDOWN_LINK_LINE_3")
            self.assertNotIn(secret_target, rendered)

    def test_external_file_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            vault = base / "vault"
            self.write(vault, "index.md", "# Index\n\n- [[index]]\n")
            outside = base / "private.md"
            outside.write_text("private\n", encoding="utf-8")
            linked = vault / "linked.md"
            try:
                linked.symlink_to(outside)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlinks are unavailable: {exc}")

            with self.assertRaisesRegex(ValueError, "unsafe path outside vault"):
                audit(vault, "index.md", vault)

    def test_internal_file_symlink_remains_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            self.write(
                vault,
                "index.md",
                "# Index\n\n- [[index]]\n- [[target]]\n- [[linked]]\n",
            )
            self.write(vault, "target.md", "# Target\n")
            linked = vault / "linked.md"
            try:
                linked.symlink_to(vault / "target.md")
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlinks are unavailable: {exc}")

            result = audit(vault, "index.md", vault)

            self.assertEqual(result["MD_FILES"], 3)
            self.assertEqual(result["BROKEN_WIKI_LINKS"], [])

    def test_markdown_links_count_as_incoming_relationships(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = Path(temp_dir) / "memory"
            self.write(
                memory,
                "index.md",
                "# Index\n\n- [index](index.md)\n- [note](note.md)\n",
            )
            self.write(memory, "note.md", "# Note\n")

            result = audit(memory, "index.md", memory)

            self.assertNotIn("note.md", result["ZERO_INCOMING_EXCEPT_INDEX"])
            self.assertIn("note.md", result["ONLY_INDEX_OR_LOG_INCOMING"])

    def test_nfc_wikilinks_resolve_nfd_file_paths_and_index_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            nfd_folder = unicodedata.normalize("NFD", "Устройства")
            nfd_name = unicodedata.normalize("NFD", "Удалённый.md")
            self.write(
                vault,
                "index.md",
                "# Index\n\n- [[index]]\n- [[source]]\n- [[Устройства/Удалённый]]\n",
            )
            self.write(vault, "source.md", "# Source\n\nSee [[Устройства/Удалённый]].\n")
            self.write(vault, f"{nfd_folder}/{nfd_name}", "# Удалённый\n")

            result = audit(vault, "index.md", vault)

            self.assertEqual(result["BROKEN_WIKI_LINKS"], [])
            self.assertEqual(result["MISSING_FROM_INDEX"], [])
            self.assertEqual(result["STALE_INDEX_ENTRIES"], [])

    def test_nfc_markdown_paths_index_nfd_files_without_stale_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            nfd_folder = unicodedata.normalize("NFD", "Документы")
            nfd_doc = unicodedata.normalize("NFD", "Отчёт.md")
            nfd_image = unicodedata.normalize("NFD", "Схема.png")
            self.write(
                vault,
                "index.md",
                "# Index\n\n- [index](index.md)\n- [source](source.md)\n"
                "- [report](Документы/Отчёт.md)\n",
            )
            self.write(
                vault,
                "source.md",
                "# Source\n\n[Отчёт](Документы/Отчёт.md)\n\n"
                "![Схема](Документы/Схема.png)\n",
            )
            self.write(vault, f"{nfd_folder}/{nfd_doc}", "# Отчёт\n")
            image = vault / nfd_folder / nfd_image
            image.write_bytes(b"png")

            result = audit(vault, "index.md", vault)

            self.assertEqual(result["BROKEN_MARKDOWN_LINKS"], [])
            self.assertEqual(result["BROKEN_MARKDOWN_ATTACHMENTS"], [])
            self.assertEqual(result["MISSING_FROM_INDEX"], [])
            self.assertEqual(result["STALE_INDEX_ENTRIES"], [])

    def test_relative_paths_do_not_conflate_unicode_equivalent_siblings(self) -> None:
        nfc_parent = unicodedata.normalize("NFC", "Mémoire")
        nfd_parent = unicodedata.normalize("NFD", "Mémoire")
        self.assertNotEqual(nfc_parent, nfd_parent)
        path = Path("/vault") / nfc_parent / "outside.md"
        root = Path("/vault") / nfd_parent

        with self.assertRaises(ValueError):
            normalize_rel(path, root)

    def test_nfd_nested_memory_root_keeps_index_and_incoming_relationships(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            nfd_memory_name = unicodedata.normalize("NFD", "Mémoire")
            memory = vault / nfd_memory_name
            self.write(memory, "index.md", "# Index\n\n- [[index]]\n- [[note]]\n")
            self.write(memory, "note.md", "# Note\n")

            result = audit(memory, "index.md", vault)

            self.assertEqual(result["BROKEN_WIKI_LINKS"], [])
            self.assertEqual(result["MISSING_FROM_INDEX"], [])
            self.assertEqual(result["STALE_INDEX_ENTRIES"], [])
            self.assertNotIn("note.md", result["ZERO_INCOMING_EXCEPT_INDEX"])

    def test_wikilink_headings_and_aliases_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            self.write(
                vault,
                "index.md",
                "# Index\n\n- [[index]]\n- [[note]]\n- [[target]]\n",
            )
            self.write(
                vault,
                "note.md",
                "# Note\n\n[[target#Раздел|Открыть раздел]]\n"
                "[[target#Отсутствует]]\n",
            )
            self.write(vault, "target.md", "# Target\n\n## Раздел\n\nText\n")

            result = audit(vault, "index.md", vault)

            self.assertEqual(
                result["BROKEN_WIKI_LINKS"],
                ["note.md -> BROKEN_WIKILINK_LINE_4"],
            )

    def test_local_headings_and_block_references_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            self.write(vault, "index.md", "# Index\n\n- [[index]]\n- [[note]]\n")
            self.write(
                vault,
                "note.md",
                "# Note\n\n## Local section\n\nParagraph ^known-block\n\n"
                "[[#Local section]]\n[[#Missing section]]\n"
                "[[note#^known-block]]\n[[note#^missing-block]]\n",
            )

            result = audit(vault, "index.md", vault)

            self.assertEqual(
                result["BROKEN_WIKI_LINKS"],
                [
                    "note.md -> BROKEN_WIKILINK_LINE_8",
                    "note.md -> BROKEN_WIKILINK_LINE_10",
                ],
            )

    def test_binary_wiki_embed_with_explicit_extension_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            self.write(vault, "index.md", "# Index\n\n- [[index]]\n- [[note]]\n")
            self.write(vault, "note.md", "# Note\n\n![[assets/image.png]]\n")
            image = vault / "assets" / "image.png"
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_bytes(b"png")

            result = audit(vault, "index.md", vault)

            self.assertEqual(result["BROKEN_WIKI_EMBEDS"], [])
            self.assertEqual(result["AMBIGUOUS_WIKI_EMBEDS"], [])

    def test_short_binary_embed_reports_ambiguity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            self.write(vault, "index.md", "# Index\n\n- [[index]]\n- [[note]]\n")
            self.write(vault, "note.md", "# Note\n\n![[image.png]]\n")
            for folder in ("a", "b"):
                image = vault / folder / "image.png"
                image.parent.mkdir(parents=True, exist_ok=True)
                image.write_bytes(b"png")

            result = audit(vault, "index.md", vault)

            self.assertEqual(result["BROKEN_WIKI_EMBEDS"], [])
            self.assertEqual(
                result["AMBIGUOUS_WIKI_EMBEDS"],
                ["note.md -> AMBIGUOUS_WIKI_EMBED_LINE_3"],
            )

    def test_markdown_embed_heading_is_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            self.write(vault, "index.md", "# Index\n\n- [[index]]\n- [[note]]\n- [[target]]\n")
            self.write(vault, "note.md", "# Note\n\n![[target#Missing]]\n")
            self.write(vault, "target.md", "# Target\n\n## Present\n")

            result = audit(vault, "index.md", vault)

            self.assertEqual(
                result["BROKEN_WIKI_EMBEDS"],
                ["note.md -> BROKEN_WIKI_EMBED_LINE_3"],
            )


if __name__ == "__main__":
    unittest.main()
