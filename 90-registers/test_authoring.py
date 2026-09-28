"""Focused tests for GOLDEN's supported canonical-record authoring doorway."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import preservation_engine as e


AS_OF = '2026-09-25T00:00:00+00:00'


class GoldenAuthoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_root = Path(__file__).resolve().parents[1]

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='andi-golden-authoring-')
        self.base = Path(self.temp.name)
        self.root = self.base / 'preservation'
        shutil.copytree(self.source_root, self.root)
        self.request_path = self.base / 'add-record.json'

    def tearDown(self):
        self.temp.cleanup()

    def request(self, **overrides):
        value = {
            'schema': 1,
            'stable_id': 'CAN-CAR-014',
            'path': '10-andi-car/history/AUTHORED-RECORD.md',
            'title': 'Authored canonical record',
            'type': 'historical',
            'record_type': 'canonical_record',
            'authority': 'PROVISIONAL',
            'status': 'UNRECONCILED',
            'body': '# Authored canonical record\nBounded authoring payload café Ω.\n',
            'source_ids': ['SRC-001'],
            'projects': ['ANDI_CAR', 'ANDI_PRESERVATION'],
            'human_summary': 'Focused supported-authoring integration record',
            'note': 'Canonical record authored through the supported boundary.',
            'relationships': [
                {'from': 'CAN-CAR-014', 'to': 'CAN-CAR-001', 'type': 'references'}
            ],
            'activity': {
                'timestamp': '2026-09-25T00:00:00Z',
                'type': 'edit',
                'description': 'Focused canonical authoring test record created.'
            }
        }
        value.update(overrides)
        return value

    def files(self):
        return e.snapshot(self.root.absolute())

    def obj(self, rel):
        return e.decode((self.root / rel).read_bytes())

    def reject(self, request, message=None):
        before = self.files()
        with self.assertRaises(e.Invalid) as caught:
            e.add_record(self.root, request, AS_OF)
        if message is not None:
            self.assertEqual(str(caught.exception), message)
        self.assertEqual(before, self.files())
        self.assertFalse(e.paths(self.root)[0].exists())
        self.assertFalse(e.paths(self.root)[1].exists())

    def existing_records(self):
        result = {}
        for row in self.obj(e.REGISTER)['records']:
            data = (self.root / row['path']).read_bytes()
            fields, _, offset = e.header(data)
            result[row['id']] = (fields, data[offset:])
        return result

    def assert_existing_semantics(self, before):
        after = self.existing_records()
        self.assertEqual(set(before), set(after) - {'CAN-CAR-014'})
        for rid, (fields, body) in before.items():
            current_fields, current_body = after[rid]
            self.assertEqual(body, current_body, rid)
            self.assertEqual({k: v for k, v in fields.items() if k != 'ACTIVITY'},
                             {k: v for k, v in current_fields.items() if k != 'ACTIVITY'}, rid)

    def test_valid_provisional_creation_views_readback_preservation_and_idempotence(self):
        before = self.existing_records()
        result = e.add_record(self.root, self.request(), AS_OF)
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(result['record_id'], 'CAN-CAR-014')
        self.assertEqual(result['path'], '10-andi-car/history/AUTHORED-RECORD.md')
        authored = e.read_record(self.root, 'CAN-CAR-014')
        fields, _, offset = e.header(authored)
        self.assertEqual(fields, {'STABLE_ID': 'CAN-CAR-014', 'SOURCE': 'SRC-001',
                                  'AUTHORITY': 'PROVISIONAL', 'STATUS': 'UNRECONCILED',
                                  'ACTIVITY': 'WARM'})
        self.assertEqual(authored[offset:].decode(), self.request()['body'])
        self.assertEqual(result['sha256'], e.digest(authored))

        register = self.obj(e.REGISTER)
        row = next(row for row in register['records'] if row['id'] == 'CAN-CAR-014')
        self.assertEqual(register['total'], 23)
        self.assertEqual(row['authority'], 'PROVISIONAL')
        self.assertEqual(row['status'], 'UNRECONCILED')
        self.assertEqual(row['source_ids'], ['SRC-001'])
        machine = self.obj(e.MACHINE)
        node = next(node for node in machine['nodes'] if node['id'] == 'CAN-CAR-014')
        self.assertEqual(node['projects'], ['ANDI_CAR', 'ANDI_PRESERVATION'])
        self.assertIn(self.request()['relationships'][0], machine['relationships'])
        self.assertEqual(self.obj(e.RETRIEVAL)['total_records'], 23)
        self.assertIn('CAN-CAR-014', (self.root / e.SYSTEM_MAP).read_text(encoding='utf-8'))
        self.assertIn('CAN-CAR-014', (self.root / e.PROJECT_TREE).read_text(encoding='utf-8'))
        self.assertEqual(self.obj(e.MISSING)['missing'], [])
        self.assert_existing_semantics(before)
        governing = e.read_record(self.root, 'CAN-GOV-001')
        self.assertEqual(e.header(governing)[0]['AUTHORITY'], 'GOVERNING_RULE')
        self.assertEqual(e.rebuild(self.root, AS_OF), {'changed': [], 'status': 'no_change'})

    def test_established_creation_is_supported(self):
        result = e.add_record(self.root, self.request(authority='ESTABLISHED'), AS_OF)
        fields = e.header(e.read_record(self.root, 'CAN-CAR-014'))[0]
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(fields['AUTHORITY'], 'ESTABLISHED')
        self.assertEqual(fields['STATUS'], 'UNRECONCILED')

    def test_governing_unreconciled_is_refused_specifically_at_authority_boundary(self):
        request = self.request(authority='GOVERNING')
        self.assertEqual(request['status'], 'UNRECONCILED')
        self.reject(request, 'New record authority must be PROVISIONAL or ESTABLISHED')

    def test_duplicate_stable_identity_and_case_aliased_path_are_refused(self):
        self.reject(self.request(stable_id='CAN-CAR-013'), 'Stable ID already exists')
        self.reject(self.request(path='10-andi-car/current/compact-current-state.md'),
                    'Canonical path already exists')
        e.add_record(self.root, self.request(), AS_OF)
        self.reject(self.request(), 'Stable ID already exists')

    def test_missing_unknown_malformed_and_invalid_requests_are_refused(self):
        request = self.request()
        del request['title']
        self.reject(request, 'Authoring request has missing/unknown fields')
        request = self.request(extra='not allowed')
        self.reject(request, 'Authoring request has missing/unknown fields')
        self.reject(self.request(schema=True), 'Unsupported authoring request schema')
        self.reject(self.request(body='not headed'),
                    'Record body needs a Markdown heading and content')
        self.reject(self.request(status='CURRENT'), 'New record must start UNRECONCILED')
        self.reject(self.request(stable_id='CAN-CAR-015'),
                    'Stable ID is not the next sequential ID for its prefix')
        self.reject(self.request(path='30-lab-mk1/current/WRONG-PREFIX.md'),
                    'Canonical path does not match the stable-ID project prefix')
        self.reject(self.request(activity={
            'timestamp': '2026-09-26T00:00:00Z', 'type': 'edit', 'description': 'future'}),
            'Activity timestamp is later than the rebuild as-of')

    def test_provenance_source_validation(self):
        self.reject(self.request(source_ids=['SRC-999']),
                    'Canonical record references unknown source identity')
        self.reject(self.request(source_ids=['SRC-001', 'SRC-001']),
                    'Invalid/duplicate source identity')

    def test_relationship_validation(self):
        self.reject(self.request(relationships=[
            {'from': 'CAN-CAR-014', 'to': 'CAN-CAR-999', 'type': 'references'}]),
            'Invalid relationship endpoint/type')
        self.reject(self.request(relationships=[
            {'from': 'CAN-CAR-001', 'to': 'CAN-GOV-001', 'type': 'references'}]),
            'Authored relationship must involve the new record')
        edge = {'from': 'CAN-CAR-014', 'to': 'CAN-CAR-001', 'type': 'references'}
        self.reject(self.request(relationships=[edge, edge]), 'Duplicate relationship')
        self.reject(self.request(relationships=[
            {'from': 'CAN-CAR-014', 'to': 'CAN-CAR-001', 'type': 'supersedes'}]),
            'Supersession requires the separate two-record maintenance procedure')

    def test_ordinary_failures_roll_back_exactly(self):
        for fault in ('before_publish', 'after_first'):
            with self.subTest(fault=fault):
                before = self.files()
                with self.assertRaises(OSError):
                    e.add_record(self.root, self.request(), AS_OF, fault=fault)
                self.assertEqual(before, self.files())
                self.assertFalse((self.root / self.request()['path']).exists())
                self.assertFalse(e.paths(self.root)[0].exists())
                self.assertFalse(e.paths(self.root)[1].exists())

    def test_cli_success_and_transient_request_non_persistence(self):
        self.request_path.write_text(json.dumps(self.request()), encoding='utf-8')
        result = subprocess.run(
            [sys.executable, '-B', str(self.root / '90-registers/preservation_engine.py'),
             'add', str(self.root), str(self.request_path), '--as-of', AS_OF],
            capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['record_id'], 'CAN-CAR-014')
        self.assertTrue(self.request_path.is_file())
        self.assertNotIn('add-record.json', self.files())

        inside = self.root / 'authoring-request.json'
        inside.write_text(json.dumps(self.request(stable_id='CAN-CAR-015',
                                                  path='10-andi-car/history/SECOND.md')),
                          encoding='utf-8')
        before = self.files()
        refused = subprocess.run(
            [sys.executable, '-B', str(self.root / '90-registers/preservation_engine.py'),
             'add', str(self.root), str(inside), '--as-of', AS_OF],
            capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(refused.returncode, 2)
        self.assertIn('outside the Preservation root', refused.stderr)
        self.assertEqual(before, self.files())

    def test_malformed_json_request_is_refused_without_change(self):
        self.request_path.write_text('{"schema": 1,', encoding='utf-8')
        before = self.files()
        result = subprocess.run(
            [sys.executable, '-B', str(self.root / '90-registers/preservation_engine.py'),
             'add', str(self.root), str(self.request_path), '--as-of', AS_OF],
            capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2)
        self.assertIn('Malformed UTF-8 JSON', result.stderr)
        self.assertEqual(before, self.files())

    def test_interrupted_uncommitted_generation_recovers_by_rollback(self):
        before = self.files()
        self.request_path.write_text(json.dumps(self.request()), encoding='utf-8')
        result = subprocess.run(
            [sys.executable, '-B', str(self.root / '90-registers/preservation_engine.py'),
             'add', str(self.root), str(self.request_path), '--as-of', AS_OF,
             '--fault', 'crash_after_first'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 73, result.stderr)
        self.assertTrue(e.paths(self.root)[0].exists())
        self.assertTrue(e.paths(self.root)[1].exists())
        with self.assertRaises(e.Invalid):
            e.add_record(self.root, self.request(), AS_OF)
        self.assertEqual(e.recover(self.root, writer_stopped=True), 'rolled_back')
        self.assertEqual(before, self.files())

    def test_interrupted_verified_generation_recovers_by_retaining_commit(self):
        self.request_path.write_text(json.dumps(self.request()), encoding='utf-8')
        result = subprocess.run(
            [sys.executable, '-B', str(self.root / '90-registers/preservation_engine.py'),
             'add', str(self.root), str(self.request_path), '--as-of', AS_OF,
             '--fault', 'crash_after_commit'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 74, result.stderr)
        self.assertEqual(e.recover(self.root, writer_stopped=True), 'kept_committed')
        fields = e.header(e.read_record(self.root, 'CAN-CAR-014'))[0]
        self.assertEqual(fields['STABLE_ID'], 'CAN-CAR-014')
        self.assertEqual(e.rebuild(self.root, AS_OF), {'changed': [], 'status': 'no_change'})


if __name__ == '__main__':
    unittest.main(verbosity=2)