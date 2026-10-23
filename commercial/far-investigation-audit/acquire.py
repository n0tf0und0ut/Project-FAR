"""Permissioned, bounded source acquisition; external data never acquires authority.

Remote HTTPS is opt-in; DNS is checked *and the resulting public IP is pinned*
for the TLS connection. Redirects revalidate. Arbitrary media binaries are not
processed, and Youtube captions are opt-in through an optional utility.
"""
from __future__ import annotations

import html
import http.client
import ipaddress
import re
import socket
import ssl
import subprocess
import tempfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from engine import InvalidBundle, digest
from bounded_io import read_bounded, BoundedInputError

MAX_DOWNLOAD = 250_000
MAX_REDIRECTS = 2
MAX_TRANSCRIPT = 120_000
MAX_SEGMENTS = 2000
MAX_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")
TIME = r"(?:\d{2}:)?[0-5]\d:[0-5]\d[.,]\d{3}"
CUE = re.compile(rf"(?P<start>{TIME})\s+-->\s+(?P<end>{TIME})(?:\s+.*)?\Z")


class AcquisitionError(ValueError):
    pass


class _VisibleText(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head", "nav", "footer", "form"}
    BREAK = {"p", "div", "section", "article", "h1", "h2", "h3", "h4", "li", "br", "tr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = []
        self.chunks = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip.append(tag)
        if tag in self.BREAK and not self.skip:
            self.chunks.append("\n")

    def handle_endtag(self, tag):
        if tag in self.skip:
            # Restore parsing after a matching nested excluded element.
            for i in range(len(self.skip) - 1, -1, -1):
                if self.skip[i] == tag:
                    del self.skip[i:]
                    break
        if tag in self.BREAK and not self.skip:
            self.chunks.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.chunks.append(data)


def normalize_html(raw: str) -> str:
    parser = _VisibleText()
    parser.feed(raw)
    lines = [re.sub(r"\s+", " ", x).strip() for x in "".join(parser.chunks).splitlines()]
    text = "\n".join(line for line in lines if line)
    if not text:
        raise AcquisitionError("HTML extraction produced no visible text")
    return text[:MAX_TRANSCRIPT]


def safe_url(url: str) -> tuple[str, str]:
    if not isinstance(url, str) or len(url) > 2048 or any(ord(c) < 32 or ord(c) > 126 for c in url):
        raise AcquisitionError("URL requires printable ASCII and must fit length cap")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise AcquisitionError("only credential-free HTTPS URLs are allowed")
    if parsed.port not in (None, 443):
        raise AcquisitionError("URL must use standard HTTPS port")
    host = parsed.hostname.lower()
    if not re.fullmatch(r"(?=.{4,253}$)[a-z0-9-]+(?:\.[a-z0-9-]+)+", host):
        raise AcquisitionError("invalid public DNS hostname")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise AcquisitionError("IP literals are not allowed")
    if host.endswith((".local", ".internal", ".localhost", ".test", ".invalid", ".example")):
        raise AcquisitionError("reserved/internal hostname blocked")
    target = parsed.path or "/"
    if parsed.query:
        target += "?" + parsed.query
    if len(target) > 2000:
        raise AcquisitionError("URL path too long")
    return host, target


def resolve_public(host: str) -> list[str]:
    try:
        answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise AcquisitionError("DNS lookup failed") from exc
    ips = sorted({a[4][0] for a in answers})
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise AcquisitionError("DNS resolution includes a non-public address")
    return ips


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host: str, ip: str, timeout: int = 8):
        super().__init__(host, port=443, timeout=timeout, context=ssl.create_default_context())
        self.pinned_ip = ip

    def connect(self):
        raw = socket.create_connection((self.pinned_ip, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def fetch_https(url: str, *, permit_network: bool = False, max_bytes: int = MAX_DOWNLOAD,
                connection_factory=None) -> dict:
    if not permit_network:
        raise AcquisitionError("remote source acquisition requires explicit network authorization")
    if not 0 < max_bytes <= MAX_DOWNLOAD:
        raise AcquisitionError("invalid size ceiling")
    current = url
    redirects = []
    for _ in range(MAX_REDIRECTS + 1):
        host, target = safe_url(current)
        ip = resolve_public(host)   # actual connection is pinned to this checked address
        conn = connection_factory(host, ip[0]) if connection_factory else _PinnedHTTPS(host, ip[0])
        try:
            conn.request("GET", target, headers={"User-Agent": "ProjectFARResearch/0.3", "Accept": "text/html,text/plain,text/vtt", "Accept-Encoding": "identity"})
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location:
                    raise AcquisitionError("redirect has no location")
                if len(redirects) >= MAX_REDIRECTS:
                    raise AcquisitionError("redirect limit exceeded")
                new_url = urljoin(current, location)
                safe_url(new_url)
                redirects.append({"from": current, "to": new_url})
                current = new_url
                continue
            if response.status != 200:
                raise AcquisitionError(f"upstream HTTP {response.status}")
            encoding = response.getheader("Content-Encoding", "identity").lower()
            if encoding not in ("identity", ""):
                raise AcquisitionError("compressed remote bodies unsupported")
            length = response.getheader("Content-Length")
            if length and (not length.isdecimal() or int(length) > max_bytes):
                raise AcquisitionError("content length exceeds cap")
            media_type = response.getheader("Content-Type", "").split(";")[0].strip().lower()
            if media_type not in {"text/html", "text/plain", "text/vtt", "application/xhtml+xml"}:
                raise AcquisitionError("remote content type unsupported")
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise AcquisitionError("remote document exceeds byte cap")
            try:
                decoded = raw.decode("utf-8", "strict")
            except UnicodeError as exc:
                raise AcquisitionError("remote content is not valid UTF-8") from exc
            text = normalize_html(decoded) if media_type in {"text/html", "application/xhtml+xml"} else decoded
            if not text.strip():
                raise AcquisitionError("remote content is empty")
            if len(text.encode("utf-8")) > MAX_DOWNLOAD:
                raise AcquisitionError("extracted text exceeds cap")
            return {"text": text, "raw_sha256": digest(raw), "raw_snapshot_utf8": decoded,
                    "url": current, "redirects": redirects,
                    "content_type": media_type, "extraction": "html_visible_text_v1" if "html" in media_type else "utf8_identity_v1",
                    "external_authenticity_verified": False}
        except (OSError, ssl.SSLError, TimeoutError, http.client.HTTPException) as exc:
            raise AcquisitionError("remote connection failed") from exc
        finally:
            conn.close()
    raise AcquisitionError("redirect limit exceeded")


def parse_captions(raw: str) -> dict:
    """Conservative SRT/VTT parser, preserving original cue times and spans."""
    if not isinstance(raw, str) or not 0 < len(raw.encode("utf-8")) <= MAX_TRANSCRIPT:
        raise AcquisitionError("caption size out of range")
    if raw.startswith("\ufeff"):
        raw = raw[1:]
    blocks = re.split(r"\r?\n\s*\r?\n", raw.replace("\r\n", "\n").strip())
    output = []
    parts = []
    for block_index, block in enumerate(blocks):
        lines = [x.strip(" \t") for x in block.splitlines() if x.strip(" \t")]
        if (not lines or (block_index == 0 and lines[0] == "WEBVTT")
                or lines[0] in {"STYLE", "REGION"}
                or re.match(r"NOTE(?:[ \t]|$)", lines[0])):
            continue
        matches = [i for i, x in enumerate(lines) if CUE.fullmatch(x)]
        if len(matches) != 1:
            raise AcquisitionError("malformed caption block")
        idx = matches[0]
        if idx > 1 or (idx == 1 and len(lines[0]) > 80):
            raise AcquisitionError("invalid caption cue identifier")
        cue = CUE.fullmatch(lines[idx])
        def ms(t):
            fields = re.split(r"[:.,]", t)
            hh, mm, sec, frac = fields if len(fields) == 4 else ["0", *fields]
            return ((int(hh) * 60 + int(mm)) * 60 + int(sec)) * 1000 + int(frac)
        start_ms, end_ms = ms(cue["start"]), ms(cue["end"])
        if end_ms <= start_ms or end_ms - start_ms > 3_600_000:
            raise AcquisitionError("invalid caption time interval")
        text = html.unescape(" ".join(re.sub(r"<[^>]{1,100}>", "", line) for line in lines[idx+1:])).strip()
        if not text:
            continue
        start = len("\n".join(parts)) + (1 if parts else 0)
        parts.append(text)
        output.append({"start_ms": start_ms, "end_ms": end_ms, "span": {"start": start, "end": start + len(text), "quote": text}})
        if len(output) > MAX_SEGMENTS:
            raise AcquisitionError("too many caption cues")
    if not output:
        raise AcquisitionError("no valid subtitle cues")
    return {"text": "\n".join(parts), "cues": output, "format": "srt_vtt"}


def youtube_id(url: str) -> str:
    host, _ = safe_url(url)
    p = urlsplit(url)
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = p.path.strip("/")
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if p.path == "/watch":
            from urllib.parse import parse_qs
            video_id = parse_qs(p.query).get("v", [""])[0]
        elif p.path.startswith(("/shorts/", "/embed/")):
            video_id = p.path.split("/")[2]
        else:
            raise AcquisitionError("unsupported YouTube path")
    else:
        raise AcquisitionError("URL is not on a supported YouTube domain")
    if not MAX_VIDEO_ID.fullmatch(video_id):
        raise AcquisitionError("invalid YouTube video ID")
    return video_id


def fetch_youtube_captions(url: str, *, permit_network: bool = False, executable: str = "yt-dlp") -> dict:
    if not permit_network:
        raise AcquisitionError("YouTube acquisition requires explicit network authorization")
    video_id = youtube_id(url)
    normalized = "https://www.youtube.com/watch?v=" + video_id
    with tempfile.TemporaryDirectory(prefix="far-captions-") as root:
        command = [executable, "--ignore-config", "--no-playlist", "--skip-download", "--write-subs", "--write-auto-subs",
                   "--sub-langs", "en", "--sub-format", "vtt", "--no-progress", "--no-warnings",
                   "--socket-timeout", "8", "--retries", "1", "--output", str(Path(root) / "caption.%(ext)s"), normalized]
        try:
            p = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=40, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AcquisitionError("YouTube caption extraction unavailable or timed out") from exc
        if p.returncode:
            raise AcquisitionError("YouTube captions unavailable (utility exit nonzero)")
        tracks = sorted(Path(root).glob("caption*.vtt"))
        if not tracks:
            raise AcquisitionError("no usable caption track")
        try:
            data = read_bounded(tracks[0], MAX_TRANSCRIPT)
        except (OSError, BoundedInputError) as exc:
            raise AcquisitionError("caption file size/type limit exceeded") from exc
        if len(data) > MAX_TRANSCRIPT:
            raise AcquisitionError("caption file too large")
        try:
            transcript = parse_captions(data.decode("utf-8", "strict"))
        except UnicodeError as exc:
            raise AcquisitionError("caption decode failed") from exc
        return {**transcript, "url": normalized, "raw_sha256": digest(data),
                "raw_snapshot_utf8": data.decode("utf-8", "strict"),
                "extraction": "yt_dlp_caption_vtt_v1",
                "external_authenticity_verified": False}
