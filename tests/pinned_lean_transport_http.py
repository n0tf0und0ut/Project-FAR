"""Hosted-only actual curl fault fixtures; canonical unit tests need no sockets.

Run explicitly with python -m tests.pinned_lean_transport_http. The managed
local runtime denies socket creation; this probe is executed by its own
read-only GitHub Actions job, without weakening canonical network policy.
"""
from contextlib import contextmanager
from hashlib import sha256
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import socketserver
import subprocess
import tempfile
import threading
import unittest

from tests.test_pinned_lean_transport import URL, WORKFLOWS, download_step

PAYLOAD = b"pinned transport regression fixture\n"


@contextmanager
def http_over_local_ipc(responses):
    # AF_UNIX avoids network access and DNS inside deny-network canonical tests.
    # Production uses the unchanged HTTPS URL; only the fixture transport differs.
    with tempfile.TemporaryDirectory(prefix="far-lean-") as directory:
        hits = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.path)
                reply = responses[min(len(hits) - 1, len(responses) - 1)]
                body = reply if isinstance(reply, bytes) else b""
                self.send_response(200 if isinstance(reply, bytes) else reply)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        path = Path(directory) / "http.sock"
        with socketserver.UnixStreamServer(str(path), Handler) as server:
            thread = threading.Thread(target=server.serve_forever,
                                      kwargs={"poll_interval": 0.05}, daemon=True)
            thread.start()
            try:
                yield directory, path, hits
            finally:
                server.shutdown()
                thread.join(timeout=2)


def run_transport(filename, responses):
    _script, original = download_step(filename)
    with http_over_local_ipc(responses) as (directory, socket_path, hits):
        archive = Path(directory) / "archive"
        argv = [str(archive) if item == "$archive" else
                "http://lean-fixture.invalid/archive" if item == URL else item
                for item in original]
        # Use actual workflow retry/failure arguments and curl's real HTTP logic.
        argv[1:1] = ["--unix-socket", str(socket_path), "--noproxy", "*"]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=10)
        check = None
        if result.returncode == 0:
            # The deployment pin is checked separately below. A tiny fixture
            # digest exercises the same sha256sum CLI, including tamper failure.
            check = subprocess.run(["sha256sum", "-c", "-"],
                                   input=f"{sha256(PAYLOAD).hexdigest()}  {archive}\n",
                                   capture_output=True, text=True, timeout=5)
        return result, check, len(hits)


class PinnedLeanHTTPFaultTests(unittest.TestCase):
    def test_actual_curl_recovers_one_http_504_and_verifies_fixture_digest(self):
        for filename in WORKFLOWS:
            with self.subTest(workflow=filename):
                result, check, hits = run_transport(filename, [504, PAYLOAD])
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(0, check.returncode, check.stderr)
                self.assertEqual(2, hits)

    def test_persistent_http_failure_exhausts_four_attempts_and_fails(self):
        result, check, hits = run_transport("validator-assurance.yml", [504])
        self.assertEqual(22, result.returncode)
        self.assertIsNone(check)
        self.assertEqual(4, hits)

    def test_successful_download_with_wrong_digest_still_fails(self):
        for filename in WORKFLOWS[:2]:
            with self.subTest(workflow=filename):
                result, check, hits = run_transport(filename, [b"tampered"])
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertNotEqual(0, check.returncode)
                self.assertEqual(1, hits)


if __name__ == "__main__":
    unittest.main()
