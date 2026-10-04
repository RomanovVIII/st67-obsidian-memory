"""Routing, compatibility and privacy contracts for the public skill."""
from __future__ import annotations
import re
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / 'skills/obsidian-memory'
sys.path.insert(0, str(ROOT / 'scripts'))

class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / 'SKILL.md').read_text(encoding='utf-8')

    def test_frontmatter(self):
        match = re.match(r'^---\nname: obsidian-memory\ndescription: ([^\n]+)\n---', self.text)
        self.assertIsNotNone(match)
        self.assertLessEqual(len(match[1]), 1024)
        self.assertNotRegex(match[1], r'[<>]')
        self.assertEqual((ROOT / 'VERSION').read_text().strip(), '0.2.0')

    def test_conditional_routes(self):
        for file in ('maintenance.md', 'creation.md', 'migration.md', 'naming-and-numbering.md', 'link-workflow.md', 'thread-completion.md'):
            self.assertIn('references/' + file, self.text)
            self.assertTrue((ROOT / 'references' / file).is_file())
        self.assertNotIn('references/onboarding.md', self.text)
        self.assertLess(len(self.text), 6500)

    def test_existing_schema_and_ownership(self):
        for phrase in ('paths, owners and lifecycle', 'Never resolve wiki-links across bases', 'Existing mandatory local procedures', 'existing names/lifecycle stay'):
            self.assertIn(phrase, self.text)

    def test_context_reuse_and_targeted_search(self):
        for phrase in ('do not re-read unchanged files', 'Do not create absent roles or read every card', 'No persistent caches or thread registries', 'Historical decisions do not prove current infrastructure state'):
            self.assertIn(phrase, self.text)

    def test_authority_and_side_effects(self):
        for term in ('without repeated approval', 'write nothing and contact no network by default', 'No network without an explicit URL-check request', 'no output file without an explicit report destination'):
            self.assertIn(term, self.text)

    def test_creation_minimum(self):
        text = (ROOT / 'references/creation.md').read_text(encoding='utf-8')
        for term in ('IDX_', 'CFG_', 'first journaled event', 'Do not create empty monthly logs', 'not mandatory duplicated RUL', 'Never replace an existing AGENTS'):
            self.assertIn(term, text)
        self.assertIn('explicitly authorized', (ROOT / 'references/migration.md').read_text(encoding='utf-8'))

    def test_vocabulary(self):
        from naming import TYPES
        text = (ROOT / 'references/naming-and-numbering.md').read_text(encoding='utf-8')
        self.assertEqual(TYPES, set('IDX CFG LOG TODO HOST DEV APP SRV NET STO PLN CPLD TRB CTRB DEC RSR RPT RUL ATT RAW TMP'.split()))
        for typ in TYPES:
            self.assertIn('| ' + typ + ' |', text)

    def test_completion(self):
        text = (ROOT / 'references/thread-completion.md').read_text(encoding='utf-8')
        for term in ('direct instruction', 'matching cryptographic checksum', 'created by this agent', 'Do not archive', 'Do not treat silence as deletion approval'):
            self.assertIn(term, text)

    def test_exclusions_and_privacy(self):
        for term in ('Source code', 'dependencies', 'builds', 'test outputs', 'secrets'):
            self.assertIn(term, self.text)
        roots = ('/' + 'Users' + '/', '/' + 'home' + '/', 'C:' + chr(92) + 'Users' + chr(92))
        for path in ROOT.rglob('*'):
            if path.is_file():
                text = path.read_text(encoding='utf-8', errors='replace')
                for root in roots:
                    self.assertNotIn(root, text, path.name)

if __name__ == '__main__':
    unittest.main()
