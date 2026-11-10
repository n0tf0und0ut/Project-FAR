"""Research-only agent next-action test for *under-specified*, not explicit, FAR tasks.

Scoring uses set-valued task-author admissibility; no unique 'correct' tool
or independent oracle is claimed. Nothing here changes the canonical FAR gate.
"""
from __future__ import annotations

import argparse
import copy
import base64
import hashlib
import http.client
import ipaddress
import socket
import threading
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "research/uncertain-routing/frozen-v0.1.json"
MODEL_SHA256 = "6eb923e7d26e9cea28811e1a8e852009b21242fb157b26149d3b188f3a8c8653"
MODEL = "Qwen2.5-0.5B-Instruct-Q4_K_M"
ENDPOINT = "http://127.0.0.1:8085/v1/chat/completions"
ACTIONS = ("ASK_SCOPE", "GATHER_EVIDENCE", "DISCOVER_CONTRACT", "PRESERVE_UNKNOWN", "VERIFY_EXPLICIT")
SYSTEM = (
    "You are deciding a next investigation step, not truth or a final verdict. "
    "No task supplies a validated machine-readable FAR comparison contract. "
    "Select exactly one next action: ASK_SCOPE, GATHER_EVIDENCE, "
    "DISCOVER_CONTRACT, PRESERVE_UNKNOWN, VERIFY_EXPLICIT. "
    "Never run verification without a validated downstream contract. "
    "Respond with exactly one uppercase action token and no other text."
)


class StudyError(ValueError):
    pass


class ModelResponseError(StudyError):
    """Response was received but could not be interpreted; retain exact byte evidence."""

    def __init__(self, reason: str, envelope: dict):
        super().__init__(reason)
        self.envelope = envelope


class ResponseTransportError(StudyError):
    """A failed HTTP attempt, including any bounded response bytes observed."""

    def __init__(self, reason: str, envelope: dict):
        super().__init__(reason)
        self.envelope = envelope


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        # Returning None makes urllib raise HTTPError for the original response;
        # its body and Location header can then be preserved without following it.
        return None


class _DeadlineHeaderReader:
    """Bound individual status/header reads to a monotonic request deadline.

    urllib's idle socket timeout is not a whole-header deadline when a peer
    trickles bytes. This wrapper checks every returned header byte without
    altering the native HTTP parser or the transport's destination policy.
    """
    def __init__(self, stream, deadline, timeout=None):
        self.stream, self.deadline, self.timeout = stream, deadline, timeout

    def check(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('absolute HTTP header deadline exceeded')
        sock = getattr(getattr(self.stream, 'raw', self.stream), '_sock', None)
        if sock is not None:
            sock.settimeout(max(.001, min(self.timeout, remaining) if self.timeout is not None else remaining))

    def readline(self, limit=-1):
        data = bytearray()
        while not data.endswith(b'\n') and (limit < 0 or len(data) < limit):
            self.check()
            part = self.stream.readline(1)
            self.check()
            if not part:
                break
            data.extend(part)
        return bytes(data)

    def __getattr__(self, name):
        return getattr(self.stream, name)



# Connection-time DNS is separate from source preflight. Never run an
# unbounded socket.getaddrinfo() on the campaign/caller thread while opening
# native HTTP(S), including when the configured destination is a proxy.
# Resolver threads retain their finite semaphore slots until they actually end.
_CONNECTION_DNS_SLOTS = threading.BoundedSemaphore(8)


def _deadline_native_connection(address, timeout, source_address, deadline):
    """Native socket connect with a bounded DNS lookup and a single deadline.

    This is a request-local HTTPConnection._create_connection adapter. The
    native HTTP/HTTPS handler still controls proxies, CONNECT and TLS/SNI.
    DNS cannot be cancelled mid-call, so timed-out resolver threads retain
    their capacity slots; no socket is opened from such a worker.
    """
    end = deadline
    if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT and timeout is not None:
        end = min(end, time.monotonic() + timeout)
    host, port = address
    if end <= time.monotonic():
        raise TimeoutError('connection deadline exhausted')
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        family = socket.AF_INET6 if literal.version == 6 else socket.AF_INET
        sockaddr = (str(literal), port, 0, 0) if literal.version == 6 else (str(literal), port)
        addresses = [(family, socket.SOCK_STREAM, 0, '', sockaddr)]
    else:
        remaining = end - time.monotonic()
        if remaining <= 0 or not _CONNECTION_DNS_SLOTS.acquire(timeout=remaining):
            raise TimeoutError('connection DNS deadline exhausted')
        result = {}
        finished = threading.Event()

        def lookup():
            try:
                result['addresses'] = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
            except BaseException as exc:
                result['error'] = exc
            finally:
                _CONNECTION_DNS_SLOTS.release()
                finished.set()

        worker = threading.Thread(target=lookup, name='far-connection-dns', daemon=True)
        try:
            worker.start()
        except BaseException:
            _CONNECTION_DNS_SLOTS.release()
            raise
        if not finished.wait(max(0., end - time.monotonic())):
            raise TimeoutError('connection DNS deadline exhausted')
        if end <= time.monotonic():
            raise TimeoutError('connection DNS deadline exhausted')
        if 'error' in result:
            raise result['error']
        addresses = result['addresses']
    last_error = None
    for family, socktype, proto, _canon, sockaddr in addresses:
        remaining = end - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('connection deadline exhausted')
        sock = socket.socket(family, socktype, proto)
        try:
            sock.settimeout(max(.001, remaining))
            if source_address:
                sock.bind(source_address)
            sock.connect(sockaddr)
            return sock
        except OSError as exc:
            last_error = exc
            sock.close()
    if last_error is not None:
        raise last_error
    raise OSError('connection DNS returned no usable address')

def _isolated_deadline_opener(opener, deadline, timeout):
    """Preserve the caller's reusable opener; bind deadline handlers per call.

    OpenerDirector.add_handler() is persistent. Installing a closure directly
    on a caller-owned opener lets the first request's timeout/deadline govern
    all later requests. Clone the handler registrations and install only on
    this request's director; shallow-copy handlers so their parent references
    cannot be rebound away from the original opener.
    """
    if deadline is None or not isinstance(opener, urllib.request.OpenerDirector):
        return opener
    isolated = urllib.request.OpenerDirector()
    for handler in opener.handlers:
        isolated.add_handler(copy.copy(handler))
    _install_deadline_header_handlers(isolated, deadline, timeout)
    return isolated


def _install_deadline_header_handlers(opener, deadline, timeout=None):
    """Attach per-request whole-header bounds without changing proxy/redirect guards."""
    if deadline is None or not isinstance(opener, urllib.request.OpenerDirector):
        return

    class DeadlineResponse(http.client.HTTPResponse):
        def _read_status(self):
            if not isinstance(self.fp, _DeadlineHeaderReader):
                self.fp = _DeadlineHeaderReader(self.fp, deadline, timeout)
            return super()._read_status()

    def bounded_connect(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
        return _deadline_native_connection(address, timeout, source_address, deadline)

    class DeadlineHTTPConnection(http.client.HTTPConnection):
        response_class = DeadlineResponse

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._create_connection = bounded_connect

    class DeadlineHTTPSConnection(http.client.HTTPSConnection):
        response_class = DeadlineResponse

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._create_connection = bounded_connect

    class DeadlineHTTPHandler(urllib.request.HTTPHandler):
        handler_order = 450  # Before urllib's default transport handler (500).
        def http_open(self, request):
            return self.do_open(DeadlineHTTPConnection, request)

    class DeadlineHTTPSHandler(urllib.request.HTTPSHandler):
        handler_order = 450
        def https_open(self, request):
            connection_options = {'context': self._context}
            # Python 3.11 retains HTTPSHandler(check_hostname=...) apart
            # from SSLContext. Later Python removed the override. Pass it
            # through only when the original runtime actually supports it.
            hostname_override = getattr(self, '_check_hostname', None)
            if hostname_override is not None:
                connection_options['check_hostname'] = hostname_override
            return self.do_open(DeadlineHTTPSConnection, request, **connection_options)

    # The deadline handler precedes the original transport. Reuse the TLS
    # context and hostname policy actually configured by the operator instead
    # of silently replacing them with urllib's default trust settings.
    original_https = next((handler for handler in opener.handlers
                           if isinstance(handler, urllib.request.HTTPSHandler)), None)
    https_options = ({'context': original_https._context}
                     if original_https is not None else {})
    if original_https is not None:
        hostname_override = getattr(original_https, '_check_hostname', None)
        if hostname_override is not None:
            https_options['check_hostname'] = hostname_override
    opener.add_handler(DeadlineHTTPHandler())
    opener.add_handler(DeadlineHTTPSHandler(**https_options))


class _ChunkFramingObserver:
    """Observe native HTTPResponse framing without replacing its body decoder.

    The stdlib accepts EOF in the trailer section and discards chunk separator
    bytes without validating CRLF. Preserve bounded decoded prefix while checking
    those framing obligations around the same native buffered stream.
    """
    def __init__(self, stream, limit, deadline_monotonic=None, timeout=None):
        self.stream, self.limit = stream, limit
        self.deadline_monotonic, self.timeout = deadline_monotonic, timeout
        self.phase, self.remaining = "size", 0
        self.prefix, self.framing_bytes = bytearray(), 0

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def _check_deadline(self):
        if self.deadline_monotonic is None:
            return
        remaining = self.deadline_monotonic - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('absolute response deadline exceeded')
        # HTTPResponse normally wraps a BufferedReader over socket.SocketIO.
        # Bound each blocking framing read by the remaining whole-request time.
        sock = getattr(getattr(self.stream, 'raw', self.stream), '_sock', None)
        if sock is not None:
            sock.settimeout(max(.001, min(self.timeout, remaining) if self.timeout is not None else remaining))

    def read(self, amount=-1):
        if self.phase == "body" and amount >= 0:
            # Native _safe_read expects the requested chunk body size, but a
            # buffered read may consume a partial body and then raise. Observe
            # each read1 return before collecting the exact-size decoder input.
            chunks, received = [], 0
            reader = getattr(self.stream, "read1", self.stream.read)
            while received < amount:
                self._check_deadline()
                part = reader(amount - received)
                if not part:
                    self._check_deadline()
                    break
                # This chunk was observed before the deadline check can reject
                # its completion; retain it in the failure receipt.
                self.prefix.extend(part[:max(0, self.limit - len(self.prefix))])
                self.remaining -= len(part)
                chunks.append(part)
                received += len(part)
                self._check_deadline()
            if self.remaining == 0:
                self.phase = "separator"
            return b"".join(chunks)
        if self.phase == "separator":
            # Native HTTPResponse._get_chunk_left() reads the separator with
            # fp.read(2). A buffered read can block for the second byte using
            # the socket timeout that was calculated before the first. Preserve
            # strict CRLF framing, refreshing the remaining absolute deadline
            # before *each* blocking byte of this two-byte protocol delimiter.
            if amount != 2:
                raise http.client.IncompleteRead(bytes(self.prefix))
            reader = getattr(self.stream, "read1", self.stream.read)
            data = bytearray()
            for expected in (b"\r", b"\n"):
                self._check_deadline()
                part = reader(1)
                if part:
                    data.extend(part)
                    self.framing_bytes += len(part)
                self._check_deadline()
                if part != expected or self.framing_bytes > self.limit + 65536:
                    raise http.client.IncompleteRead(bytes(self.prefix))
            self.phase = "size"
            return bytes(data)
        self._check_deadline()
        data = self.stream.read(amount)
        self._check_deadline()
        return data

    def readline(self, limit=-1):
        # stdlib readline() is allowed to block while a peer trickles a single
        # chunk-size/extension or trailer line. A one-time deadline check
        # would allow arbitrary overrun. Read bounded framing bytes one at a
        # time, checking both before and after each blocking operation.
        data = bytearray()
        while not data.endswith(b"\n"):
            self._check_deadline()
            part = self.stream.readline(1)
            if not part:
                self._check_deadline()
                break
            data.extend(part)
            self._check_deadline()
            self.framing_bytes += len(part)
            if ((limit >= 0 and len(data) > limit)
                    or self.framing_bytes > self.limit + 65536):
                raise http.client.IncompleteRead(bytes(self.prefix))
        data = bytes(data)
        if (not data.endswith(b"\r\n")
                or self.phase not in ("size", "trailers")):
            raise http.client.IncompleteRead(bytes(self.prefix))
        if self.phase == "size":
            size = data[:-2].split(b";", 1)[0]
            if not size or any(c not in b"0123456789abcdefABCDEF" for c in size):
                raise http.client.IncompleteRead(bytes(self.prefix))
            self.remaining = int(size, 16)
            self.phase = "body" if self.remaining else "trailers"
        elif data == b"\r\n":
            self.phase = "complete"
        return data


def read_bounded_response(request: urllib.request.Request, *, timeout: float,
                          max_bytes: int, opener=None, checkpoint=None,
                          chunk_size: int | None = None,
                          deadline_monotonic: float | None = None) -> tuple[bytes, dict]:
    """Refuse redirects and retain bounded failures before rejecting the response.

    response_sha256 always hashes precisely the retained bytes. On truncation it
    is explicitly a prefix hash, never represented as the hash of the whole body.
    The optional operator opener preserves its destination/proxy policy. Bounded
    chunked reads and checkpoints let source tools journal progressive receipts
    without implementing a second HTTP framing parser.
    """
    envelope = {
        "request_url": request.full_url, "request_method": request.get_method(),
        "http_status": None, "response_headers": {},
        "raw_response_base64": "", "response_sha256": digest(b""),
        "response_bytes_retained": 0, "response_truncated": False,
        "response_complete": False, "response_hash_scope": "retained_prefix",
        "requested_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "received_at": None,
        "timing_scope": "request_start_to_body_read_or_transport_failure",
    }
    response, observer, raw = None, None, b""

    def enforce_deadline():
        if deadline_monotonic is not None and time.monotonic() >= deadline_monotonic:
            raise TimeoutError('absolute response deadline exceeded')

    def retain(data, complete=False):
        retained = data[:max_bytes]
        envelope.update(raw_response_base64=base64.b64encode(retained).decode("ascii"),
                        response_sha256=digest(retained), response_bytes_retained=len(retained),
                        response_truncated=len(data) > max_bytes, response_complete=complete,
                        response_hash_scope="complete_body" if complete else "retained_prefix")
        if checkpoint is not None:
            checkpoint(json.loads(json.dumps(envelope)))

    try:
        try:
            supplied = opener if opener is not None else urllib.request.build_opener(NoRedirect())
            client = _isolated_deadline_opener(supplied, deadline_monotonic, timeout)
            enforce_deadline()
            remaining = (deadline_monotonic - time.monotonic()) if deadline_monotonic is not None else timeout
            response = client.open(request, timeout=max(.001, min(timeout, remaining)))
            enforce_deadline()
        except urllib.error.HTTPError as exc:
            # HTTPError is also a readable response, including for refused redirects.
            response = exc
        with response:
            envelope["http_status"] = response.status
            envelope["response_url"] = getattr(response, "url", request.full_url)
            headers = getattr(response, "headers", None)
            envelope["response_headers"] = dict(headers.items()) if headers is not None else {}
            get_all = getattr(headers, "get_all", None)
            lengths = (get_all("Content-Length", []) if get_all else
                       ([headers.get("Content-Length")] if headers and headers.get("Content-Length") is not None else []))
            encodings = (get_all("Transfer-Encoding", []) if get_all else
                         ([headers.get("Transfer-Encoding")] if headers and headers.get("Transfer-Encoding") is not None else []))
            envelope["content_length_values"] = lengths
            envelope["transfer_encoding_values"] = encodings
            framing_error, declared_length = None, None
            if lengths:
                value = str(lengths[0]).strip()
                if len(lengths) != 1 or not value.isascii() or not value.isdigit() or len(value) > 20:
                    framing_error = "InvalidContentLength"
                else:
                    declared_length = int(str(lengths[0]).strip())
            native = response if isinstance(response, http.client.HTTPResponse) else getattr(response, "fp", None)
            if encodings:
                if len(encodings) != 1 or str(encodings[0]).strip().lower() != "chunked" or lengths:
                    framing_error = "UnsupportedOrAmbiguousTransferFraming"
                elif isinstance(native, http.client.HTTPResponse) and native.chunked and native.fp is not None:
                    observer = _ChunkFramingObserver(native.fp, max_bytes + 1,
                                                     deadline_monotonic, timeout)
                    native.fp = observer
                else:
                    framing_error = "UnverifiedChunkFraming"
            try:
                # Native read(n) may consume a buffered prefix and then raise
                # while waiting for the remaining n bytes. read1(n) returns the
                # available non-chunked bytes before another blocking syscall.
                # Native chunked decoding must use read(), which enforces the
                # same strict framing/partial-prefix behavior as before. Its
                # framing observer now checks the absolute model deadline.
                incremental = isinstance(native, http.client.HTTPResponse) and not native.chunked
                reader = native.read1 if incremental else response.read

                def bound_native_body_read():
                    # The header reader has already set a socket idle timeout.
                    # Each subsequent read1() must instead use the *remaining*
                    # whole-request budget; a clock check alone cannot interrupt
                    # a blocked socket read before its older idle timeout.
                    if not incremental or deadline_monotonic is None:
                        return
                    remaining = deadline_monotonic - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError('absolute response deadline exceeded')
                    stream = native.fp
                    sock = getattr(getattr(stream, 'raw', stream), '_sock', None)
                    if sock is not None:
                        sock.settimeout(max(.001, min(timeout, remaining)))
                if chunk_size is None and not incremental:
                    enforce_deadline()
                    raw = response.read(max_bytes + 1)
                    enforce_deadline()
                else:
                    while len(raw) <= max_bytes:
                        enforce_deadline()
                        bound_native_body_read()
                        chunk = reader(min(chunk_size or 65536, max_bytes + 1 - len(raw)))
                        if not chunk:
                            enforce_deadline()
                            break
                        raw += chunk
                        retain(raw)
                        # A body chunk returned after deadline remains observed
                        # evidence, even when the response cannot be accepted.
                        enforce_deadline()
                enforce_deadline()
                complete = len(raw) <= max_bytes
            except http.client.IncompleteRead as exc:
                raw, complete = bytes(observer.prefix) if observer else raw + exc.partial, False
                envelope["transport_error"] = "IncompleteRead"
            if declared_length is not None and len(raw) != declared_length:
                framing_error = "ContentLengthMismatch"
            if observer is not None and observer.phase != "complete":
                framing_error = "IncompleteChunkFraming"
            if framing_error:
                complete = False
                envelope["framing_error"] = framing_error
            retain(raw, complete)
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
        # Native chunk decoding can raise after observing complete chunks but
        # before read() returns its aggregated body. Preserve the observer's
        # bounded decoded prefix even on timeout, reset, or response-close error.
        retain(bytes(observer.prefix) if observer is not None else raw)
        envelope["response_complete"] = False
        envelope["response_hash_scope"] = "retained_prefix"
        envelope["transport_error"] = type(exc).__name__
        raise ResponseTransportError("HTTP transport failed: " + type(exc).__name__, envelope) from exc
    finally:
        envelope["received_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if envelope["http_status"] != 200:
        raise ResponseTransportError("HTTP response rejected: " + str(envelope["http_status"]), envelope)
    if not envelope["response_complete"]:
        raise ResponseTransportError("HTTP response exceeds size ceiling or is incomplete", envelope)
    return raw[:max_bytes], envelope


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for buf in iter(lambda: f.read(1024 * 1024), b""):
            h.update(buf)
    return h.hexdigest()


def load() -> tuple[dict, str]:
    raw = FROZEN.read_bytes()
    p = json.loads(raw)
    if (p.get("schema") != "far-uncertain-routing/0.1"
            or p.get("status") != "RESEARCH_FROZEN_TASK_AUTHOR"
            or p.get("action_vocabulary") != list(ACTIONS)
            or p.get("case_count") != 12
            or p.get("controls", {}).get("model_sha256") != MODEL_SHA256
            or p.get("controls", {}).get("model_calls") != 12):
        raise StudyError("frozen protocol mismatch")
    tasks = p.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 12:
        raise StudyError("case count drift")
    if len({c["id"] for c in tasks}) != 12:
        raise StudyError("duplicate case")
    if len({c["prompt"] for c in tasks}) != 12:
        raise StudyError("duplicate model inputs")
    for c in tasks:
        if (not isinstance(c.get("prompt"), str) or not c["prompt"].strip()
                or not isinstance(c.get("admissible"), list)
                or not (1 <= len(c["admissible"]) <= 4)
                or len(set(c["admissible"])) != len(c["admissible"])
                or any(a not in ACTIONS or a == "VERIFY_EXPLICIT" for a in c["admissible"])):
            raise StudyError("invalid set-valued task-author admissibility")
    return p, digest(raw)


def request_model(prompt: str, endpoint: str = ENDPOINT) -> dict:
    if endpoint != ENDPOINT:
        raise StudyError("only the local pinned server can be used")
    data = {
        "model": MODEL, "temperature": 0, "stream": False, "max_tokens": 32,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Case text (untrusted task data):\n" + prompt},
        ],
    }
    reqbytes = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, reqbytes,
                                 headers={"Content-Type": "application/json"}, method="POST")
    request_evidence = {"request": data, "request_sha256": digest(reqbytes)}
    try:
        response_bytes, transport = read_bounded_response(req, timeout=60, max_bytes=1024 * 1024)
    except ResponseTransportError as exc:
        raise ModelResponseError("local model transport failed: " + str(exc),
                                 {**request_evidence, **exc.envelope}) from exc
    # The raw envelope is constructed before any model-output validation.
    # An invalid completion is evidence, not something to silently discard.
    envelope = {
        **request_evidence, **transport,
    }
    try:
        payload = json.loads(response_bytes)
        text = payload["choices"][0]["message"]["content"]
        usage = payload["usage"]["total_tokens"]
        identity = payload["model"]
        if not isinstance(text, str) or type(usage) is not int or usage < 1:
            raise StudyError("invalid model telemetry")
        if not isinstance(identity, str) or not identity:
            raise StudyError("model identity missing")
        action = text.strip() if text.strip() in ACTIONS else "INVALID_ACTION"
        return {
            "action": action, "raw_choice": text,
            "reported_model": identity, "total_tokens": usage,
            **envelope,
        }
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ModelResponseError("invalid provider output: " + type(exc).__name__, envelope) from exc


def persist(path: Path, obj: dict) -> None:
    """Atomic per-call evidence checkpoint: a later model failure loses no earlier trace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def evaluate(protocol: dict, source_hash: str, model_path: Path,
             runner=request_model, checkpoint=None) -> dict:
    if sha256_file(model_path) != MODEL_SHA256:
        raise StudyError("model SHA-256 mismatch")
    records = []
    identity = set()
    for task in protocol["tasks"]:
        began = time.perf_counter_ns()
        try:
            event = runner(task["prompt"])
        except ModelResponseError as exc:
            if checkpoint is not None:
                checkpoint({
                    "schema": "far-uncertain-routing-execution/0.1",
                    "status": "FAILED_OR_INCOMPLETE",
                    "protocol_sha256": source_hash,
                    "completed": len(records),
                    "records": records,
                    "failed_model_call": {
                        "case_id": task["id"],
                        "reason": str(exc),
                        "raw_envelope": exc.envelope,
                    },
                    "claim": "NOT_ESTABLISHED",
                })
            raise
        ms = (time.perf_counter_ns() - began) / 1_000_000
        if event["action"] not in ACTIONS + ("INVALID_ACTION",):
            raise StudyError("invalid runner action outside bounded vocabulary")
        if (type(event["total_tokens"]) is not int or event["total_tokens"] < 1
                or not isinstance(event["reported_model"], str) or not event["reported_model"]):
            raise StudyError("missing model telemetry")
        identity.add(event["reported_model"])
        row = {
            "id": task["id"], "action": event["action"],
            "admissible": event["action"] in task["admissible"],
            "unsafe_verification": event["action"] == "VERIFY_EXPLICIT",
            "elapsed_ms": ms, "model": event["reported_model"],
            "total_tokens": event["total_tokens"], "prompt_sha256": digest(task["prompt"].encode()),
            "raw_model_event": event,
        }
        records.append(row)
        if checkpoint is not None:
            checkpoint({
                "schema": "far-uncertain-routing-execution/0.1",
                "status": "INCOMPLETE",
                "protocol_sha256": source_hash,
                "completed": len(records),
                "records": records,
                "claim": "NOT_ESTABLISHED",
            })
    if len(identity) != 1:
        raise StudyError("model identity drift")
    count = len(records)
    # Score every constant action using the same frozen, set-valued rubric.
    # A model that emits one action on every task is not an adaptive router.
    fixed_scores = {
        action: sum(action in task["admissible"] for task in protocol["tasks"])
        for action in ACTIONS
    }
    action_counts = {action: sum(r["action"] == action for r in records)
                     for action in ACTIONS + ("INVALID_ACTION",)}
    return {
        "schema": "far-uncertain-routing-execution/0.1",
        "status": "EXECUTED_INTERNAL_RESEARCH",
        "protocol_sha256": source_hash,
        "model_sha256": MODEL_SHA256,
        "model_reported": next(iter(identity)),
        "n": count,
        "summary": {
            "agent_admissible": sum(x["admissible"] for x in records),
            "fixed_discover_contract_admissible": fixed_scores["DISCOVER_CONTRACT"],
            "fixed_action_scores": fixed_scores,
            "model_action_counts": action_counts,
            "unique_model_actions": sum(n > 0 for n in action_counts.values()),
            "model_minus_best_constant": (
                sum(x["admissible"] for x in records)
                - max(fixed_scores.values())
            ),
            "unsafe_verification": sum(x["unsafe_verification"] for x in records),
            "invalid_action": sum(x["action"] == "INVALID_ACTION" for x in records),
            "model_tokens": sum(x["total_tokens"] for x in records),
            "model_median_ms": statistics.median(x["elapsed_ms"] for x in records),
        },
        "records": records,
        "claim": "SCOPED_TASK_AUTHOR_SET_VALUED_OBSERVATION_ONLY",
        "limitations": [
            "Task-author admissible sets not independently adjudicated",
            "No uniquely optimal next action on under-specified inputs",
            "Simulated routing decisions; no evidence retrieval or discovery tool execution",
            "Small public 12-case curated set; no population inference",
            "Compare model against every constant action; task-author admissibility is not an independent oracle",
            "Repeated one-action output cannot demonstrate adaptation even if its score is high",
            "One quantized 0.5B CPU model, no comparison to frontier agents",
        ],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("validate", "run"))
    ap.add_argument("--model", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args(argv)
    try:
        p, h = load()
        if args.command == "validate":
            print(json.dumps({"status": "FROZEN_INPUT_VALID", "sha256": h, "cases": 12}))
            return 0
        if args.model is None or args.output is None:
            raise StudyError("run requires --model and --output")
        partial = args.output.with_name(args.output.stem + ".partial.json")
        result = evaluate(p, h, args.model,
                          checkpoint=lambda x: persist(partial, x))
        persist(args.output, result)
        partial.unlink(missing_ok=True)
        print(json.dumps({"status": result["status"], "summary": result["summary"],
                          "claim": result["claim"]}, sort_keys=True))
        return 0
    except (StudyError, OSError, ValueError, KeyError, TypeError) as exc:
        if args.command == "run" and args.output is not None:
            persist(args.output.with_name(args.output.stem + ".failure.json"),
                    {"status": "FAILED_OR_INCOMPLETE", "reason_class": type(exc).__name__,
                     "claim": "NOT_ESTABLISHED"})
        print(json.dumps({"status": "BLOCKED", "error_class": type(exc).__name__,
                          "reason": str(exc), "claim": "NOT_ESTABLISHED"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
