from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import unicodedata
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/obsidian-memory/scripts'
sys.path.insert(0, str(SCRIPTS))
import link_audit
import structure_audit


def config(**updates):
    value = dict(schema_version=3, base_id='atlas', index_path='IDX_ATLAS.md',
                 file_namespace='ATLAS', naming_profile='naming-v1',
                 allocation_owner='allocator', last_issued={})
    value.update(updates)
    return value


class NamingV3Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write('IDX_ATLAS.md', '# Atlas\n- [[IDX_ATLAS]]\n')
        self.write_config()

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        return target

    def write_config(self, **updates):
        self.write('CFG_ATLAS.json', json.dumps(config(**updates)))

    def check(self, *args):
        result = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'link_audit.py'),
                                 str(self.root), '--json', '--strict-exit', *args],
                                capture_output=True, text=True)
        return result, json.loads(result.stdout) if result.stdout else {}

    def test_minimum_without_event_log_is_valid(self):
        result, report = self.check()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        result = structure_audit.audit(self.root, profile='naming-v1')
        self.assertEqual(result['NAMING_VIOLATIONS'], [])
        self.assertEqual(result['MISSING_CURRENT_LOG'], [])

    def test_v2_rejects_new_keys(self):
        with self.assertRaises(ValueError):
            link_audit.validate_config(config(schema_version=2))

    def test_v3_config_validation(self):
        cases = [dict(file_namespace='bad-space'), dict(allocation_owner=''),
                 dict(last_issued={'SRV': True}), dict(last_issued={'SVC': 1}),
                 dict(last_issued={'SRV': -1}), dict(parent_base_id=''),
                 dict(naming_profile='unknown'), dict(last_issued=[])]
        for update in cases:
            with self.subTest(update=update), self.assertRaises(ValueError):
                link_audit.validate_config(config(**update))

    def test_legacy_config_has_priority(self):
        self.write('obsidian-memory.config.json', '{"schema_version":1}')
        value, path = link_audit.load_config(self.root, None)
        self.assertEqual(value['schema_version'], 1)
        self.assertEqual(path.name, 'obsidian-memory.config.json')

    def test_ambiguous_config_is_usage_error(self):
        self.write('CFG_OTHER.json', '{}')
        result, _ = self.check()
        self.assertEqual(result.returncode, 2)
        value, _ = link_audit.load_config(self.root, 'CFG_ATLAS.json')
        self.assertEqual(value['schema_version'], 3)

    def card(self, name='SRV_ATLAS-0007_service.md', identity='SRV_ATLAS-0007'):
        self.write(name, f'---\nid: {identity}\n---\n# Service\n')
        self.write('IDX_ATLAS.md', f'# Atlas\n- [[IDX_ATLAS]]\n- [[{name}]]\n')
        self.write_config(last_issued={'SRV': 7})

    def test_gaps_and_highwater_are_allowed(self):
        self.card()
        self.write_config(last_issued={'SRV': 12})
        result, _ = self.check()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_counter_below_issued_is_error(self):
        self.card()
        self.write_config(last_issued={'SRV': 6})
        result, report = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn('COUNTER_BELOW_ISSUED', str(report['NAMING_FINDINGS']))

    def test_missing_counter_is_error(self):
        self.card()
        self.write_config()
        _, report = self.check()
        self.assertIn('COUNTER_BELOW_ISSUED', str(report['NAMING_FINDINGS']))

    def test_duplicate_id_different_topics(self):
        self.card()
        self.write('SRV_ATLAS-0007_other.md', '---\nid: SRV_ATLAS-0007\n---\n# Other\n')
        _, report = self.check('--changed', 'SRV_ATLAS-0007_service.md')
        self.assertIn('DUPLICATE_DOCUMENT_ID', str(report['NAMING_FINDINGS']))

    def test_identity_mismatch(self):
        self.card(identity='SRV_ATLAS-0008')
        _, report = self.check()
        self.assertIn('DOCUMENT_ID_MISMATCH', str(report['NAMING_FINDINGS']))

    def test_service_abbreviation_and_foreign_namespace_rejected(self):
        for name in ('SVC_ATLAS-0001_service.md', 'SRV_OTHER-0001_service.md'):
            self.card(name, name.split('_service')[0])
            _, report = self.check('--changed', name)
            self.assertTrue(report['NAMING_FINDINGS'])

    def test_unrelated_naming_error_is_not_local_error(self):
        self.card()
        self.write('bad-name.md', '# Unrelated\n[[missing]]\n')
        result, _ = self.check('--changed', 'SRV_ATLAS-0007_service.md')
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_todo_ids_count_even_without_separate_cards(self):
        self.write('TODO_ATLAS.md', '# TODO\n- TODO_ATLAS-0004: open question\n')
        _, report = self.check('--changed', 'TODO_ATLAS.md')
        self.assertIn('COUNTER_BELOW_ISSUED', str(report['NAMING_FINDINGS']))

    def test_closed_card_requires_origin_and_own_new_id(self):
        self.card('CPLD_ATLAS-0001_2026-10-04_12-00_work.md', 'CPLD_ATLAS-0001')
        self.write_config(last_issued={'CPLD': 1})
        _, report = self.check()
        self.assertIn('INVALID_SOURCE_ID', str(report['NAMING_FINDINGS']))

    def test_removed_attachment_participates_in_local_check(self):
        self.card()
        self.write('SRV_ATLAS-0007_service.md', '---\nid: SRV_ATLAS-0007\n---\n# Service\n![[ATT_ATLAS-0001_proof.png]]\n')
        _, report = self.check('--removed', 'ATT_ATLAS-0001_proof.png')
        self.assertEqual(len(report['BROKEN_WIKI_EMBEDS']), 1)

    def test_duplicate_attachment_names(self):
        self.write('a/ATT_ATLAS-0001_proof.png', 'proof')
        self.write('b/ATT_ATLAS-0001_proof.png', 'proof')
        self.write_config(last_issued={'ATT': 1})
        _, report = self.check('--changed', 'a/ATT_ATLAS-0001_proof.png')
        self.assertEqual(len(report['DUPLICATE_MANAGED_FILENAMES']), 1)

    def test_diagnostics_hide_targets_json_and_stderr(self):
        secret = 'private-sensitive-value-67'
        self.write('IDX_ATLAS.md', f'# Index\n[[{secret}]]\n[ref](../{secret}.txt)\n')
        result, report = self.check()
        self.assertNotIn(secret, result.stdout + result.stderr)
        self.assertIn('LINE_2', str(report['BROKEN_WIKI_LINKS']))
        result, _ = self.check('--config', '../' + secret)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(secret, result.stderr)

    def test_original_line_after_code_and_fragment(self):
        self.card()
        self.write('SRV_ATLAS-0007_service.md', '---\nid: SRV_ATLAS-0007\n---\n```text\n[[ignore]]\n```\n[[#Missing]]\n')
        _, report = self.check()
        self.assertEqual(report['BROKEN_WIKI_LINKS'], ['SRV_ATLAS-0007_service.md -> BROKEN_WIKILINK_LINE_7'])

    def test_parent_path_inside_boundary_is_valid(self):
        self.write('cards/note.md', '# Note\n![proof](../assets/proof.png)\n')
        self.write('assets/proof.png', 'proof')
        report = link_audit.audit(self.root, 'IDX_ATLAS.md', {})
        self.assertEqual(report['BROKEN_MARKDOWN_ATTACHMENTS'], [])

    def test_unicode_equivalent_attachment_collision(self):
        first = 'ATT_ATLAS-0001_é.png'
        second = unicodedata.normalize('NFD', first)
        self.write(first, 'first')
        self.write(second, 'second')
        if len(list(self.root.glob('*.png'))) != 2:
            self.skipTest('filesystem coalesces Unicode names')
        self.write_config(last_issued={'ATT': 1})
        _, report = self.check('--changed', first)
        self.assertTrue(report['DUPLICATE_MANAGED_FILENAMES'])

    def test_wiki_escape_does_not_fall_back_to_local_basename(self):
        self.write('secret.md', '# Local\n')
        self.write('IDX_ATLAS.md', '# Index\n[[../secret]]\n')
        report = link_audit.audit(self.root, 'IDX_ATLAS.md', {})
        self.assertEqual(len(report['BROKEN_WIKI_LINKS']), 1)

    def test_todo_reference_is_not_duplicate_allocation(self):
        self.write('TODO_ATLAS.md', '# TODO\n## TODO_ATLAS-0004 — verify\nSee TODO_ATLAS-0004 for context.\n')
        self.write_config(last_issued={'TODO': 4})
        _, report = self.check('--changed', 'TODO_ATLAS.md')
        self.assertNotIn('DUPLICATE_DOCUMENT_ID', str(report['NAMING_FINDINGS']))

    def test_new_lifecycle_code_is_checked(self):
        name = 'cards/PLN_ATLAS-0001_2026-10-04_12-00_work.md'
        self.card(name, 'PLN_ATLAS-0001')
        self.write_config(last_issued={'PLN': 1}, disallowed_lifecycle_codes=[{'code': 'PLN', 'path_prefixes': ['cards']}])
        _, report = self.check('--changed', name)
        self.assertTrue(report['DISALLOWED_LIFECYCLE_CODE_FINDINGS'])

    def test_bad_arguments_do_not_echo_sensitive_values(self):
        result, _ = self.check('--private-sensitive-value-67')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('private-sensitive-value-67', result.stderr)


if __name__ == '__main__':
    unittest.main()
