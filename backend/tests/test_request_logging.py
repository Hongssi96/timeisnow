import io
import json
import logging
from pathlib import Path
import sys
import unittest

from fastapi import Request
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app
from app.request_logging import logger, RequestJsonFormatter, RequestEventFilter, configure_request_logger
from test_api_contract import request


class RequestLogTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.routes = list(app.router.routes)
        async def item(item_id: str, request: Request):
            await request.body()
            return JSONResponse({'private_response': 'secret-response'})
        async def broken():
            raise RuntimeError('secret-exception-message')
        async def validation(count: int):
            return {'count': count}
        app.add_api_route('/_log/item/{item_id}', item, methods=['POST'])
        app.add_api_route('/_log/broken', broken)
        app.add_api_route('/_log/validation', validation)

    @classmethod
    def tearDownClass(cls):
        app.router.routes[:] = cls.routes

    def setUp(self):
        self.handlers, self.level = list(logger.handlers), logger.level
        self.stream = io.StringIO()
        handler = logging.StreamHandler(self.stream)
        handler.setFormatter(RequestJsonFormatter())
        handler.addFilter(RequestEventFilter())
        logger.handlers[:] = [handler]
        logger.setLevel(logging.INFO)

    def tearDown(self):
        logger.handlers[:] = self.handlers
        logger.setLevel(self.level)

    def entries(self):
        return [json.loads(line) for line in self.stream.getvalue().splitlines()]

    async def test_success_logged_once_with_matching_id(self):
        status, headers, body = await request('/api/v1/health')
        entries = self.entries()
        self.assertEqual(len(entries), 1)
        event = entries[0]
        self.assertEqual(event['event'], 'http.request.completed')
        self.assertEqual(event['request_id'], body['meta']['request_id'])
        self.assertEqual(event['request_id'], headers[b'x-request-id'].decode())
        self.assertEqual(event['status_code'], status)
        self.assertEqual(event['route'], '/api/v1/health')
        self.assertTrue(event['timestamp'].endswith('Z'))
        self.assertGreaterEqual(event['duration_ms'], 0)

    async def test_route_template_excludes_paths_queries_headers_and_bodies(self):
        await request('/_log/item/secret-path', 'POST', query=b'serviceKey=secret-query',
                      headers=[(b'authorization', b'Bearer secret-auth'), (b'cookie', b'secret-cookie'),
                               (b'x-request-id', b'secret-client-id')], body=b'secret-body')
        self.assertEqual(self.entries()[0]['route'], '/_log/item/{item_id}')
        self.assertNotIn('secret-', self.stream.getvalue())
        self.assertEqual(len(self.entries()), 1)

    async def test_unmatched_path_does_not_leak_actual_path(self):
        await request('/api/v1/secret-path', query=b'address=secret-query')
        entry = self.entries()[0]
        self.assertEqual(entry['route'], 'unmatched')
        self.assertEqual(entry['status_code'], 404)
        self.assertEqual(entry['error_code'], 'RESOURCE_NOT_FOUND')
        self.assertNotIn('secret-', self.stream.getvalue())

    async def test_validation_error_is_not_unexpected_server_failure(self):
        await request('/_log/validation', query=b'count=secret-input')
        entries = self.entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['level'], 'INFO')
        self.assertEqual(entries[0]['error_code'], 'VALIDATION_ERROR')
        self.assertNotIn('secret-input', self.stream.getvalue())

    async def test_exception_logs_safe_error_and_one_completion(self):
        _, headers, body = await request('/_log/broken')
        entries = self.entries()
        self.assertEqual([e['event'] for e in entries], ['http.request.failed', 'http.request.completed'])
        self.assertEqual(entries[0]['level'], 'ERROR')
        self.assertEqual(entries[0]['exception_type'], 'RuntimeError')
        self.assertEqual(entries[0]['error_code'], 'INTERNAL_ERROR')
        self.assertTrue(all(e['request_id'] == body['meta']['request_id'] for e in entries))
        self.assertEqual(entries[0]['request_id'], headers[b'x-request-id'].decode())
        self.assertNotIn('secret-exception-message', self.stream.getvalue())

    def test_formatter_and_filter_ignore_raw_message_trace_and_extras(self):
        logger.error('secret-raw-message')
        try:
            raise ValueError('secret-exception-message')
        except ValueError:
            logger.error('secret-message', exc_info=True, extra={
                'event': 'http.request.failed', 'request_id': 'req_test', 'method': 'GET',
                'route': '/safe/{id}', 'status_code': 500, 'duration_ms': 1,
                'payload': 'secret-payload', 'address': 'secret-address'})
        self.assertEqual(len(self.entries()), 1)
        self.assertNotIn('secret-', self.stream.getvalue())
        self.assertNotIn('payload', self.entries()[0])

    def test_configuration_does_not_duplicate_handlers_or_enable_debug(self):
        configure_request_logger('INFO')
        configure_request_logger('INFO')
        self.assertEqual(len(logger.handlers), 1)
        configure_request_logger('DEBUG')
        self.assertEqual(logger.level, logging.INFO)
        self.assertFalse(logger.propagate)
