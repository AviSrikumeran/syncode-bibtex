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
