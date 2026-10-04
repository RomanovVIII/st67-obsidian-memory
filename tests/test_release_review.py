from __future__ import annotations
import json
import os
import subprocess
import sys
import tempfile
import unittest
import unicodedata
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/obsidian-memory/scripts/link_audit.py'

class ReleaseReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write('index.md', '# Index\n[[index]]\n[[note]]\n')
        self.write('note.md', '# Note\n[[missing]]\n')

    def write(self, path, text):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')

    def check(self, *args):
        r = subprocess.run([sys.executable, '-B', str(SCRIPT), str(self.root), '--json', '--strict-exit', *args], capture_output=True, text=True)
        return r, json.loads(r.stdout) if r.stdout else {}

    @unittest.skipUnless(os.name == 'nt', 'Windows case-insensitive input')
    def test_changed_case_selects_actual_card(self):
        r, report = self.check('--changed', 'NOTE.md')
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertEqual(report['AUDIT_SCOPE']['checked_documents'], ['note.md'])
        self.assertTrue(report['BROKEN_WIKI_LINKS'])

    def test_changed_nfd_selects_actual_card(self):
        name = unicodedata.normalize('NFD', 'é.md')
        self.write(name, '# Card\n[[missing]]\n')
        r, report = self.check('--changed', name)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertEqual(report['AUDIT_SCOPE']['checked_documents'], ['é.md'])
        self.assertTrue(report['BROKEN_WIKI_LINKS'])

    def test_unrelated_escaping_policy_link_does_not_break_point_check(self):
        self.write('note.md', '# Good\n')
        self.write('todo.md', '[bad](../../outside.md)\n')
        self.write('obsidian-memory.config.json', json.dumps({'schema_version':2, 'disallowed_lifecycle_codes':[{'code':'HND','path_prefixes':['cards']}]}))
        r, report = self.check('--changed', 'note.md')
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(report['STRICT_PROBLEM_COUNT'], 0)

    def test_index_heading_not_emitted_in_diagnostics(self):
        marker = 'private-sensitive-heading-67'
        self.write('note.md', '# Note\n')
        self.write('index.md', '# Index\n## ' + marker + '\n[[note]]\n[[index]]\n')
        self.write('obsidian-memory.config.json', json.dumps({'schema_version':2, 'index_section_rules':[{'heading':'Expected','path_prefixes':['note.md'],'lifecycle_codes':[]}]}))
        r, report = self.check()
        self.assertNotIn(marker, r.stdout + r.stderr)
        self.assertTrue(report['INDEX_POLICY_FINDINGS'])

    def test_wiki_absolute_with_whitespace_is_broken(self):
        self.write('note.md', '# Note\n')
        self.write('index.md', '[[ /note]]\n')
        _, report = self.check('--changed', 'index.md')
        self.assertTrue(report['BROKEN_WIKI_LINKS'])

    def test_markdown_missing_fragment_is_broken(self):
        self.write('note.md', '# Note\n[frag](note.md#Missing)\n')
        _, report = self.check('--changed', 'note.md')
        self.assertEqual(len(report['BROKEN_MARKDOWN_LINKS']), 1)

    def test_inline_code_heading_uses_visible_text(self):
        self.write('note.md', '# Command `foo`\n[[#Command foo]]\n')
        _, report = self.check('--changed', 'note.md')
        self.assertEqual(report['BROKEN_WIKI_LINKS'], [])

    def test_same_sequence_number_cannot_use_extra_padding(self):
        self.write('CFG_ATLAS.json', json.dumps({'schema_version':3,'base_id':'atlas','file_namespace':'ATLAS','naming_profile':'naming-v1','allocation_owner':'owner','last_issued':{'SRV':1},'index_path':'IDX_ATLAS.md'}))
        for identity, topic in [('SRV_ATLAS-0001','a'), ('SRV_ATLAS-00001','b')]:
            self.write(identity + '_' + topic + '.md', '---\nid: ' + identity + '\n---\n# Service\n')
        self.write('IDX_ATLAS.md', '# Index\n[[IDX_ATLAS]]\n[[SRV_ATLAS-0001_a]]\n[[SRV_ATLAS-00001_b]]\n')
        _, report = self.check('--config', 'CFG_ATLAS.json', '--changed', 'SRV_ATLAS-00001_b.md')
        self.assertTrue(report['NAMING_FINDINGS'])

    def naming_config(self, counters):
        self.write('CFG_ATLAS.json', json.dumps({'schema_version':3,'base_id':'atlas','file_namespace':'ATLAS','naming_profile':'naming-v1','allocation_owner':'owner','last_issued':counters,'index_path':'IDX_ATLAS.md'}))

    def test_nfd_numbered_card_name_is_valid(self):
        self.naming_config({'SRV':1})
        name = unicodedata.normalize('NFD', 'SRV_ATLAS-0001_café.md')
        self.write(name, '---\nid: SRV_ATLAS-0001\n---\n# Service\n')
        self.write('IDX_ATLAS.md', '# Index\n[[IDX_ATLAS]]\n[[SRV_ATLAS-0001_café]]\n')
        _, report = self.check('--config', 'CFG_ATLAS.json', '--changed', name)
        self.assertEqual(report['NAMING_FINDINGS'], [])

    def test_completed_origin_contributes_reserved_highwater(self):
        self.naming_config({'CPLD':1,'PLN':0})
        name = 'CPLD_ATLAS-0001_2026-10-04_12-00_work.md'
        self.write(name, '---\nid: CPLD_ATLAS-0001\nsource_id: PLN_ATLAS-0100\n---\n# Completed\n')
        self.write('IDX_ATLAS.md', '# Index\n[[IDX_ATLAS]]\n[[' + name + ']]\n')
        _, report = self.check('--config', 'CFG_ATLAS.json', '--changed', name)
        self.assertIn('COUNTER_BELOW_ISSUED', str(report['NAMING_FINDINGS']))

    def test_schema_version_requires_integer(self):
        for value in ([], {}, True, 1.0):
            self.write('obsidian-memory.config.json', json.dumps({'schema_version':value}))
            result, _ = self.check()
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_raw_markdown_original_does_not_require_modified_frontmatter(self):
        self.naming_config({'RAW':1})
        name = 'RAW_ATLAS-0001_original.md'
        self.write(name, '# Original source\n')
        self.write('IDX_ATLAS.md', '# Index\n[[IDX_ATLAS]]\n[[' + name + ']]\n')
        _, report = self.check('--config', 'CFG_ATLAS.json', '--changed', name)
        self.assertEqual(report['NAMING_FINDINGS'], [])

    def test_legacy_positional_exclusion_does_not_enable_network(self):
        sys.path.insert(0, str(SCRIPT.parent))
        from link_audit import audit
        from unittest.mock import patch
        self.write('note.md', '# Note\nhttps://example.invalid/check\n')
        with patch('link_audit.check_url', side_effect=AssertionError('network must remain disabled')):
            audit(self.root, 'index.md', self.root, ['raw/*'])

    def test_binary_wiki_link_and_embed_counter(self):
        self.write('proof.pdf', 'proof')
        self.write('note.md', '[[proof.pdf]]\n![[image.png]]\n')
        self.write('a/image.png', 'a')
        self.write('b/image.png', 'b')
        _, report = self.check('--changed', 'note.md')
        self.assertEqual(report['BROKEN_WIKI_LINKS'], [])
        self.assertEqual(len(report['AMBIGUOUS_WIKI_EMBEDS']), 1)
        self.assertEqual(report['AMBIGUOUS_WIKI_LINKS'], [])

    def test_removed_binary_short_link_cannot_retarget(self):
        self.write('note.md', '[[proof.pdf]]\n')
        self.write('b/proof.pdf', 'remaining')
        _, report = self.check('--removed', 'a/proof.pdf')
        self.assertTrue(report['REMOVAL_LINK_FINDINGS'])

    def test_extensionless_attachment_cannot_shadow_markdown(self):
        self.write('note.md', '# Note\n')
        self.write('note', 'binary')
        self.write('index.md', '[[note#Missing]]\n')
        _, report = self.check('--changed', 'index.md')
        self.assertTrue(report['BROKEN_WIKI_LINKS'])

    def test_windows_index_exclusion_slashes_remain_compatible(self):
        self.write('note.md', '# Note\n')
        self.write('raw/source.md', '# Source\n')
        _, report = self.check('--index-exclude', 'raw\\*.md')
        self.assertEqual(report['MISSING_FROM_INDEX'], [])

    def test_todo_entries_require_positive_canonical_sequence(self):
        self.naming_config({'TODO':1})
        self.write('IDX_ATLAS.md', '# Index\n[[IDX_ATLAS]]\n[[TODO_ATLAS]]\n')
        self.write('TODO_ATLAS.md', '# TODO\n## TODO_ATLAS-0001 — one\n## TODO_ATLAS-00001 — repeated\n## TODO_ATLAS-0000 — zero\n')
        _, report = self.check('--config','CFG_ATLAS.json','--changed','TODO_ATLAS.md')
        self.assertIn('NONCANONICAL_SEQUENCE_NUMBER', str(report['NAMING_FINDINGS']))

    def test_network_reason_cannot_inject_sensitive_line_diagnostic(self):
        sys.path.insert(0, str(SCRIPT.parent))
        from link_audit import audit, validate_config
        from unittest.mock import patch
        url = 'https://example.invalid/?token=private-sensitive-url-value-67'
        self.write('note.md', url + '\n')
        with patch('link_audit.request_url', return_value=(False,500,'Line 1: ' + url)):
            report = audit(self.root,'index.md',validate_config({'schema_version':2}), True)
        self.assertNotIn('private-sensitive-url-value-67', json.dumps(report))

    def test_code_block_does_not_join_setext_heading_lines(self):
        self.write('note.md', 'Bogus\n```text\ncode\n```\n---\n[[#Bogus]]\n')
        _, report = self.check('--changed', 'note.md')
        self.assertEqual(len(report['BROKEN_WIKI_LINKS']), 1)

    def test_markdown_conventional_slug_anchor(self):
        self.write('note.md', '# Command foo\n[valid](#command-foo)\n')
        _, report = self.check('--changed', 'note.md')
        self.assertEqual(report['BROKEN_MARKDOWN_LINKS'], [])

    def test_container_fences_preserve_real_links_and_original_lines(self):
        for body in (
            '# Note\n- ```text\n  [[inside-code]]\n  ```\n[[real-missing]]\n',
            '# Note\n> ```text\n> [[inside-code]]\n> ```\n[[real-missing]]\n',
            '# Note\n- > ~~~~text\n  > [[inside-code]]\n  > ~~~~\n[[real-missing]]\n',
            '# Note\n123. ```text\n     [[inside-code]]\n     ```\n[[real-missing]]\n',
        ):
            with self.subTest(body=body):
                self.write('note.md', body)
                _, report = self.check('--changed', 'note.md')
                self.assertEqual(len(report['BROKEN_WIKI_LINKS']), 1)
                self.assertIn('BROKEN_WIKILINK_LINE_5', str(report['BROKEN_WIKI_LINKS']))

    def test_unclosed_container_fence_ends_at_container_boundary(self):
        for body in (
            '# Note\n- ```text\n  [[inside-code]]\n[[real-missing]]\n',
            '# Note\n> ```text\n> [[inside-code]]\n[[real-missing]]\n',
        ):
            with self.subTest(body=body):
                self.write('note.md', body)
                _, report = self.check('--changed', 'note.md')
                self.assertEqual(len(report['BROKEN_WIKI_LINKS']), 1)
                self.assertIn('BROKEN_WIKILINK_LINE_4', str(report['BROKEN_WIKI_LINKS']))

if __name__ == '__main__':
    unittest.main()
