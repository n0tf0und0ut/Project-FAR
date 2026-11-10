"""Read-only, bounded public-source retrieval for Research investigation execution.

An operator supplies the host policy; model and source text cannot expand it.
Content, links and search hits are untrusted observations, never instructions.
DNS checks default to public-address preflight. An operator can explicitly select
``dns_mode='proxy'`` when DNS is available only through the inherited HTTPS proxy.
That mode requires and forces the configured proxy, rejects bypass rules, and
records DNS addresses as unknown. The proxy then owns destination/DNS enforcement;
this module does not claim to pin its resolution or authenticate source truth.
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import ipaddress
import json
import socket
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.parse import urlencode, urljoin, urlsplit

from mechanization.far_mechanization.intake_v1 import _strict_json_loads
from tools.far_uncertain_routing_pilot import read_bounded_response, ResponseTransportError


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class ToolError(ValueError):
    """A rejected or failed tool call, retaining the observed response prefix."""

    def __init__(self, message: str, receipt: dict):
        super().__init__(message)
        self.receipt = receipt


@dataclass(frozen=True)
class RetrievalPolicy:
    allowed_hosts: tuple[str, ...]
    max_bytes: int = 2_000_000
    timeout: float = 25.0
    resolver: Callable = field(default=socket.getaddrinfo, repr=False, compare=False)
    dns_mode: str = "preflight"

    def __post_init__(self):
        if (type(self.max_bytes) is not int or not 1 <= self.max_bytes <= 20_000_000
                or type(self.timeout) not in (int, float) or not 0 < self.timeout <= 60):
            raise ValueError("invalid retrieval resource bounds")
        if not self.allowed_hosts or any(not _valid_host(h) for h in self.allowed_hosts):
            raise ValueError("allowed_hosts must contain exact public DNS host names")
        if self.dns_mode not in ("preflight", "proxy"):
            raise ValueError("dns_mode must be preflight or explicitly operator-selected proxy")
        object.__setattr__(self, "allowed_hosts", tuple(h.lower() for h in self.allowed_hosts))


def _valid_host(host: Any) -> bool:
    if not isinstance(host, str) or host != host.strip() or not host.isascii():
        return False
    host = host.lower()
    if ("." not in host or host.endswith(".") or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-." for c in host)
            or any(not p or p.startswith("-") or p.endswith("-") or len(p) > 63 for p in host.split("."))
            or host.endswith((".localhost", ".local", ".internal", ".test", ".invalid"))):
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        return True


class _ProxyPolicyError(ValueError):
    """Controlled diagnostics never containing the configured proxy URI."""


def _proxy_configuration(host: str) -> tuple[str, str]:
    """Return private configuration and a separately safe hostname for receipts."""
    configured = urllib.request.getproxies().get("https")
    if not isinstance(configured, str) or not configured:
        raise _ProxyPolicyError("explicit proxy DNS mode requires an inherited HTTPS proxy")
    try:
        parsed = urlsplit(configured)
        proxy_host = parsed.hostname
        if (parsed.scheme not in ("http", "https") or not proxy_host or not proxy_host.isascii()
                or any(ord(c) < 33 or ord(c) == 127 for c in configured)
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment
                or parsed.port is not None and not 1 <= parsed.port <= 65535):
            raise ValueError("invalid proxy configuration")
        # The inherited proxy can have an internal DNS name or IP address. Its
        # location is operator configuration, never supplied by source/model text.
        if any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.:" for c in proxy_host):
            raise ValueError("invalid proxy hostname")
    except (ValueError, TypeError, AttributeError) as exc:
        raise _ProxyPolicyError("inherited HTTPS proxy configuration is invalid") from exc
    if urllib.request.proxy_bypass(host):
        raise _ProxyPolicyError("proxy bypass forbids explicit proxy DNS mode for this host")
    return configured, proxy_host.lower()



# Blocking system resolution is not cancellable on its caller's thread.
# A finite number of daemon workers lets deadlines fail closed even when
# getaddrinfo hangs; expired workers keep their slot until actually finished.
_DNS_PENDING_LIMIT = threading.BoundedSemaphore(8)


def _deadline_resolve(host: str, policy: RetrievalPolicy, deadline_monotonic: float | None):
    end = min(time.monotonic() + policy.timeout,
              deadline_monotonic if deadline_monotonic is not None else float('inf'))
    remaining = end - time.monotonic()
    if remaining <= 0 or not _DNS_PENDING_LIMIT.acquire(timeout=remaining):
        raise TimeoutError("DNS preflight deadline exhausted")
    answer = {}
    finished = threading.Event()

    def resolve():
        try:
            answer['rows'] = policy.resolver(host, 443, type=socket.SOCK_STREAM)
        except BaseException as exc:
            answer['exception'] = exc
        finally:
            _DNS_PENDING_LIMIT.release()
            finished.set()

    worker = threading.Thread(target=resolve, name="far-dns-preflight", daemon=True)
    try:
        worker.start()
    except BaseException:
        _DNS_PENDING_LIMIT.release()
        raise
    if not finished.wait(max(0., end - time.monotonic())):
        raise TimeoutError("DNS preflight deadline exhausted")
    if 'exception' in answer:
        raise answer['exception']
    if time.monotonic() > end:
        raise TimeoutError("DNS preflight deadline exhausted")
    return answer['rows']


def validate_url(url: str, policy: RetrievalPolicy, *, deadline_monotonic: float | None = None) -> dict:
    """Validate exact hostname, then the explicitly chosen DNS trust boundary."""
    if not isinstance(url, str) or len(url) > 8192 or any(ord(c) < 33 or ord(c) == 127 for c in url):
        raise ValueError("invalid URL transport")
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if (parsed.scheme != "https" or parsed.username is not None or parsed.password is not None
            or parsed.fragment or parsed.port not in (None, 443) or not _valid_host(host)
            or host not in policy.allowed_hosts or "\\" in url):
        raise ValueError("destination outside exact operator HTTPS policy")
    if policy.dns_mode == "proxy":
        _, proxy_host = _proxy_configuration(host)
        return {"host": host, "addresses": None, "validated_at": _now(), "dns_mode": "proxy",
                "proxy_host": proxy_host, "public_ip_validation": "UNESTABLISHED",
                "transport_boundary": "Exact HTTPS hostname policy; inherited forced proxy owns DNS and destination enforcement; resolved target addresses unknown"}
    results = _deadline_resolve(host, policy, deadline_monotonic)
    addresses = sorted({row[4][0] for row in results})
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError("DNS returned no address or a non-public destination")
    return {"host": host, "addresses": addresses, "validated_at": _now(), "dns_mode": "preflight",
            "transport_boundary": "validated DNS preflight; environment proxy/TLS trust remains applicable"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


class _RequiredProxyHandler(urllib.request.ProxyHandler):
    """Refuse urllib's ordinary direct fallback when a bypass rule is present."""

    def proxy_open(self, req, proxy, type):
        if req.host and urllib.request.proxy_bypass(req.host):
            raise _ProxyPolicyError("proxy bypass forbids explicit proxy DNS mode for this host")
        return super().proxy_open(req, proxy, type)


def _envelope(url: str) -> dict:
    return {"schema": "far-source-receipt/0.1", "request": {
        "url": url, "method": "GET", "headers": {
            "Accept": "application/json,text/html,text/plain;q=0.8",
            "Accept-Encoding": "identity", "User-Agent": "Project-FAR-Research/0.1",
        }}, "retrieved_at": None, "status": "STARTED", "http_status": None,
        "content_type": None, "raw_base64": "", "sha256": _sha(b""),
        "observed_bytes": 0, "truncated": False, "error": None}


def retrieve(url: str, policy: RetrievalPolicy, *, checkpoint: Callable | None = None,
             opener: Any = None, deadline_monotonic: float | None = None) -> dict:
    """Perform one GET; persist received bytes before content parsing or rejection.

    A response larger than max_bytes retains the observed max_bytes+1 prefix.
    HTTP errors retain the same bounded response body. No automatic redirects,
    cookies, authorization, caller-supplied headers, writes or arbitrary methods.
    The optional opener exists for test transports and must be operator supplied.
    """
    receipt = _envelope(url)
    started = time.monotonic()
    # Bound the entire DNS + HTTP operation by both transport and campaign
    # deadlines instead of resetting the transport window after DNS.
    request_deadline = min(started + policy.timeout,
                           deadline_monotonic if deadline_monotonic is not None else float('inf'))
    next_progress_bytes = 65536

    def save():
        receipt["elapsed_seconds"] = time.monotonic() - started
        if checkpoint is not None:
            checkpoint(json.loads(json.dumps(receipt)))

    save()
    try:
        receipt["destination"] = validate_url(url, policy, deadline_monotonic=request_deadline)
        req = urllib.request.Request(url, headers=receipt["request"]["headers"], method="GET")
        if policy.dns_mode == "proxy":
            configured_proxy, proxy_host = _proxy_configuration(receipt["destination"]["host"])
            if proxy_host != receipt["destination"]["proxy_host"]:
                raise _ProxyPolicyError("inherited proxy changed after destination validation")
            client = opener if opener is not None else urllib.request.build_opener(
                _RequiredProxyHandler({"https": configured_proxy}), _NoRedirect())
        else:
            client = opener if opener is not None else urllib.request.build_opener(_NoRedirect())
        def capture(transport):
            nonlocal next_progress_bytes
            receipt["http_status"] = transport["http_status"]
            headers = {k.lower(): v for k, v in transport["response_headers"].items()}
            receipt["content_type"] = headers.get("content-type", "")
            receipt["content_encoding"] = headers.get("content-encoding", "identity")
            receipt["response_url"] = transport.get("response_url", url)
            receipt.update(raw_base64=transport["raw_response_base64"],
                           sha256=transport["response_sha256"],
                           observed_bytes=transport["response_bytes_retained"],
                           truncated=transport["response_bytes_retained"] > policy.max_bytes,
                           retrieved_at=_now(), status="RECEIVED")
            # The reader reports an accumulated body after each bounded read.
            # Keep progressive checkpoints at geometric thresholds, plus every
            # terminal/failure snapshot. This bounds journal growth for a large
            # permitted source while preserving exact interrupted prefixes.
            size = receipt["observed_bytes"]
            terminal = (transport.get("response_complete") is True
                        or transport.get("transport_error") is not None
                        or transport.get("framing_error") is not None)
            if size >= next_progress_bytes or terminal:
                while size >= next_progress_bytes:
                    next_progress_bytes *= 2
                save()

        try:
            # Preserve the established max_bytes+1 failure-prefix contract while
            # delegating all declared-length and chunk framing checks to the
            # same bounded reader used by the model and historical source tools.
            raw, transport = read_bounded_response(
                req, timeout=policy.timeout, max_bytes=policy.max_bytes + 1,
                opener=client, checkpoint=capture, chunk_size=65536,
                deadline_monotonic=request_deadline)
        except ResponseTransportError as exc:
            capture(exc.envelope)
            receipt["transport"] = exc.envelope
            raise ValueError("incomplete or rejected HTTP transport") from exc
        receipt["transport"] = transport
        if receipt["response_url"] != url:
            raise ValueError("redirect refused")
        if receipt["truncated"]:
            raise ValueError("response exceeds byte ceiling; preserved prefix only")
        if receipt["content_encoding"].lower() not in ("", "identity"):
            raise ValueError("compressed response refused")
        if not raw:
            raise ValueError("empty response")
        receipt["status"] = "RETRIEVED"
        save()
        return receipt
    except (ValueError, OSError, TimeoutError, urllib.error.URLError, http.client.HTTPException) as exc:
        receipt["status"] = "FAILED"
        receipt["retrieved_at"] = receipt["retrieved_at"] or _now()
        # Proxy implementation diagnostics may interpolate their configured URI.
        # Keep only controlled policy diagnostics or the exception class in this
        # explicit mode; never serialize proxy credentials or complete values.
        reason = (str(exc) if policy.dns_mode != "proxy" or isinstance(exc, _ProxyPolicyError)
                  else "Proxy-mode transport failed; original diagnostic withheld to protect configured credentials")
        receipt["error"] = {"class": type(exc).__name__, "reason": reason}
        save()
        raise ToolError("source retrieval failed: " + type(exc).__name__, receipt) from exc


class _VisibleHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ignored: list[str] = []
        self.parts: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "template"):
            self.ignored.append(tag)
        if not self.ignored:
            if tag in ("p", "div", "br", "li", "h1", "h2", "h3", "tr"):
                self.parts.append("\n")
            if tag == "a":
                self.links.extend(v for k, v in attrs if k == "href" and v)

    def handle_endtag(self, tag):
        if self.ignored and tag == self.ignored[-1]:
            self.ignored.pop()
        if not self.ignored and tag in ("p", "div", "li", "h1", "h2", "h3", "tr"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def receipt_bytes(receipt: dict) -> bytes:
    raw = base64.b64decode(receipt["raw_base64"], validate=True)
    if _sha(raw) != receipt["sha256"] or len(raw) != receipt["observed_bytes"]:
        raise ToolError("source receipt hash/length mismatch", receipt)
    return raw


def _enforce_bounded_document_depth(document, *, max_depth=64):
    """Reject deeply nested source JSON before recursive state checkpoints."""
    pending = [(document, 0)]
    while pending:
        node, depth = pending.pop()
        if depth > max_depth:
            raise ValueError('source JSON nesting limit exceeded')
        if type(node) is dict:
            pending.extend((child, depth + 1) for child in node.values())
        elif type(node) is list:
            pending.extend((child, depth + 1) for child in node)


def parse_receipt(receipt: dict) -> dict:
    """Extract data only. An extraction failure keeps the original raw receipt."""
    try:
        if receipt["status"] != "RETRIEVED" or receipt["truncated"]:
            raise ValueError("only complete successful observations can be parsed")
        raw = receipt_bytes(receipt)
        text = raw.decode("utf-8", errors="strict")
        content_type = (receipt.get("content_type") or "").split(";", 1)[0].lower().strip()
        result = {"source_sha256": receipt["sha256"], "dependency_host": urlsplit(receipt["request"]["url"]).hostname,
                  "links": [], "text": text, "format": "text", "authority": "UNTRUSTED_SOURCE_DATA"}
        if content_type == "application/json" or content_type.endswith("+json"):
            document = _strict_json_loads(text)
            _enforce_bounded_document_depth(document)
            result["document"] = document
            result["format"] = "json"
        elif content_type in ("text/html", "application/xhtml+xml"):
            parser = _VisibleHTML()
            parser.feed(text)
            parser.close()
            result["text"] = "".join(parser.parts)
            result["links"] = sorted({urljoin(receipt["request"]["url"], link) for link in parser.links})
            result["format"] = "html-visible-text"
        elif content_type and not content_type.startswith("text/"):
            raise ValueError("unsupported content type")
        result["projection_sha256"] = _sha(result["text"].encode("utf-8"))
        return result
    except (ValueError, KeyError, TypeError, UnicodeError) as exc:
        if isinstance(exc, ToolError):
            raise
        raise ToolError("source parse failed: " + type(exc).__name__, receipt) from exc


def bind_quote(receipt: dict, quote: str, *, start: int | None = None) -> dict:
    """Bind an exact contiguous quote to a reproducible source-text projection.

    HTML entities/tags are projected explicitly, so offsets denote Unicode code
    points in visible text, not raw bytes. The original byte hash remains bound.
    """
    parsed = parse_receipt(receipt)
    text = parsed["text"]
    if not isinstance(quote, str) or not quote:
        raise ToolError("quote must be nonempty exact text", receipt)
    location = text.find(quote) if start is None else start
    if type(location) is not int or location < 0 or text[location:location + len(quote)] != quote:
        raise ToolError("quote absent from source projection", receipt)
    return {"source_sha256": receipt["sha256"], "projection_sha256": parsed["projection_sha256"],
            "quote": quote, "start": location, "end": location + len(quote),
            "offset_semantics": "Unicode code points in " + parsed["format"],
            "authority": "SOURCE_ASSERTION_NOT_VERIFIED_TRUTH"}


def search(query: str, policy: RetrievalPolicy, *, provider: Callable | None = None,
           checkpoint: Callable | None = None) -> dict:
    """Execute an operator-installed search adapter and validate, never invent hits.

    Provider signature: provider(query, policy, checkpoint) -> {receipt, hits}.
    receipt is a successful actual retrieval receipt whose parsed JSON or text
    is retained. Every hit {url,title} must be quoted in that response text.
    Search-result URLs are not fetched here and remain subject to retrieve policy.
    """
    if not isinstance(query, str) or not query.strip() or len(query) > 4000:
        raise ToolError("invalid search query", {"status": "REJECTED", "query": query})
    if provider is None:
        raise ToolError("search provider unavailable", {"status": "UNAVAILABLE", "query": query})
    result = provider(query, policy, checkpoint)
    receipt = result["receipt"]
    parsed = parse_receipt(receipt)
    hits = result["hits"]
    if not isinstance(hits, list) or len(hits) > 50:
        raise ToolError("search result bounds invalid", receipt)
    checked = []
    for hit in hits:
        if (not isinstance(hit, dict) or not isinstance(hit.get("url"), str)
                or not isinstance(hit.get("title"), str)
                or hit["url"] not in parsed["text"] or hit["title"] not in parsed["text"]):
            raise ToolError("unanchored search hit", receipt)
        p = urlsplit(hit["url"])
        if p.scheme != "https" or p.username is not None or p.password is not None or not _valid_host(p.hostname):
            raise ToolError("invalid search hit URL", receipt)
        checked.append({"url": hit["url"], "title": hit["title"], "source_sha256": receipt["sha256"]})
    return {"query": query, "receipt": receipt, "hits": checked, "status": "SEARCH_COMPLETED"}


def public_search(query: str, provider: str, policy: RetrievalPolicy, *,
                  checkpoint: Callable | None = None, deadline_monotonic: float | None = None) -> dict:
    """Execute a fixed public no-key metadata search, preserving its response.

    Crossref uses its documented works endpoint (message.items[].URL/title).
    Wikimedia uses documented query+search records; page locators are derived
    transparently from actual pageid values, not represented as retrieved pages.
    Search relevance, completeness, publisher truth and source independence are
    unestablished. Search results never grant permission to fetch new hosts.

    API contracts: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
    and https://www.mediawiki.org/wiki/API:Search .
    """
    url = public_search_url(query, provider)
    receipt = retrieve(url, policy, checkpoint=checkpoint,
                       deadline_monotonic=deadline_monotonic)
    return project_public_search(query, provider, receipt)


def public_search_url(query, provider):
    """Canonical request locator for the supported no-key adapters."""
    if not isinstance(query, str) or not query.strip() or len(query) > 4000:
        raise ToolError("invalid search query", {"status": "REJECTED", "query": query})
    if provider == "crossref":
        url = "https://api.crossref.org/works?" + urlencode({"query": query, "rows": 5})
    elif provider == "wikimedia":
        url = "https://en.wikipedia.org/w/api.php?" + urlencode({
            "action": "query", "list": "search", "srsearch": query,
            "srlimit": 5, "format": "json", "utf8": 1,
        })
    else:
        raise ToolError("unknown public search provider", {"status": "UNAVAILABLE", "query": query, "provider": provider})
    return url


def project_public_search(query, provider, receipt):
    """Pure projection of retained native search metadata; no network call."""
    try:
        document = parse_receipt(receipt)["document"]
        hits = []
        skipped = []
        if provider == "crossref":
            records = document["message"]["items"]
        else:
            records = document["query"]["search"]
        if not isinstance(records, list) or len(records) > 5:
            raise ValueError("search API response bounds invalid")
        for index, record in enumerate(records):
            if provider == "crossref":
                title = record["title"][0]
                locator = record["URL"]
                basis = {"url_pointer": f"/message/items/{index}/URL",
                         "title_pointer": f"/message/items/{index}/title/0",
                         "derivation": "Literal URL and first title from returned Crossref metadata."}
            else:
                title = record["title"]
                pageid = record["pageid"]
                if type(pageid) is not int or pageid < 1:
                    raise ValueError("invalid Wikimedia pageid")
                locator = "https://en.wikipedia.org/?curid=" + str(pageid)
                basis = {"pageid_pointer": f"/query/search/{index}/pageid",
                         "title_pointer": f"/query/search/{index}/title",
                         "derivation": "Official MediaWiki curid locator constructed from returned numeric pageid; page not retrieved."}
            if not isinstance(title, str) or not title or not isinstance(locator, str):
                skipped.append({"index": index, "reason": "metadata lacks a string locator or nonempty title"})
                continue
            parsed = urlsplit(locator)
            if (parsed.scheme != "https" or parsed.username is not None or parsed.password is not None
                    or parsed.fragment or parsed.port not in (None, 443) or not _valid_host(parsed.hostname)):
                skipped.append({"index": index, "reason": "metadata lacks a safe literal HTTPS locator or nonempty title"})
                continue
            hits.append({"url": locator, "title": title, "source_sha256": receipt["sha256"], "basis": basis})
        return {"query": query, "provider": provider, "status": "SEARCH_COMPLETED", "receipt": receipt,
                "hits": hits, "skipped": skipped, "scope": "five returned metadata records; discovery only, not evidence of source truth"}
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        raise ToolError("malformed public search response: " + type(exc).__name__, receipt) from exc
