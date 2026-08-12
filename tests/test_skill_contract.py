#!/usr/bin/env python3
"""Contract tests for the distributable Obsidian Memory skill."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "obsidian-memory"
SKILL_PATH = SKILL_ROOT / "SKILL.md"


class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill_text = SKILL_PATH.read_text(encoding="utf-8")
        cls.onboarding_text = (SKILL_ROOT / "references" / "onboarding.md").read_text(
            encoding="utf-8"
        )

    def test_frontmatter_contract(self) -> None:
        match = re.match(r"^---\n(.*?)\n---", self.skill_text, re.DOTALL)
        self.assertIsNotNone(match)
        frontmatter = match.group(1)
        name = re.search(r"^name: (.+)$", frontmatter, re.MULTILINE).group(1)
        description = re.search(
            r"^description: (.+)$", frontmatter, re.MULTILINE
        ).group(1)
        self.assertEqual(name, "obsidian-memory")
        self.assertEqual(SKILL_ROOT.name, name)
        self.assertRegex(name, r"^[a-z0-9-]+$")
        self.assertLessEqual(len(name), 64)
        self.assertLessEqual(len(description), 1024)
        self.assertNotRegex(description, r"[<>]")
        self.assertIn("set up", description.lower())
        self.assertIn("unstructured", description.lower())

    def test_local_schema_is_authoritative(self) -> None:
        self.assertIn("local `AGENTS.md` and `rules/`", self.skill_text)
        self.assertIn("Do not add optional sections", self.skill_text)

    def test_separate_vaults_and_no_cross_vault_wikilinks(self) -> None:
        self.assertIn("Never create a Wikilink to another vault", self.skill_text)
        self.assertIn("Do not assume one shared vault", self.skill_text)

    def test_existing_local_schema_remains_authoritative(self) -> None:
        self.assertIn("A journal is optional", self.skill_text)
        self.assertIn("Do not retrofit the onboarding schema", self.skill_text)

    def test_four_operating_modes_are_distinct(self) -> None:
        for mode in ("Onboarding", "Maintenance", "Query", "Audit"):
            self.assertRegex(self.skill_text, rf"(?m)^- \*\*{mode}:\*\*")

    def test_onboarding_requires_explanation_and_confirmation(self) -> None:
        self.assertIn("Read-only discovery", self.onboarding_text)
        self.assertIn("Show the proposed structure", self.onboarding_text)
        self.assertIn("Wait for explicit approval", self.onboarding_text)
        self.assertIn("Purpose:", self.onboarding_text)
        self.assertIn("Contents:", self.onboarding_text)

    def test_onboarding_contains_adaptive_document_templates(self) -> None:
        self.assertIn("Use the user's language", self.onboarding_text)
        for heading in (
            "## Template catalog",
            "### Root AGENTS.md template",
            "### Common frontmatter template",
            "### Numbered frontmatter template",
            "### Main index template",
            "### Current TODO template",
            "### Accumulated decisions template",
            "### Monthly log template",
            "### Incident card template",
            "### Entity card template",
            "### Database maintenance rule template",
            "### Link workflow rule template",
            "### Setup proposal template",
        ):
            self.assertIn(heading, self.onboarding_text)
        self.assertIn("Never replace an existing `AGENTS.md`", self.onboarding_text)

    def test_setup_proposal_requires_verified_exact_scope(self) -> None:
        self.assertIn("enumerate every path individually", self.onboarding_text)
        self.assertIn("derive it from the final path inventory", self.onboarding_text)

    def test_onboarding_standard_excludes_daily_notes(self) -> None:
        self.assertNotIn("`daily/`", self.onboarding_text)
        for optional_folder in (
            "`attachments/`",
            "`archive/`",
            "`templates/`",
            "`references/`",
            "`plans/`",
            "`reports/`",
            "`workflows/`",
            "`projects/`",
        ):
            self.assertIn(optional_folder, self.onboarding_text)

    def test_non_wiki_material_is_excluded(self) -> None:
        for term in ("source code", "dependencies", "builds", "test outputs", "secrets"):
            self.assertIn(term, self.skill_text)

    def test_skill_has_no_user_specific_absolute_paths(self) -> None:
        user_roots = (
            "/" + "Users" + "/",
            "/" + "home" + "/",
            "C:" + "\\" + "Users" + "\\",
        )
        for path in SKILL_ROOT.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace")
                for root in user_roots:
                    self.assertNotIn(root, text, msg=str(path.relative_to(REPO_ROOT)))


if __name__ == "__main__":
    unittest.main()
