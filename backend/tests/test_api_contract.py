"""Exercise actual ASGI responses without DB, network, or extra dependencies."""
import asyncio
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app


async def request(path, method="GET", query=b"", headers=None, body=b""):
    messages = []
    supplied = False
    async def receive():
        nonlocal supplied
        if not supplied:
            supplied = True
            return {"type": "http.request", "body": body, "more_body": False}
        await asyncio.Event().wait()
    async def send(message):
        messages.append(message)
    scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
             "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
             "query_string": query, "root_path": "", "headers": headers or [],
             "client": ("127.0.0.1", 12345), "server": ("test", 80), "http_version": "1.1"}
    await asyncio.wait_for(app(scope, receive, send), timeout=3)
    start = next(item for item in messages if item["type"] == "http.response.start")
    raw = b"".join(item.get("body", b"") for item in messages if item["type"] == "http.response.body")
    return start["status"], dict(start["headers"]), json.loads(raw)


class ApiContractTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_routes = list(app.router.routes)
        async def broken():
            raise ValueError("private-secret-location")
        async def validate(count: int):
            return {"count": count}
        app.add_api_route("/_test/broken", broken)
        app.add_api_route("/_test/validate", validate)

    @classmethod
    def tearDownClass(cls):
        app.router.routes[:] = cls.original_routes

    def identity(self, headers, body):
        self.assertEqual(headers[b"x-request-id"].decode(), body["meta"]["request_id"])
        self.assertRegex(body["meta"]["request_id"], r"^req_[0-9a-f]{32}$")
        self.assertTrue(body["meta"]["server_time"].endswith("Z"))

    async def test_health_and_forged_request_id(self):
        status, headers, body = await request("/api/v1/health", headers=[(b"x-request-id", b"caller-id")])
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["status"], "ok")
        self.identity(headers, body)
        self.assertNotEqual(body["meta"]["request_id"], "caller-id")

    async def test_each_request_gets_distinct_id(self):
        first = await request("/api/v1/health")
        second = await request("/api/v1/health")
        self.assertNotEqual(first[2]["meta"]["request_id"], second[2]["meta"]["request_id"])

    async def test_unknown_path_is_safe_common_error(self):
        status, headers, body = await request("/api/v1/private-secret-location")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"]["code"], "RESOURCE_NOT_FOUND")
        self.assertNotIn("private-secret", json.dumps(body))
        self.identity(headers, body)

    async def test_method_error_preserves_allow(self):
        status, headers, body = await request("/api/v1/health", "POST")
        self.assertEqual(status, 405)
        self.assertIn(b"GET", headers[b"allow"])
        self.assertEqual(body["error"]["code"], "METHOD_NOT_ALLOWED")
        self.identity(headers, body)

    async def test_validation_excludes_submitted_input(self):
        status, headers, body = await request("/_test/validate", query=b"count=private-secret-location")
        self.assertEqual(status, 422)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertNotIn("private-secret", json.dumps(body))
        self.assertEqual(body["error"]["details"][0]["field"], "query.count")
        self.identity(headers, body)

    async def test_exception_hides_raw_error(self):
        status, headers, body = await request("/_test/broken")
        self.assertEqual(status, 500)
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn("private-secret", json.dumps(body))
        self.identity(headers, body)
