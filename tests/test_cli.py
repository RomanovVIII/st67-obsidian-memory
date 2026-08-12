#!/usr/bin/env python3
"""End-to-end CLI contract tests for link_audit.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "obsidian-memory" / "scripts" / "link_audit.py"
COUNTERS = (
    "BROKEN_WIKI_LINKS",
    "BROKEN_WIKI_EMBEDS",
    "AMBIGUOUS_WIKI_LINKS",
    "AMBIGUOUS_WIKI_EMBEDS",
    "BROKEN_MARKDOWN_LINKS",
    "BROKEN_MARKDOWN_ATTACHMENTS",
    "MISSING_FROM_INDEX",
    "STALE_INDEX_ENTRIES",
    "ZERO_INCOMING_EXCEPT_INDEX",
    "ONLY_INDEX_OR_LOG_INCOMING",
    "TBD_REFERENCES",
)


class LinkAuditCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def write(self, root: Path, relative: str, text: str) -> None:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def test_clean_vault_returns_zero_and_stable_counters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            self.write(vault, "index.md", "# Index\n\n- [[index]]\n- [[note]]\n")
            self.write(vault, "note.md", "# Note\n")

            result = self.run_cli(str(vault), "--strict-exit")

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("MD_FILES=2\n", result.stdout)
            for counter in COUNTERS:
                self.assertRegex(result.stdout, rf"(?m)^{counter}=\d+$")
            self.assertIn("ZERO_INCOMING_EXCEPT_INDEX=0\n", result.stdout)
            self.assertIn("ONLY_INDEX_OR_LOG_INCOMING=1\nnote.md\n", result.stdout)
            self.assertIn("TBD_REFERENCES=0\n", result.stdout)
            self.assertEqual(result.stderr, "")

    def test_strict_problem_returns_one_and_reports_safe_location(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            self.write(vault, "index.md", "# Index\n\n- [[index]]\n- [[note]]\n")
            self.write(vault, "note.md", "# Note\n\nSee [[missing-page]].\n")

            result = self.run_cli(str(vault), "--strict-exit")

            self.assertEqual(result.returncode, 1)
            self.assertIn("BROKEN_WIKI_LINKS=1\n", result.stdout)
            self.assertIn("note.md -> BROKEN_WIKILINK_LINE_3\n", result.stdout)
            self.assertNotIn("missing-page", result.stdout)
            self.assertEqual(result.stderr, "")

    def test_missing_memory_root_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing"

            result = self.run_cli(str(missing))

            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertEqual(
                result.stderr,
                "ERROR: memory root is not a directory\n",
            )
            self.assertNotIn(str(missing), result.stderr)

    def test_memory_root_outside_vault_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            memory = base / "memory"
            vault = base / "vault"
            self.write(memory, "index.md", "# Index\n")
            self.write(vault, "index.md", "# Vault\n")

            result = self.run_cli(
                str(memory),
                "--vault-root",
                str(vault),
            )

            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("ERROR: memory root must be inside the vault root", result.stderr)

    def test_index_outside_memory_root_returns_two_without_echoing_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            vault = base / "vault"
            private_index = base / "example-private-index-value-67.md"
            self.write(vault, "index.md", "# Index\n\n- [[index]]\n")
            private_index.write_text("private\n", encoding="utf-8")

            result = self.run_cli(
                str(vault),
                "--index",
                f"../{private_index.name}",
            )

            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertEqual(
                result.stderr,
                "ERROR: index must be inside memory root\n",
            )
            self.assertNotIn(private_index.name, result.stderr)

    def test_help_lists_stable_options(self) -> None:
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        for option in ("--index", "--vault-root", "--index-exclude", "--strict-exit"):
            self.assertIn(option, result.stdout)


if __name__ == "__main__":
    unittest.main()
