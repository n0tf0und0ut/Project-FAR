"""Set-valued ambiguous routing pilot tests; model/network is mocked in unit tests."""
import base64
import copy
import hashlib
import http.client
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
import urllib.error
from pathlib import Path
from unittest.mock import patch

from tools import far_uncertain_routing_pilot as study


class FakeResponse:
    status = 200
    def __init__(self, choice="ASK_SCOPE"):
        self.raw = json.dumps({
            "model": "/tmp/pinned-model.gguf",
            "choices": [{"message": {"content": choice}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 44},
        }).encode()
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self, n): return self.raw[:n]


def native_http_response(body, headers, failure_on_eof=None):
    """The real stdlib decoder over a deterministic socket byte stream."""
    wire = b"HTTP/1.1 200 OK\r\n" + headers + b"\r\n" + body
    class ControlledStream(io.BytesIO):
        def readline(self, *args):
            if failure_on_eof is not None and self.tell() == len(wire):
                raise failure_on_eof("controlled transport failure")
            return super().readline(*args)
    class MemorySocket:
        def makefile(self, _mode):
            return ControlledStream(wire)
    response = http.client.HTTPResponse(MemorySocket())
    response.begin()
    return response


def native_stalling_response(body=b'retained prefix', headers=b'Content-Length: 100\r\n', error=TimeoutError):
    """Real buffered native reader: read() can lose its buffer on a later fault."""
    wire = b'HTTP/1.1 200 OK\r\n' + headers + b'\r\n' + body
    class PrefixThenFailure(io.RawIOBase):
        def __init__(self):
            self.offset = 0
        def readable(self):
            return True
        def readinto(self, buffer):
            if self.offset == len(wire):
                raise error('controlled stalled native response')
            count = min(len(buffer), len(wire) - self.offset)
            buffer[:count] = wire[self.offset:self.offset + count]
            self.offset += count
            return count
    class MemorySocket:
        def makefile(self, _mode):
            return io.BufferedReader(PrefixThenFailure())
    response = http.client.HTTPResponse(MemorySocket())
    response.begin()
    return response


class NativeFramingTests(unittest.TestCase):
    def test_http_header_trickle_is_bounded_by_whole_request_deadline(self):
        import socket
        import threading
        import time
        from unittest.mock import patch
        import urllib.request

        workers = []
        def connect(connection):
            client, server = socket.socketpair()
            connection.sock = client
            def respond():
                with server:
                    request = server.recv(65536)
                    self.assertIn(b'GET', request)
                    for byte in b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok':
                        try:
                            server.send(bytes([byte]))
                        except OSError:
                            break
                        time.sleep(.025)
            worker = threading.Thread(target=respond, daemon=True)
            worker.start()
            workers.append(worker)
        start = time.monotonic()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with patch.object(http.client.HTTPConnection, 'connect', connect):
            with self.assertRaises(study.ResponseTransportError) as failed:
                study.read_bounded_response(
                    urllib.request.Request('http://127.0.0.1:18085/'),
                    timeout=1, max_bytes=100, opener=opener,
                    deadline_monotonic=start + .1)
        for worker in workers:
            worker.join(timeout=2)
        self.assertLess(time.monotonic() - start, 1.4)
        self.assertFalse(failed.exception.envelope['response_complete'])
        self.assertEqual(failed.exception.envelope['transport_error'], 'TimeoutError')

    def test_real_nonchunked_socket_trickle_uses_remaining_absolute_deadline(self):
        """Second native read1 must not inherit the header's older idle timeout."""
        import socket
        import threading
        import time
        import urllib.request

        workers = []
        def connect(connection):
            client, server = socket.socketpair()
            connection.sock = client
            def respond():
                with server:
                    try:
                        request = server.recv(65536)
                        self.assertIn(b'GET', request)
                        server.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n')
                        time.sleep(.05)
                        server.sendall(b'a')
                        time.sleep(.30)  # Later than the entire request deadline.
                        server.sendall(b'b')
                    except OSError:
                        pass  # The client should close on its absolute deadline.
            worker = threading.Thread(target=respond, daemon=True)
            worker.start()
            workers.append(worker)

        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        start = time.monotonic()
        with patch.object(http.client.HTTPConnection, 'connect', connect):
            with self.assertRaises(study.ResponseTransportError) as failed:
                study.read_bounded_response(
                    urllib.request.Request('http://127.0.0.1:18085/'),
                    timeout=1, max_bytes=100, opener=opener,
                    deadline_monotonic=start + .20)
        elapsed = time.monotonic() - start
        for worker in workers:
            worker.join(timeout=1)
        observed = base64.b64decode(failed.exception.envelope['raw_response_base64'])
        self.assertEqual(observed, b'a')
        self.assertEqual(failed.exception.envelope['response_sha256'],
                         hashlib.sha256(observed).hexdigest())
        self.assertEqual(failed.exception.envelope['transport_error'], 'TimeoutError')
        self.assertFalse(failed.exception.envelope['response_complete'])
        self.assertLess(elapsed, .30)

    def test_real_chunk_separator_trickle_uses_remaining_absolute_deadline(self):
        """The CR and LF between native chunks must be separately bounded."""
        import socket
        import threading
        import time
        import urllib.request

        workers = []
        def connect(connection):
            client, server = socket.socketpair()
            connection.sock = client
            def respond():
                with server:
                    try:
                        request = server.recv(65536)
                        self.assertIn(b'GET', request)
                        server.sendall(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n'
                                       b'1\r\na')
                        time.sleep(.05)
                        server.sendall(b'\r')
                        time.sleep(.30)  # LF arrives after the whole-request deadline.
                        server.sendall(b'\n0\r\n\r\n')
                    except OSError:
                        pass

            worker = threading.Thread(target=respond, daemon=True)
            worker.start()
            workers.append(worker)

        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        start = time.monotonic()
        with patch.object(http.client.HTTPConnection, 'connect', connect):
            with self.assertRaises(study.ResponseTransportError) as failed:
                study.read_bounded_response(
                    urllib.request.Request('http://127.0.0.1:18085/'),
                    timeout=1, max_bytes=100, opener=opener,
                    deadline_monotonic=start + .20)
        elapsed = time.monotonic() - start
        for worker in workers:
            worker.join(timeout=1)
        observed = base64.b64decode(failed.exception.envelope['raw_response_base64'])
        self.assertEqual(observed, b'a')
        self.assertEqual(failed.exception.envelope['response_sha256'],
                         hashlib.sha256(b'a').hexdigest())
        self.assertEqual(failed.exception.envelope['transport_error'], 'TimeoutError')
        self.assertFalse(failed.exception.envelope['response_complete'])
        self.assertLess(elapsed, .30)

    def test_header_trickle_reader_enforces_absolute_deadline_without_network(self):
        import time
        from tools.far_uncertain_routing_pilot import _DeadlineHeaderReader
        class SlowHeader:
            def readline(self, *_):
                time.sleep(.025)
                return b'H'
        start = time.monotonic()
        with self.assertRaises(TimeoutError):
            _DeadlineHeaderReader(SlowHeader(), start + .09).readline()
        self.assertLess(time.monotonic() - start, .3)

    def test_deadline_failure_retains_the_last_observed_body_chunk(self):
        import time
        from unittest.mock import Mock
        class SlowBody(io.BytesIO):
            status = 200
            headers = {}
            url = 'https://example.org/slow'
            def __init__(self):
                super().__init__(b'ab')
                self.calls = 0
            def read(self, size=-1):
                self.calls += 1
                time.sleep(.025 if self.calls == 1 else .11)
                return super().read(min(size, 1))
        transport = Mock()
        transport.open.return_value = SlowBody()
        request = __import__('urllib.request', fromlist=['Request']).Request(
            'https://example.org/slow')
        with self.assertRaises(study.ResponseTransportError) as caught:
            study.read_bounded_response(request, opener=transport,
                timeout=1, max_bytes=20, chunk_size=1,
                deadline_monotonic=time.monotonic() + .07)
        record = caught.exception.envelope
        self.assertEqual(base64.b64decode(record['raw_response_base64']), b'ab')
        self.assertFalse(record['response_complete'])
        self.assertEqual(record['response_hash_scope'], 'retained_prefix')

    def read(self, body, headers, limit=10000):
        response = native_http_response(body, headers)
        with patch("urllib.request.OpenerDirector.open", return_value=response):
            return study.read_bounded_response(
                study.urllib.request.Request(study.ENDPOINT), timeout=1, max_bytes=limit)

    def test_native_positive_control_short_content_length_is_silent(self):
        body = FakeResponse().raw
        response = native_http_response(body, f"Content-Length: {len(body)+100}\r\n".encode())
        self.assertEqual(response.read(10000), body)  # no IncompleteRead
        self.assertEqual(response.length, 100)
        response.close()

    def test_native_nonchunked_timeout_and_reset_preserve_observed_prefix(self):
        prefix = b'retained prefix'
        for headers in (b'Content-Length: 100\r\n', b'Connection: close\r\n'):
            for error in (TimeoutError, ConnectionResetError):
                control = native_stalling_response(prefix, headers, error)
                with self.assertRaises(error):
                    control.read(65536)  # Consumes the prefix, then raises without returning it.
                control.close()
                for chunk_size in (None, 65536):
                    with self.subTest(headers=headers, error=error, chunk_size=chunk_size):
                        response = native_stalling_response(prefix, headers, error)
                        with patch('urllib.request.OpenerDirector.open', return_value=response):
                            with self.assertRaises(study.ResponseTransportError) as failed:
                                study.read_bounded_response(
                                    study.urllib.request.Request(study.ENDPOINT), timeout=1,
                                    max_bytes=10000, chunk_size=chunk_size)
                        envelope = failed.exception.envelope
                        self.assertEqual(base64.b64decode(envelope['raw_response_base64']), prefix)
                        self.assertEqual(envelope['response_sha256'], hashlib.sha256(prefix).hexdigest())
                        self.assertEqual(envelope['response_bytes_retained'], len(prefix))
                        self.assertEqual(envelope['transport_error'], error.__name__)
                        self.assertFalse(envelope['response_complete'])
                        self.assertEqual(envelope['response_hash_scope'], 'retained_prefix')

    def test_interrupted_partial_chunk_body_preserves_bounded_prefix(self):
        for error in (TimeoutError, ConnectionResetError):
            for limit, expected, truncated in ((10, b'abc', False), (2, b'ab', True)):
                with self.subTest(error=error, limit=limit):
                    response = native_stalling_response(
                        b'10\r\nabc', b'Transfer-Encoding: chunked\r\n', error)
                    with patch('urllib.request.OpenerDirector.open', return_value=response):
                        with self.assertRaises(study.ResponseTransportError) as failed:
                            study.read_bounded_response(
                                study.urllib.request.Request(study.ENDPOINT), timeout=1, max_bytes=limit)
                    envelope = failed.exception.envelope
                    self.assertEqual(base64.b64decode(envelope['raw_response_base64']), expected)
                    self.assertEqual(envelope['response_sha256'], hashlib.sha256(expected).hexdigest())
                    self.assertEqual(envelope['response_bytes_retained'], len(expected))
                    self.assertEqual(envelope['response_truncated'], truncated)
                    self.assertFalse(envelope['response_complete'])
                    self.assertEqual(envelope['response_hash_scope'], 'retained_prefix')
                    if not truncated:
                        self.assertEqual(envelope['transport_error'], error.__name__)

    def test_native_chunk_transport_exceptions_retain_observed_bounded_prefix(self):
        # HTTPResponse has decoded abc, then its next chunk-size read fails.
        # Its local aggregation never returns, but the observer has the bytes.
        for error in (TimeoutError, ConnectionResetError, http.client.RemoteDisconnected):
            for limit, expected, truncated in ((10, b"abc", False), (2, b"ab", True)):
                with self.subTest(error=error, limit=limit):
                    response = native_http_response(
                        b"3\r\nabc\r\n", b"Transfer-Encoding: chunked\r\n", error)
                    with patch("urllib.request.OpenerDirector.open", return_value=response):
                        with self.assertRaises(study.ResponseTransportError) as failed:
                            study.read_bounded_response(
                                study.urllib.request.Request(study.ENDPOINT),
                                timeout=1, max_bytes=limit)
                    envelope = failed.exception.envelope
                    if limit == 10:
                        self.assertEqual(envelope["transport_error"], error.__name__)
                    self.assertEqual(base64.b64decode(envelope["raw_response_base64"]), expected)
                    self.assertEqual(envelope["response_sha256"], hashlib.sha256(expected).hexdigest())
                    self.assertEqual(envelope["response_bytes_retained"], len(expected))
                    self.assertEqual(envelope["response_truncated"], truncated)
                    self.assertFalse(envelope["response_complete"])
                    self.assertEqual(envelope["response_hash_scope"], "retained_prefix")

    def test_short_native_content_length_cannot_be_accepted_as_model_action(self):
        body = FakeResponse().raw
        response = native_http_response(body, f"Content-Length: {len(body)+100}\r\n".encode())
        with patch("urllib.request.OpenerDirector.open", return_value=response):
            with self.assertRaises(study.ModelResponseError) as failed:
                study.request_model("x")
        envelope = failed.exception.envelope
        self.assertFalse(envelope["response_complete"])
        self.assertEqual(envelope["response_hash_scope"], "retained_prefix")
        self.assertEqual(envelope["framing_error"], "ContentLengthMismatch")
        self.assertEqual(base64.b64decode(envelope["raw_response_base64"]), body)

    def test_complete_native_content_length_and_chunked_controls(self):
        for body, headers in (
                (b"abc", b"Content-Length: 3\r\n"),
                (b"3\r\nabc\r\n0\r\nX-Trace: valid\r\n\r\n", b"Transfer-Encoding: chunked\r\n")):
            with self.subTest(headers=headers):
                raw, envelope = self.read(body, headers)
                self.assertEqual(raw, b"abc")
                self.assertTrue(envelope["response_complete"])
                self.assertEqual(envelope["response_hash_scope"], "complete_body")

    def test_native_positive_control_missing_chunk_trailer_is_silent(self):
        response = native_http_response(b"3\r\nabc\r\n0\r\n", b"Transfer-Encoding: chunked\r\n")
        self.assertEqual(response.read(10000), b"abc")
        response.close()

    def test_invalid_chunk_framing_retains_decoded_prefix_and_fails_closed(self):
        for wire in (b"5\r\nabc", b"3\r\nabc\r\n0\r\n", b"3\r\nabcXX0\r\n\r\n"):
            with self.subTest(wire=wire):
                with self.assertRaises(study.ResponseTransportError) as failed:
                    self.read(wire, b"Transfer-Encoding: chunked\r\n")
                envelope = failed.exception.envelope
                self.assertFalse(envelope["response_complete"])
                self.assertEqual(base64.b64decode(envelope["raw_response_base64"]), b"abc")
                self.assertEqual(envelope["framing_error"], "IncompleteChunkFraming")
                self.assertEqual(envelope["response_hash_scope"], "retained_prefix")

    def test_trickled_chunk_size_and_trailer_deadline_is_checked_per_byte(self):
        # The prior one-shot readline() accepted a complete line after the
        # absolute deadline. Simulate per-byte network progress with a clock.
        for phase in ('size', 'trailers'):
            with self.subTest(phase=phase):
                clock = [0.0]
                class Trickle:
                    def __init__(self):
                        self.body = io.BytesIO(b'3;slow=' + b'x' * 20 + b'\r\n'
                            if phase == 'size' else b'X-Slow: ' + b'x' * 20 + b'\r\n')
                    def readline(self, limit=-1):
                        data = self.body.readline(limit)
                        clock[0] += .025 * len(data)
                        return data
                observer = study._ChunkFramingObserver(
                    Trickle(), limit=1024, deadline_monotonic=.1)
                observer.phase = phase
                with patch.object(study.time, 'monotonic', side_effect=lambda: clock[0]):
                    with self.assertRaisesRegex(TimeoutError, 'absolute response deadline'):
                        observer.readline()
                self.assertLessEqual(clock[0], .125)
                self.assertEqual(bytes(observer.prefix), b'')

    def test_ambiguous_duplicate_invalid_lengths_and_transfer_codings_rejected(self):
        for headers in (b"Content-Length: 3\r\nContent-Length: 3\r\n",
                        b"Content-Length: x\r\n", b"Content-Length: -3\r\n",
                        b"Content-Length: " + b"9" * 5000 + b"\r\n",
                        b"Transfer-Encoding: gzip\r\n",
                        b"Content-Length: 3\r\nTransfer-Encoding: chunked\r\n"):
            with self.subTest(headers=headers[:80]):
                wire = b"3\r\nabc\r\n0\r\n\r\n" if b"chunked" in headers else b"abc"
                with self.assertRaises(study.ResponseTransportError) as failed:
                    self.read(wire, headers)
                self.assertFalse(failed.exception.envelope["response_complete"])


class UncertainRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p, cls.digest = study.load()

    def test_transport_completion_timestamp_is_recorded_after_read(self):
        start=datetime(2026,11,3,1,0,0,tzinfo=timezone.utc)
        end=datetime(2026,11,3,1,0,9,tzinfo=timezone.utc)
        response=FakeResponse()
        with patch.object(study,"datetime") as clock, patch("urllib.request.build_opener") as opener:
            clock.now.side_effect=[start,end]
            opener.return_value.open.return_value=response
            raw,envelope=study.read_bounded_response(study.urllib.request.Request("http://127.0.0.1/model"),timeout=10,max_bytes=10000)
        self.assertEqual(raw,response.raw)
        self.assertEqual(envelope["requested_at"],"2026-11-03T01:00:00Z")
        self.assertEqual(envelope["received_at"],"2026-11-03T01:00:09Z")

    def test_transport_timeout_retains_distinct_completion_timestamp(self):
        start=datetime(2026,11,3,1,0,0,tzinfo=timezone.utc)
        end=datetime(2026,11,3,1,1,0,tzinfo=timezone.utc)
        with patch.object(study,"datetime") as clock, patch("urllib.request.build_opener") as opener:
            clock.now.side_effect=[start,end]
            opener.return_value.open.side_effect=TimeoutError("test")
            with self.assertRaises(study.ResponseTransportError) as raised:
                study.read_bounded_response(study.urllib.request.Request("http://127.0.0.1/model"),timeout=60,max_bytes=10000)
        self.assertEqual(raised.exception.envelope["requested_at"],"2026-11-03T01:00:00Z")
        self.assertEqual(raised.exception.envelope["received_at"],"2026-11-03T01:01:00Z")
        self.assertEqual(raised.exception.envelope["transport_error"],"TimeoutError")

    def test_frozen_cases_have_nontrivial_admissible_action_sets(self):
        self.assertEqual(self.p["case_count"], 12)
        self.assertEqual(len(self.p["tasks"]), 12)
        self.assertTrue(all(len(t["admissible"]) >= 2 for t in self.p["tasks"]))
        self.assertTrue(all("VERIFY_EXPLICIT" not in t["admissible"] for t in self.p["tasks"]))
        self.assertEqual(len(set(t["prompt"] for t in self.p["tasks"])), 12)
        self.assertEqual(len(self.digest), 64)
        self.assertEqual(self.p["status"], "RESEARCH_FROZEN_TASK_AUTHOR")

    def test_model_request_separates_public_task_from_gold_action_set(self):
        with patch("urllib.request.OpenerDirector.open", return_value=FakeResponse()) as mock:
            x = study.request_model("No contract supplied")
        self.assertEqual(mock.call_count, 1)
        self.assertEqual(x["action"], "ASK_SCOPE")
        request = x["request"]
        self.assertEqual(request["messages"][1]["content"], "Case text (untrusted task data):\nNo contract supplied")
        self.assertNotIn('"admissible"', json.dumps(request))
        self.assertEqual(hashlib.sha256(base64.b64decode(x["raw_response_base64"])).hexdigest(),
                         x["response_sha256"])
        body = json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(body).hexdigest(), x["request_sha256"])

    def test_network_restricted_and_uninterpretable_completion_not_inferred(self):
        with patch("urllib.request.OpenerDirector.open") as mock:
            with self.assertRaises(study.StudyError):
                study.request_model("x", endpoint="https://api.example")
            mock.assert_not_called()
        with patch("urllib.request.OpenerDirector.open", return_value=FakeResponse("Maybe ask?")):
            x = study.request_model("under-specified")
        self.assertEqual(x["action"], "INVALID_ACTION")

    def test_complete_mock_run_reports_set_valued_admissibility(self):
        def simulated(prompt):
            return {"action": "DISCOVER_CONTRACT", "reported_model": "pinned",
                    "total_tokens": 20, "raw_response_base64": "e30=",
                    "request": {}, "request_sha256": "a" * 64,
                    "response_sha256": "b" * 64}
        with patch.object(study, "sha256_file", return_value=study.MODEL_SHA256):
            result = study.evaluate(self.p, self.digest, Path("/fake/model.gguf"),
                                    runner=simulated)
        self.assertEqual(result["status"], "EXECUTED_INTERNAL_RESEARCH")
        self.assertEqual(len(result["records"]), 12)
        self.assertEqual(result["summary"]["agent_admissible"],
                         result["summary"]["fixed_discover_contract_admissible"])
        self.assertEqual(result["summary"]["model_tokens"], 240)
        self.assertEqual(result["summary"]["unsafe_verification"], 0)
        self.assertEqual(result["claim"], "SCOPED_TASK_AUTHOR_SET_VALUED_OBSERVATION_ONLY")

    def test_all_constant_routing_baselines_expose_nonadaptive_model(self):
        def ask_every_time(prompt):
            return {"action": "ASK_SCOPE", "reported_model": "pinned",
                    "total_tokens": 12}
        with patch.object(study, "sha256_file", return_value=study.MODEL_SHA256):
            output = study.evaluate(self.p, self.digest, Path("/fake"), runner=ask_every_time)
        summary = output["summary"]
        self.assertEqual(summary["agent_admissible"], 11)
        self.assertEqual(summary["fixed_action_scores"]["ASK_SCOPE"], 11)
        self.assertEqual(summary["fixed_action_scores"]["DISCOVER_CONTRACT"], 6)
        self.assertEqual(summary["model_action_counts"]["ASK_SCOPE"], 12)
        self.assertEqual(summary["unique_model_actions"], 1)
        self.assertEqual(summary["model_minus_best_constant"], 0)

    def test_action_diversity_reported_without_claiming_unique_correct_action(self):
        case_actions = iter([row["admissible"][0] for row in self.p["tasks"]])
        def admit_each(prompt):
            return {"action": next(case_actions), "reported_model": "pinned",
                    "total_tokens": 12}
        with patch.object(study, "sha256_file", return_value=study.MODEL_SHA256):
            output = study.evaluate(self.p, self.digest, Path("/fake"), runner=admit_each)
        self.assertEqual(output["summary"]["agent_admissible"], 12)
        self.assertGreater(output["summary"]["unique_model_actions"], 1)
        self.assertEqual(output["summary"]["model_minus_best_constant"], 1)
        self.assertIn("task_author", output["claim"].lower())

    def test_unsafe_verification_is_counted_not_promoted(self):
        def bad(prompt):
            return {"action": "VERIFY_EXPLICIT", "reported_model": "pinned",
                    "total_tokens": 20}
        with patch.object(study, "sha256_file", return_value=study.MODEL_SHA256):
            result = study.evaluate(self.p, self.digest, Path("/fake"), runner=bad)
        self.assertEqual(result["summary"]["unsafe_verification"], 12)
        self.assertEqual(result["summary"]["agent_admissible"], 0)

    def test_malformed_http_200_preserves_raw_response_and_request_in_partial(self):
        # Regression for Codex: missing model telemetry must never discard bytes
        # already received from an actual HTTP 200 model call.
        class BadResponse(FakeResponse):
            def __init__(self):
                self.raw = b'{"model":"local","choices":[{"message":{"content":"ASK_SCOPE"}}]}'

        with tempfile.TemporaryDirectory() as directory:
            partial = Path(directory) / "raw-failure.json"
            def store(record):
                study.persist(partial, record)
            with patch.object(study, "sha256_file", return_value=study.MODEL_SHA256):
                with patch("urllib.request.OpenerDirector.open", return_value=BadResponse()):
                    with self.assertRaises(study.ModelResponseError):
                        study.evaluate(
                            self.p, self.digest, Path("/fake"),
                            checkpoint=store,
                        )
            artifact = json.loads(partial.read_text())
            self.assertEqual(artifact["status"], "FAILED_OR_INCOMPLETE")
            self.assertEqual(artifact["completed"], 0)
            failed = artifact["failed_model_call"]
            self.assertEqual(failed["case_id"], self.p["tasks"][0]["id"])
            envelope = failed["raw_envelope"]
            self.assertEqual(
                hashlib.sha256(base64.b64decode(envelope["raw_response_base64"])).hexdigest(),
                envelope["response_sha256"])
            self.assertEqual(
                hashlib.sha256(json.dumps(
                    envelope["request"], sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                envelope["request_sha256"])

    def test_partial_evidence_survives_second_model_timeout(self):
        calls = 0
        def broken(prompt):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise study.StudyError("second call transport failure")
            return {"action": "ASK_SCOPE", "reported_model": "pinned", "total_tokens": 20,
                    "raw_response_base64": "e30=", "request_sha256": "a" * 64,
                    "response_sha256": "b" * 64}
        with tempfile.TemporaryDirectory() as directory:
            partial = Path(directory) / "partial.json"
            with patch.object(study, "sha256_file", return_value=study.MODEL_SHA256):
                with self.assertRaisesRegex(study.StudyError, "transport failure"):
                    study.evaluate(self.p, self.digest, Path("/fake"), runner=broken,
                                   checkpoint=lambda record: study.persist(partial, record))
            data = json.loads(partial.read_text())
            self.assertEqual(data["status"], "INCOMPLETE")
            self.assertEqual(data["completed"], 1)
            self.assertEqual(len(data["records"]), 1)
            self.assertEqual(data["claim"], "NOT_ESTABLISHED")

    def test_native_chunk_timeout_and_reset_survive_model_checkpoint(self):
        for error in (TimeoutError, ConnectionResetError):
            with self.subTest(error=error):
                response = native_http_response(
                    b"3\r\nabc\r\n", b"Transfer-Encoding: chunked\r\n", error)
                records = []
                with patch.object(study, "sha256_file", return_value=study.MODEL_SHA256), \
                        patch("urllib.request.OpenerDirector.open", return_value=response):
                    with self.assertRaises(study.ModelResponseError):
                        study.evaluate(self.p, self.digest, Path("/fake"), checkpoint=records.append)
                self.assertEqual(records[-1]["status"], "FAILED_OR_INCOMPLETE")
                envelope = records[-1]["failed_model_call"]["raw_envelope"]
                self.assertEqual(base64.b64decode(envelope["raw_response_base64"]), b"abc")
                self.assertEqual(envelope["response_sha256"], hashlib.sha256(b"abc").hexdigest())
                self.assertFalse(envelope["response_complete"])
                self.assertEqual(envelope["response_hash_scope"], "retained_prefix")

    def test_invalid_model_or_malformed_protocol_blocks(self):
        with patch.object(study, "sha256_file", return_value="0" * 64):
            with self.assertRaisesRegex(study.StudyError, "SHA-256"):
                study.evaluate(self.p, self.digest, Path("/fake"), runner=lambda _: {})
        mutated = copy.deepcopy(self.p)
        mutated["tasks"][0]["admissible"] = ["VERIFY_EXPLICIT"]
        with tempfile.TemporaryDirectory() as directory:
            location = Path(directory) / "invalid.json"
            location.write_text(json.dumps(mutated), encoding="utf-8")
            with patch.object(study, "FROZEN", location):
                with self.assertRaisesRegex(study.StudyError, "admissibility"):
                    study.load()

    def test_distinct_model_identity_required(self):
        count = 0
        def varied(prompt):
            nonlocal count
            count += 1
            return {"action": "ASK_SCOPE", "reported_model": str(count % 2),
                    "total_tokens": 5}
        with patch.object(study, "sha256_file", return_value=study.MODEL_SHA256):
            with self.assertRaisesRegex(study.StudyError, "identity drift"):
                study.evaluate(self.p, self.digest, Path("/fake"), runner=varied)

    def test_http_error_body_headers_and_request_survive_model_failure(self):
        raw = b'{"error":"provider unavailable"}'
        error = urllib.error.HTTPError(study.ENDPOINT, 503, "Unavailable",
                                       {"Retry-After": "60"}, io.BytesIO(raw))
        records = []
        with patch.object(study, "sha256_file", return_value=study.MODEL_SHA256):
            with patch("urllib.request.OpenerDirector.open", side_effect=error):
                with self.assertRaises(study.ModelResponseError):
                    study.evaluate(self.p, self.digest, Path("/fake"), checkpoint=records.append)
        env = records[-1]["failed_model_call"]["raw_envelope"]
        self.assertEqual(env["http_status"], 503)
        self.assertEqual(env["response_headers"]["Retry-After"], "60")
        self.assertEqual(base64.b64decode(env["raw_response_base64"]), raw)
        self.assertEqual(env["response_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertTrue(env["response_complete"])
        self.assertIn("request_sha256", env)

    def test_oversized_response_preserves_explicitly_truncated_prefix(self):
        response = FakeResponse()
        response.raw = b"abcdef"
        request = study.urllib.request.Request(study.ENDPOINT, b"{}", method="POST")
        with patch("urllib.request.OpenerDirector.open", return_value=response):
            with self.assertRaises(study.ResponseTransportError) as failure:
                study.read_bounded_response(request, timeout=1, max_bytes=4)
        env = failure.exception.envelope
        self.assertEqual(base64.b64decode(env["raw_response_base64"]), b"abcd")
        self.assertEqual(env["response_sha256"], hashlib.sha256(b"abcd").hexdigest())
        self.assertTrue(env["response_truncated"])
        self.assertFalse(env["response_complete"])
        self.assertEqual(env["response_hash_scope"], "retained_prefix")

    def test_model_http_redirect_is_preserved_without_destination_request(self):
        from tests.redirect_transport_fixture import RedirectTransport
        transport = RedirectTransport(b"redirect observation")
        with patch("urllib.request.build_opener", side_effect=transport.build_opener):
            with self.assertRaises(study.ModelResponseError) as failure:
                study.request_model("x")
        env = failure.exception.envelope
        self.assertEqual(env["http_status"], 302)
        self.assertEqual(base64.b64decode(env["raw_response_base64"]), b"redirect observation")
        self.assertEqual(transport.forbidden, [])
        self.assertEqual(len(transport.requests), 1)

    def test_redirect_transport_detects_an_unguarded_native_client(self):
        from tests.redirect_transport_fixture import RedirectTransport
        transport = RedirectTransport(b"redirect observation")
        request = study.urllib.request.Request(study.ENDPOINT, b"{}", method="POST")
        with transport.build_opener().open(request) as response:
            self.assertEqual(response.status, 200)
        self.assertEqual(len(transport.forbidden), 1)
        self.assertEqual(len(transport.requests), 2)


if __name__ == "__main__":
    unittest.main()
