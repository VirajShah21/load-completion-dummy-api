"""Stateless HTTP source and sink for load completion-handler testing."""

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

RECORDS = [
    {"id": 1, "name": "First sample", "workflow": "Load Completion Event Test"},
    {"id": 2, "name": "Second sample", "workflow": "Load Completion Event Test"},
]
MAX_BODY_BYTES = 1024 * 1024


class handler(BaseHTTPRequestHandler):
    """Serve the original sample routes without storing request payloads."""

    def log_message(self, format, *args):
        """Suppress the default logger, which includes unfiltered query strings."""

    def respond(self, status, value):
        payload = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def record(self, status, path):
        """Log only metadata for known routes; never log bodies or credentials."""
        print(json.dumps({"time": datetime.now(timezone.utc).isoformat(),
                          "method": self.command, "path": path,
                          "status": status}), flush=True)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/health":
            self.respond(200, {"status": "healthy"})
        elif path == "/extract":
            self.record(200, path)
            self.respond(200, RECORDS)
        elif path == "/requests":
            self.respond(501, {"error": "Request history is not stored",
                               "message": "Request metadata is available in Vercel runtime logs; payloads are not logged."})
        elif path in ("/", "/api", "/api/index"):
            self.respond(200, {"workflow": "Load Completion Event Test",
                               "source": "GET /extract", "sink": "POST /load",
                               "failureSink": "POST /load/fail", "health": "GET /health",
                               "evidence": "Vercel runtime logs (metadata only)"})
        else:
            self.respond(404, {"error": "Unknown endpoint"})

    def do_POST(self):
        path = urlsplit(self.path).path
        if path not in ("/load", "/load/fail"):
            self.respond(404, {"error": "Unknown endpoint"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.respond(400, {"error": "Invalid Content-Length"})
            return
        if length < 0:
            self.respond(400, {"error": "Invalid Content-Length"})
            return
        if length > MAX_BODY_BYTES:
            self.respond(413, {"error": "Sample payload limit is 1 MiB"})
            return
        try:
            json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            self.respond(400, {"error": "Expected JSON"})
            return
        status = 500 if path == "/load/fail" else 200
        self.record(status, path)
        self.respond(status, {"accepted": status == 200,
                              "message": "Intentional test failure" if status == 500 else "Sample received"})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 5290), handler).serve_forever()
