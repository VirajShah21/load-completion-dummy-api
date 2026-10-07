"""Exercise the real HTTP handler over a local socket."""
import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from api.index import handler, RECORDS


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, body=None):
        connection = HTTPConnection(*self.server.server_address, timeout=5)
        try:
            connection.request(method, path, body, {"Content-Type": "application/json"})
            response = connection.getresponse()
            self.assertEqual(response.getheader("Cache-Control"), "no-store")
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_health(self):
        self.assertEqual(self.request("GET", "/health"), (200, {"status": "healthy"}))

    def test_extract(self):
        self.assertEqual(self.request("GET", "/extract?test=1"), (200, RECORDS))

    def test_success(self):
        self.assertEqual(self.request("POST", "/load", json.dumps(RECORDS)),
                         (200, {"accepted": True, "message": "Sample received"}))

    def test_failure(self):
        self.assertEqual(self.request("POST", "/load/fail", json.dumps(RECORDS)),
                         (500, {"accepted": False, "message": "Intentional test failure"}))

    def test_bad_json(self):
        for body in ("not-json", "", b"\xff"):
            self.assertEqual(self.request("POST", "/load", body)[0], 400)

    def test_payload_limit(self):
        connection = HTTPConnection(*self.server.server_address, timeout=5)
        try:
            connection.putrequest("POST", "/load")
            connection.putheader("Content-Length", str(1024 * 1024 + 1))
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 413)
            self.assertEqual(json.loads(response.read())["error"], "Sample payload limit is 1 MiB")
        finally:
            connection.close()

    def test_unknown_route(self):
        self.assertEqual(self.request("GET", "/missing")[0], 404)
        self.assertEqual(self.request("POST", "/missing", "{}")[0], 404)

    def test_history_is_explicitly_unavailable(self):
        self.assertEqual(self.request("GET", "/requests")[0], 501)

    def test_root(self):
        self.assertEqual(self.request("GET", "/")[1]["failureSink"], "POST /load/fail")
