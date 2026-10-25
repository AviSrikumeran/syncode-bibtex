from http.client import HTTPConnection
import json
import threading
import unittest

from review_demo import ReviewServer, analyze_output


class ReviewerDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ReviewServer(('127.0.0.1', 0), offline=True)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, payload=None, headers=None):
        connection = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request(method, path, body=json.dumps(payload) if payload is not None else None,
                           headers=headers or {})
        response = connection.getresponse()
        status, body = response.status, response.read()
        connection.close()
        return status, json.loads(body)

    def test_fence_extraction_does_not_repair_bibtex(self):
        valid = analyze_output(self.server.parser, '```bibtex\n@misc{k,title={x}}\n```')
        self.assertFalse(valid['raw_valid'])
        self.assertTrue(valid['extracted_valid'])
        broken = analyze_output(self.server.parser, '```bibtex\n@misc{k,title={x}\n```')
        self.assertFalse(broken['extracted_valid'])

    def test_validation_endpoint_accepts_nested_groups(self):
        status, body = self.request('POST', '/api/validate', {'source': '@misc{k,title={a {b}}}'})
        self.assertEqual(status, 200)
        self.assertTrue(body['raw_valid'])
        self.assertIn('braced', body['tree'])

    def test_validation_endpoint_rejects_incomplete_input(self):
        status, body = self.request('POST', '/api/validate', {'source': '@misc{k,title={x}'})
        self.assertEqual(status, 200)
        self.assertFalse(body['raw_valid'])
        self.assertIsNone(body['tree'])

    def test_non_text_request_is_rejected(self):
        status, body = self.request('POST', '/api/validate', {'source': ['not', 'text']})
        self.assertEqual(status, 400)
        self.assertIn('source', body['error'])

    def test_cross_origin_generation_is_rejected(self):
        status, _ = self.request('POST', '/api/run', headers={'Origin': 'https://example.org'})
        self.assertEqual(status, 403)

    def test_concurrent_model_run_is_rejected(self):
        with self.server.job_lock:
            self.server.job['status'] = 'running'
        try:
            status, body = self.request('POST', '/api/run')
            self.assertEqual(status, 409)
            self.assertFalse(body['started'])
        finally:
            with self.server.job_lock:
                self.server.job['status'] = 'idle'

    def test_evidence_is_revalidated(self):
        status, body = self.request('GET', '/api/evidence')
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(body['generations']), 6)
        for record in body['generations']:
            self.assertEqual(record['assessment']['raw_valid'], record['valid'])

    def test_no_arbitrary_file_access(self):
        status, _ = self.request('GET', '/../.venv/pyvenv.cfg')
        self.assertEqual(status, 404)

    def test_boundary_report_matches_current_grammar(self):
        status, body = self.request('GET', '/api/bounds')
        self.assertEqual(status, 200)
        self.assertEqual(body['after']['grammar_sha256'], body['active_grammar_sha256'])
        self.assertTrue(all(row['matched_expectation'] for row in body['after']['cases']))
        self.assertTrue(any(not row['matched_expectation'] for row in body['before']['cases']))

    def test_case_catalog_exposes_all_fixtures_and_requirements(self):
        status, body = self.request('GET', '/api/cases')
        self.assertEqual(status, 200)
        self.assertEqual(len(body['cases']), 224)
        self.assertEqual(len({case['case_id'] for case in body['cases']}), 224)
        self.assertEqual(sum(case['category'] == 'provided-assignment' for case in body['cases']), 7)
        self.assertEqual(sum('R1' in case['requirements'] and case['category'] == 'regression-valid' for case in body['cases']), 14)
        large = next(case for case in body['cases'] if case['case_id'] == 'value-length-valid/characters-100000')
        self.assertIsNone(large['source'])
        self.assertEqual(large['characters'], 100017)

    def test_original_stress_fixtures_run_without_truncating_or_recursing_preview(self):
        for case_id, characters in [('nesting-valid/depth-1000', 2018),
                                    ('value-length-valid/characters-100000', 100017)]:
            with self.subTest(case_id=case_id):
                status, body = self.request('POST', '/api/run-case', {'case_id': case_id})
                self.assertEqual(status, 200)
                self.assertTrue(body['actual_accept'])
                self.assertTrue(body['matched_expectation'])
                self.assertEqual(body['characters'], characters)
                self.assertTrue('omitted' in body['tree'] or 'truncated' in body['tree'])

    def test_invalid_group_is_actually_rejected(self):
        status, body = self.request('POST', '/api/run-group', {'group': 'regression-invalid'})
        self.assertEqual(status, 200)
        self.assertEqual(body['matched'], 24)
        self.assertEqual(body['total'], 24)
        self.assertTrue(all(not row['actual_accept'] and not row['crash'] and row['error'] for row in body['results']))

    def test_unknown_case_cannot_supply_arbitrary_fixture(self):
        status, body = self.request('POST', '/api/run-case', {'case_id': '../outside.bib', 'source': '@misc{k,}'})
        self.assertEqual(status, 404)
        self.assertIn('Unknown case', body['error'])
