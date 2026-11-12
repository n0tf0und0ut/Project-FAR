#!/usr/bin/env python3
"""Reviewable natural-language and GitHub-Issue intake for FAR's Research factory.

A requirement is *data*, not an instruction granting a coding agent permissions.
Only the explicit `submit` command creates queue state. This module never starts
workers, performs network writes, or bypasses protected GitHub controls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

try:
    from tools.software_factory import Factory, FactoryError, digest, validate_order
except ModuleNotFoundError:  # python tools/software_factory_intake.py
    from software_factory import Factory, FactoryError, digest, validate_order

INTAKE_SCHEMA = "far-software-factory/intake/1"
MAX_REQUEST_BYTES = 65536
MAX_ISSUE_BYTES = 131072
HEADING = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]+)?(?:acceptance(?:[ \t]+criteria)?|done[ \t]+when|"
    r"definition[ \t]+of[ \t]+done|success[ \t]+criteria)[ \t]*:?[ \t]*$",
    re.I | re.ASCII,
)
ATX_HEADING = re.compile(r"^[ \t]*#{1,6}(?:[ \t]+|$)")
PLAIN_LABEL = re.compile(r"^[A-Z][\w /-]{2,48}:[ \t]*$")
LIST_MARKER = r"(?:[-*+]|[0-9]{1,9}[.)])"
LIST_CONTAINER = re.compile(rf"^ {{0,3}}{LIST_MARKER}(?:[ \t]+|$)")
BULLET = re.compile(rf"^[ \t]*{LIST_MARKER}[ \t]+(?:\[[ xX]\]\s*)?(\S.*)$")
THEMATIC_BREAK = re.compile(r"^ {0,3}([*_-])(?:[ \t]*\1){2,}[ \t]*$")
FENCE = re.compile(r"^ {0,3}(?P<mark>`{3,}|~{3,})(?P<suffix>.*)$")
# GFM type 1 HTML blocks terminate on the exact tag, case-insensitively.
HTML_CONTROL = re.compile(r"<!--|-->|<pre(?:[ \t][^<>]*)?>|</pre>", re.I)
HTML_PRE_PREFIX = re.compile(r"</?pre\b", re.I)
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")


class IntakeError(FactoryError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not follow GitHub API redirects with a bearer credential."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _ensure_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IntakeError(f"{name} must be nonempty text")
    try:
        raw = value.encode("utf-8", "strict")
    except UnicodeError as exc:
        raise IntakeError(f"{name} is not valid UTF-8") from exc
    if len(raw) > MAX_REQUEST_BYTES or "\x00" in value:
        raise IntakeError(f"{name} is too large or contains NUL")
    return value


def _strict_json(raw: str) -> object:
    def unique(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise IntakeError(f"duplicate JSON key: {k}")
            d[k] = v
        return d

    def invalid(x):
        raise IntakeError(f"invalid JSON constant: {x}")

    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)
    except json.JSONDecodeError as exc:
        raise IntakeError(f"invalid JSON: {exc.msg}") from exc


def _reject_unhandled_html(text: str) -> None:
    """Fail closed on raw HTML other than recognized comment/pre examples.

    Unknown tags can introduce GFM HTML blocks whose contents look like live
    Markdown acceptance criteria. Never silently promote those example lines.
    Source inside Markdown fences, HTML comments, or pre blocks is excluded
    before this check; plain comparisons with a separated '<' stay literal.
    """
    if re.search(r"<(?=[A-Za-z!/?])", text):
        raise IntakeError("unsupported raw HTML requires clarification")


def _visible_html_line(line: str, pre: bool, comment: bool,
                       acceptance: bool) -> tuple[str, bool, bool]:
    """Exclude raw HTML examples by source order, before heading extraction.

    Each marker is consumed under the state at its own position: a comment
    inside preformatted code cannot close an outer comment, and a pre tag
    inside a comment cannot open code. Ambiguous mixed visible/HTML content
    must be clarified instead of silently shortening requirements.
    """
    visible: list[str] = []
    pos = 0
    found = False
    tokens = list(HTML_CONTROL.finditer(line))
    complete_pre_starts = {
        match.start() for match in tokens
        if match.group(0).lower().startswith(("<pre", "</pre"))
    }
    # Valid HTML pre tags can span physical source lines. A per-line parser
    # must reject incomplete delimiters rather than promoting their hidden
    # example criteria into real acceptance requirements.
    for prefix in HTML_PRE_PREFIX.finditer(line):
        if prefix.start() not in complete_pre_starts:
            raise IntakeError("multiline or malformed HTML pre tag requires clarification")
    for match in tokens:
        found = True
        token = match.group(0).lower()
        if not pre and not comment:
            fragment = line[pos:match.start()]
            # GFM tag/container whitespace is ASCII space/tab. Python's
            # Unicode-aware str.strip() would erase NBSP before <pre>, enter
            # the wrong HTML state and skip a real subsequent code fence.
            if any(ch.isspace() and ch not in " \t" for ch in fragment):
                raise IntakeError("non-GFM whitespace before HTML delimiter requires clarification")
            _reject_unhandled_html(fragment)
            visible.append(fragment)
        if pre:
            if token.startswith("</pre"):
                pre = False
            elif token.startswith("<pre"):
                raise IntakeError("nested HTML preformatted examples are ambiguous")
        elif comment:
            if token == "-->":
                comment = False
        elif token == "<!--":
            if acceptance:
                raise IntakeError("HTML comment in acceptance criteria requires clarification")
            comment = True
        elif token.startswith("<pre"):
            if acceptance:
                raise IntakeError("HTML code in acceptance criteria requires clarification")
            pre = True
        else:
            if acceptance:
                raise IntakeError("stray HTML close in acceptance criteria")
            raise IntakeError("stray HTML closing delimiter requires clarification")
        pos = match.end()
    if not pre and not comment:
        fragment = line[pos:]
        _reject_unhandled_html(fragment)
        visible.append(fragment)
    result = "".join(visible)
    if found and result.strip():
        raise IntakeError("mixed HTML examples and visible prose require clarification")
    return result, pre, comment


def _criteria(body: str) -> list[str]:
    """Extract explicit acceptance bullets without silently losing requirements.

    Indented Markdown continuations are joined. Unexpected prose or fenced code
    inside a criteria section is rejected, not interpreted as instructions.
    """
    result: list[str] = []
    in_section = False
    last_bullet: int | None = None
    fence: tuple[str, int] | None = None
    html_pre = False
    html_comment = False
    container_paragraph = False
    list_context = False
    blank = True
    for line in re.split(r"\r\n|\n|\r", body):
        blank_before, blank = blank, not line.strip(" \t")
        if blank:
            container_paragraph = False
        marker = FENCE.fullmatch(line)
        if fence is not None:
            if (marker and not marker.group("suffix").strip(" \t")
                    and marker.group("mark")[0] == fence[0]
                    and len(marker.group("mark")) >= fence[1]):
                fence = None
            continue
        # Classify literal Markdown blocks before interpreting HTML markers.
        # Four-column indentation means a marker in the code is only text;
        # an info string on an opening fence is likewise never an HTML tag.
        # Preserve open pre/comment state so its genuine closer is still read.
        if not html_pre and not html_comment:
            content = line.lstrip(" \t")
            indentation = line[:len(line) - len(content)]
            columns = 0
            for char in indentation:
                columns = columns + 1 if char == " " else (columns // 4 + 1) * 4
            # A blank line ends the current paragraph, but an indented
            # nonblank line can resume a list item at any supported indent.
            possible_list_block = columns > 0 and list_context
            if not in_section and possible_list_block and content:
                container_paragraph = True
            # An indented fence may belong to a list item even when its
            # absolute indent also matches the top-level fence grammar. The
            # flat parser cannot bind its closer to the correct container.
            if (possible_list_block or columns >= 4) and FENCE.fullmatch(content):
                raise IntakeError("ambiguous indented Markdown fence requires clarification")
            if possible_list_block and HTML_CONTROL.match(content):
                raise IntakeError("ambiguous indented HTML example requires clarification")
            if columns >= 4 and line.strip():
                if in_section:
                    raise IntakeError("indented code in acceptance criteria requires clarification")
                continue
            # The intake parser intentionally supports only top-level fence
            # openers. GFM also permits fences nested in list/blockquote
            # containers, which can desynchronize the flat state machine and
            # promote sample text as executable acceptance criteria.
            # Reject every marker not recognized as a bare top-level fence.
            if not marker and re.search(r"(?:`{3,}|~{3,})", line):
                raise IntakeError("container-prefixed Markdown fence requires clarification")
            if marker:
                if marker.group("mark")[0] == "`" and "`" in marker.group("suffix"):
                    raise IntakeError("backtick fence info string requires clarification")
                if in_section:
                    raise IntakeError("fenced examples inside acceptance criteria require clarification")
                container_paragraph = False
                list_context = False
                fence = (marker.group("mark")[0], len(marker.group("mark")))
                continue
        line, html_pre, html_comment = _visible_html_line(
            line, html_pre, html_comment, in_section)
        if not line.strip():
            continue
        # Compute bullet continuation BEFORE interpreting acceptance-shaped
        # headings. Otherwise an indented literal "Acceptance:" continuation
        # resets the section and silently drops required contract text.
        leading = len(line) - len(line.lstrip(" \t"))
        # GFM permits indented ATX headings inside list items. Parsing such
        # nested structure with the flat acceptance grammar can silently
        # discard requirements; require clarification instead.
        atx_heading = ATX_HEADING.match(line)
        indented_after_bullet = in_section and last_bullet is not None and leading > 0
        continuation = indented_after_bullet and not blank_before
        if indented_after_bullet and atx_heading:
            raise IntakeError("nested Markdown heading requires clarification")
        if not in_section and LIST_CONTAINER.match(line):
            list_context = True
            container_paragraph = True
        elif not in_section and re.match(r"^ {0,3}>", line):
            container_paragraph = True
        elif atx_heading and not leading:
            container_paragraph = False
            list_context = False
        elif not leading and not container_paragraph:
            list_context = False
        acceptance_heading = HEADING.fullmatch(line)
        plain_label = PLAIN_LABEL.fullmatch(line)
        if (in_section and last_bullet is not None and not blank_before
                and not atx_heading and not continuation and (acceptance_heading or plain_label)):
            raise IntakeError("plain section labels after criteria require a blank line")
        if acceptance_heading and not continuation:
            # Indented acceptance headers can be text inside an enclosing
            # Markdown list, not a live top-level work-order section.
            # Supporting them requires a container-aware Markdown parser.
            if leading:
                raise IntakeError("indented acceptance heading requires clarification")
            if container_paragraph:
                raise IntakeError("possible lazy Markdown container acceptance heading requires clarification")
            last_bullet = None
            list_context = False
            in_section = True
            continue
        if not in_section:
            continue
        if THEMATIC_BREAK.fullmatch(line):
            raise IntakeError("thematic break in acceptance criteria requires clarification")
        # An indented title-like line may be a continuation of a bullet.
        # Do not silently terminate the section and drop later criteria.
        if (atx_heading and not leading) or plain_label:
            last_bullet = None
            in_section = False
            continue
        match = BULLET.match(line)
        if match:
            # A nested GFM list item is not a new top-level acceptance item.
            # Flattening nested requirements without their container semantics
            # can change the contract; reject this unsupported structure.
            if leading >= 2:
                raise IntakeError("nested acceptance bullet requires clarification")
            value = match.group(1).strip()
            if not value or len(value) > 1000:
                raise IntakeError("acceptance criterion must have 1-1000 characters")
            result.append(value)
            last_bullet = len(result) - 1
        else:
            # Markdown's indented continuation belongs to the preceding bullet.
            if continuation:
                combined = result[last_bullet] + " " + line.strip()
                if len(combined) > 1000:
                    raise IntakeError("acceptance criterion exceeds 1000 characters")
                result[last_bullet] = combined
            else:
                raise IntakeError("unrecognized acceptance prose; use a bullet or heading")
    if len(result) > 32 or len(set(result)) != len(result):
        raise IntakeError("duplicate or excessive acceptance criteria")
    return result


def compile_request(*, repository: str, base_sha: str, title: str, body: str,
                    source_kind: str = "chat", source_ref: str = "manual") -> dict:
    """Compile only explicit requirements. Return blocked drafts for missing tests.

    Source strings are retained exactly and bound to the queue identity by SHA-256.
    This is deterministic extraction, NOT a language model's semantic analysis.
    """
    if not isinstance(repository, str) or not REPO.fullmatch(repository):
        raise IntakeError("invalid repository")
    if not isinstance(base_sha, str) or not SHA.fullmatch(base_sha):
        raise IntakeError("base_sha must be a full lowercase Git commit SHA")
    if source_kind not in {"chat", "github_issue", "api"}:
        raise IntakeError("invalid source kind")
    title = _ensure_text(title, "title")
    body = _ensure_text(body, "body")
    source_ref = _ensure_text(source_ref, "source reference")
    if len(title) > 500 or len(source_ref) > 500:
        raise IntakeError("title or reference exceeds limit")
    original = {"kind": source_kind, "ref": source_ref, "title": title, "body": body}
    source_hash = digest(original)
    # The queue is shared by repositories and versions: avoid accidental ID collisions.
    work_identity = digest({"source_sha256": source_hash, "repository": repository.casefold(),
                            "base_sha": base_sha})
    order_id = f"intake-{work_identity[:24]}"
    acceptance = _criteria(body)
    if title.strip().endswith("?"):
        # Questions are not implementation authorizations.
        acceptance = []
    order = None
    if acceptance:
        order = {"schema": "far-software-factory/work-order/1", "id": order_id,
                 "repository": repository.casefold(), "base_sha": base_sha,
                 "tasks": [{"id": "implementation", "objective": title.strip(),
                            "acceptance": acceptance, "depends_on": []}]}
        validate_order(order)
    draft = {"schema": INTAKE_SCHEMA, "source": original, "source_sha256": source_hash,
             "repository": repository, "base_sha": base_sha,
             "status": "ready_for_manual_submission" if order else "needs_clarification",
             "questions": [] if order else ["Provide observable, testable items under an 'Acceptance criteria:' heading."],
             "order": order, "authority": "ADVISORY_ONLY",
             "compiler": "deterministic-explicit-criteria-v1"}
    draft["fingerprint"] = digest(draft)
    return draft


def verify_draft(draft: object) -> dict:
    """Regenerate from preserved source, detecting accidental draft edits.

    Fingerprints provide integrity checks, NOT authentication or an approval.
    """
    if not isinstance(draft, dict) or set(draft) != {"schema", "source", "source_sha256", "repository", "base_sha",
                                                    "status", "questions", "order", "authority", "compiler", "fingerprint"}:
        raise IntakeError("invalid intake draft fields")
    if draft["schema"] != INTAKE_SCHEMA or not isinstance(draft["source"], dict):
        raise IntakeError("unsupported intake draft")
    src = draft["source"]
    if set(src) != {"kind", "ref", "title", "body"}:
        raise IntakeError("invalid source fields")
    expected = compile_request(repository=draft["repository"], base_sha=draft["base_sha"],
                               title=src["title"], body=src["body"],
                               source_kind=src["kind"], source_ref=src["ref"])
    if expected != draft:
        raise IntakeError("intake draft differs from deterministic source compilation")
    return draft


def _issue_from_payload(payload: object, repository: str, issue_number: int) -> tuple[str, str]:
    if not isinstance(payload, dict):
        raise IntakeError("invalid GitHub issue response")
    number = payload.get("number")
    if type(number) is not int or number != issue_number:
        raise IntakeError("GitHub issue number mismatch")
    if "pull_request" in payload or payload.get("state") != "open":
        raise IntakeError("source must be an open GitHub issue, not a PR")
    repo_url = payload.get("repository_url")
    if not isinstance(repo_url, str) or repo_url.casefold() != f"https://api.github.com/repos/{repository}".casefold():
        raise IntakeError("GitHub issue repository mismatch")
    title = _ensure_text(payload.get("title"), "issue title")
    body = _ensure_text(payload.get("body"), "issue body")
    return title, body


def fetch_issue(repository: str, issue_number: int, *, token: str | None = None,
                fetcher=None) -> tuple[str, str]:
    """GET one fixed-host GitHub API issue. No arbitrary URL, redirects, or writes.

    The optional fetcher injects a test transport; the default uses HTTPS.
    """
    if not isinstance(repository, str) or not REPO.fullmatch(repository):
        raise IntakeError("invalid repository")
    if type(issue_number) is not int or not 1 <= issue_number <= 1_000_000_000:
        raise IntakeError("invalid issue number")
    url = f"https://api.github.com/repos/{repository}/issues/{issue_number}"
    if fetcher is None:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "far-factory-intake-v1",
                   "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.build_opener(_NoRedirect).open(req, timeout=12) as response:
                if response.geturl() != url:  # prohibit redirected credentials / source swaps
                    raise IntakeError("redirected issue source is not trusted")
                raw = response.read(MAX_ISSUE_BYTES + 1)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            raise IntakeError(f"GitHub issue retrieval failed: {type(exc).__name__}") from exc
    else:
        raw = fetcher(url)
    if not isinstance(raw, bytes) or len(raw) > MAX_ISSUE_BYTES:
        raise IntakeError("issue response is not a bounded byte string")
    try:
        payload = _strict_json(raw.decode("utf-8", "strict"))
    except UnicodeError as exc:
        raise IntakeError("invalid issue response encoding") from exc
    return _issue_from_payload(payload, repository, issue_number)


def submit_draft(draft: object, db_path: str | Path) -> dict:
    validated = verify_draft(draft)
    if validated["status"] != "ready_for_manual_submission":
        raise IntakeError("draft requires clarification; queue unchanged")
    # No network actions, worker invocation, or permission inference.
    factory = Factory(db_path)
    try:
        receipt = factory.submit(validated["order"])
    finally:
        factory.db.close()
    return {"queue": receipt, "source_sha256": validated["source_sha256"],
            "draft_fingerprint": validated["fingerprint"], "authority": "ADVISORY_ONLY"}


def _aliases(path: Path, protected: Path) -> bool:
    if path.resolve() == protected.resolve():
        return True
    try:
        return path.samefile(protected)
    except FileNotFoundError:
        return False


def _write_json(path: Path, value: dict, *, ensure_ascii: bool = True) -> None:
    # Replace the destination entry without truncating any existing inode.
    # This also protects existing hardlinks if they appear after alias checks.
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False,
        ) as stream:
            temp_path = Path(stream.name)
            json.dump(value, stream, sort_keys=True, indent=2, ensure_ascii=ensure_ascii)
            stream.write("\n")
        temp_path.replace(path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("draft-text", "draft-issue"):
        p = commands.add_parser(name)
        p.add_argument("--repo", required=True)
        p.add_argument("--base-sha", required=True)
        p.add_argument("--output", required=True)
        if name == "draft-text":
            p.add_argument("--text-file", required=True)
            p.add_argument("--source-ref", default="manual")
        else:
            p.add_argument("--issue", type=int, required=True)
    p = commands.add_parser("submit")
    p.add_argument("--draft-file", required=True)
    p.add_argument("--db", required=True)
    p.add_argument("--receipt-file")
    args = parser.parse_args(argv)
    try:
        if args.command == "draft-text":
            output = Path(args.output).resolve()
            if _aliases(output, Path(args.text_file)):
                raise IntakeError("draft output must not overwrite original source")
            text = Path(args.text_file).read_bytes().decode("utf-8", "strict")
            lines = text.splitlines()
            title = next((line.strip() for line in lines if line.strip()), "")
            if not title:
                raise IntakeError("request file must contain a nonempty title")
            draft = compile_request(repository=args.repo, base_sha=args.base_sha,
                                    title=title, body=text, source_kind="chat", source_ref=args.source_ref)
        elif args.command == "draft-issue":
            output = Path(args.output).resolve()
            title, body = fetch_issue(args.repo, args.issue, token=os.getenv("GITHUB_TOKEN"))
            draft = compile_request(repository=args.repo, base_sha=args.base_sha, title=title,
                                    body=body, source_kind="github_issue",
                                    source_ref=f"{args.repo}#{args.issue}")
        else:
            db_file = Path(args.db).resolve()
            draft_file = Path(args.draft_file).resolve()
            related_db_files = (
                db_file, *(Path(str(db_file) + suffix) for suffix in ("-wal", "-shm", "-journal")),
            )
            if any(_aliases(draft_file, path) for path in related_db_files):
                raise IntakeError("draft must not be the queue database or its sidecars")
            if args.receipt_file:
                receipt_file = Path(args.receipt_file).resolve()
                if any(_aliases(receipt_file, path) for path in (draft_file, *related_db_files)):
                    raise IntakeError("receipt must not overwrite draft or queue database/sidecars")
            draft = _strict_json(draft_file.read_text(encoding="utf-8"))
            receipt = submit_draft(draft, db_file)
            if args.receipt_file:
                _write_json(receipt_file, receipt)
            print(json.dumps(receipt, sort_keys=True, indent=2))
            return 0
        _write_json(output, draft, ensure_ascii=False)
        print(json.dumps({"status": draft["status"], "output": args.output,
                          "source_sha256": draft["source_sha256"], "questions": draft["questions"]}, indent=2))
        return 0 if draft["order"] else 3
    except (IntakeError, FactoryError, OSError, ValueError, UnicodeError) as exc:
        print(f"software-factory-intake: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
