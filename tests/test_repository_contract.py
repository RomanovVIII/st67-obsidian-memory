#!/usr/bin/env python3
"""Repository packaging, attribution, and privacy contracts."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "obsidian-memory"


class RepositoryContractTests(unittest.TestCase):
    def test_required_repository_files_exist(self) -> None:
        required = {
            "AGENTS.md",
            "README.md",
            "README.ru.md",
            "LICENSE",
            "CHANGELOG.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            ".gitignore",
            ".github/workflows/ci.yml",
        }
        missing = sorted(name for name in required if not (REPO_ROOT / name).is_file())
        self.assertEqual(missing, [])

    def test_distributable_skill_contains_only_runtime_files(self) -> None:
        actual = {
            path.relative_to(SKILL_ROOT).as_posix()
            for path in SKILL_ROOT.rglob("*")
            if path.is_file()
        }
        self.assertEqual(
            actual,
            {
                "SKILL.md",
                "agents/openai.yaml",
                "references/onboarding.md",
                "scripts/link_audit.py",
                "scripts/structure_audit.py",
            },
        )

    def test_plugin_manifest_is_deferred(self) -> None:
        self.assertFalse((REPO_ROOT / ".codex-plugin" / "plugin.json").exists())

    def test_license_and_attribution_are_present(self) -> None:
        license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
        readme_en = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        readme_ru = (REPO_ROOT / "README.ru.md").read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("Copyright (c) 2026 Master V", license_text)
        self.assertIn("Developer: Studio 67", readme_en)
        self.assertIn("Author and copyright holder: Master V", readme_en)
        self.assertIn("Technical co-developer: MacMaster", readme_en)
        self.assertIn("Разработчик: Studio 67", readme_ru)
        self.assertIn("Автор и правообладатель: Master V", readme_ru)
        self.assertIn("Технический соразработчик: MacMaster", readme_ru)

    def test_repository_has_no_email_addresses(self) -> None:
        email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
        findings = []
        for path in REPO_ROOT.rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                text = path.read_text(encoding="utf-8", errors="replace")
                if email.search(text):
                    findings.append(path.relative_to(REPO_ROOT).as_posix())
        self.assertEqual(findings, [])

    def test_openai_metadata_matches_public_skill_name(self) -> None:
        metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "Obsidian Memory"', metadata)
        self.assertIn("$obsidian-memory", metadata)
        self.assertIn("organize", metadata.lower())


if __name__ == "__main__":
    unittest.main()
