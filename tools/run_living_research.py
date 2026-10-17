#!/usr/bin/env python3
"""Project FAR unattended living-research discovery engine.

This program is Research-only infrastructure. It discovers, deduplicates, routes,
and records candidate literature and historical/philosophical sources. It never
promotes evidence, changes a canonical claim, executes EFR, or creates external
independence. Any candidate that could affect a FAR claim is only routed into the
governed review/reopening path.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

CONFIG_PATH = Path("research/living/config-v1.0.json")
STATE_PATH = Path("research/living/state-v1.0.json")
RQ_PATH = Path("research/registry/research-questions-v1.0.json")
THREAT_PATH = Path("research/registry/epistemic-threats-v1.0.json")
CLAIM_PATH = Path("theory/terminal/project-far-core-theory-v1.1.json")
CANDIDATE_DIR = Path("research/living/inbox/candidates")
RUN_DIR = Path("research/living/runs")
DASHBOARD_PATH = Path("docs/research/living-research-status.md")

AUTHORITY_BOUNDARY = (
    "Research candidate only. Discovery or triage does not establish support, dispute, "
    "novelty, priority, external validity, utility, independence, theorem status, EFR result, "
    "or any other Project FAR claim/evidence disposition."
)
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_CLAIM_RE = re.compile(r"FAR-CORE-(\d{3})")


class LivingResearchError(RuntimeError):
    """Configuration, source, or invariant failure; never a negative research result."""


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise LivingResearchError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise LivingResearchError(f"timestamp must include timezone: {value}")
    return parsed.astimezone(timezone.utc)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def clean_text(value: Any, limit: int = 5000) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = " ".join(str(part) for part in value if part is not None)
    text = html.unescape(_TAG_RE.sub(" ", str(value)))
    return _SPACE_RE.sub(" ", text).strip()[:limit]


def claim_ids_from_question(question: dict[str, Any], all_claim_ids: list[str]) -> list[str]:
    """Extract exact explicit FAR-CORE references/ranges from governed RQ text and dependencies."""
    corpus = " ".join(
        clean_text(question.get(key))
        for key in ("exact_question", "governing_scope", "dependencies", "falsifier_resolution_criterion")
    )
    found = {f"FAR-CORE-{m}" for m in _CLAIM_RE.findall(corpus)}
    range_match = re.search(r"FAR-CORE-(\d{3})\s+(?:through|to|–|-)\s+FAR-CORE-(\d{3})", corpus)
    if range_match:
        lo, hi = map(int, range_match.groups())
        found.update(f"FAR-CORE-{n:03d}" for n in range(lo, hi + 1))
    return [claim_id for claim_id in all_claim_ids if claim_id in found]


def question_index(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    questions = registry.get("questions")
    if not isinstance(questions, list):
        raise LivingResearchError("research-question registry missing questions array")
    result: dict[str, dict[str, Any]] = {}
    for question in questions:
        if not isinstance(question, dict) or not isinstance(question.get("id"), str):
            raise LivingResearchError("malformed research-question registry entry")
        if question["id"] in result:
            raise LivingResearchError(f"duplicate research question: {question['id']}")
        result[question["id"]] = question
    return result


def threat_ids(registry: dict[str, Any]) -> set[str]:
    threats = registry.get("threats")
    if not isinstance(threats, list):
        raise LivingResearchError("epistemic-threat registry missing threats array")
    result = set()
    for threat in threats:
        if not isinstance(threat, dict) or not isinstance(threat.get("id"), str):
            raise LivingResearchError("malformed epistemic-threat registry entry")
        result.add(threat["id"])
    return result


def claim_index(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    claims = ledger.get("claims")
    if not isinstance(claims, list):
        raise LivingResearchError("core claim ledger missing claims array")
    result: dict[str, dict[str, Any]] = {}
    for claim in claims:
        if not isinstance(claim, dict) or not isinstance(claim.get("id"), str):
            raise LivingResearchError("malformed core claim ledger entry")
        result[claim["id"]] = claim
    expected = [f"FAR-CORE-{n:03d}" for n in range(1, 15)]
    if list(result) != expected:
        raise LivingResearchError("living engine requires exact FAR-CORE-001 through FAR-CORE-014 ledger")
    return result


def validate_bindings(
    config: dict[str, Any],
    rq_registry: dict[str, Any],
    threat_registry: dict[str, Any],
    claim_ledger: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    if config.get("program_id") != "FAR-LIVING-RESEARCH-001":
        raise LivingResearchError("unexpected living-research program_id")
    if config.get("authority_boundary") != AUTHORITY_BOUNDARY:
        raise LivingResearchError("authority boundary drift")
    questions = question_index(rq_registry)
    guards = config.get("threat_guards")
    if not isinstance(guards, list) or not guards:
        raise LivingResearchError("threat_guards must be nonempty")
    missing = sorted(set(guards) - threat_ids(threat_registry))
    if missing:
        raise LivingResearchError(f"unknown threat guard(s): {', '.join(missing)}")

    # Every source is called with `source["endpoint"]` and `source["user_agent"]`. A key
    # missing from the configuration used to surface as a per-query KeyError that silently
    # killed the whole lane while the run still reported partial success: run
    # 34227532304 lost both the OpenAlex and Open Library lanes that way. Fail closed here
    # instead, before any request is issued.
    sources = config.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise LivingResearchError("sources must be a nonempty object")
    for name in ("crossref", "openalex", "openlibrary"):
        source = sources.get(name)
        if not isinstance(source, dict):
            raise LivingResearchError(f"source {name!r} must be an object")
        for field in ("endpoint", "user_agent"):
            value = source.get(field)
            if not isinstance(value, str) or not value.strip():
                raise LivingResearchError(f"source {name!r} missing required {field!r}")

    claim_ids = list(claim_index(claim_ledger).keys()) if claim_ledger else []
    targets = config.get("targets")
    if not isinstance(targets, list) or not targets:
        raise LivingResearchError("targets must be nonempty")
    seen: set[str] = set()
    for target in targets:
        if not isinstance(target, dict):
            raise LivingResearchError("target must be an object")
        target_id = target.get("target_id")
        if not isinstance(target_id, str) or target_id not in questions:
            raise LivingResearchError(f"unknown target_id: {target_id!r}")
        if target_id in seen:
            raise LivingResearchError(f"duplicate target_id: {target_id}")
        seen.add(target_id)
        allowed = target.get("allowed_dispositions")
        if not isinstance(allowed, list) or not allowed:
            raise LivingResearchError(f"{target_id}: allowed_dispositions required")
        disposition = questions[target_id].get("current_disposition")
        if disposition not in allowed:
            raise LivingResearchError(
                f"{target_id}: current disposition {disposition!r} is not watched; update config deliberately"
            )
        for field in ("queries", "signal_terms"):
            values = target.get(field)
            if not isinstance(values, list) or not values or not all(isinstance(x, str) and x.strip() for x in values):
                raise LivingResearchError(f"{target_id}: {field} must be nonempty strings")
        if not isinstance(target.get("candidate_relation"), str):
            raise LivingResearchError(f"{target_id}: candidate_relation required")
        if claim_ids:
            target["_derived_claim_ids"] = claim_ids_from_question(questions[target_id], claim_ids)

    lenses = config.get("lenses")
    if not isinstance(lenses, dict) or not lenses:
        raise LivingResearchError("lenses must be a nonempty object")
    for lens_id, lens in lenses.items():
        if not isinstance(lens, dict):
            raise LivingResearchError(f"lens {lens_id}: must be object")
        if not isinstance(lens.get("bridge_terms"), list):
            raise LivingResearchError(f"lens {lens_id}: bridge_terms must be array")
        if int(lens.get("min_bridge_hits", 0)) < 0:
            raise LivingResearchError(f"lens {lens_id}: invalid min_bridge_hits")

    backfill = config.get("historical_backfill")
    if not isinstance(backfill, dict):
        raise LivingResearchError("historical_backfill missing")
    queries = backfill.get("queries")
    if not isinstance(queries, list) or not queries:
        raise LivingResearchError("historical_backfill.queries must be nonempty")
    for item in queries:
        if not isinstance(item, dict):
            raise LivingResearchError("historical query must be object")
        if item.get("lens") not in lenses:
            raise LivingResearchError(f"historical query {item.get('id')}: unknown lens")
        tids = item.get("target_ids")
        if not isinstance(tids, list) or not tids or any(t not in questions for t in tids):
            raise LivingResearchError(f"historical query {item.get('id')}: invalid target_ids")
    return questions


def default_transport(url: str, headers: dict[str, str], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise LivingResearchError("source response was not a JSON object")
    return payload


def request_json(
    url: str,
    *,
    user_agent: str,
    timeout: int,
    retries: int,
    transport: Callable[[str, dict[str, str], int], dict[str, Any]] = default_transport,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    headers = {"Accept": "application/json", "User-Agent": user_agent}
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return transport(url, headers, timeout)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, LivingResearchError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            sleep_fn(min(2**attempt, 8))
    assert last_error is not None
    raise last_error


def crossref_query(
    query: str,
    source: dict[str, Any],
    *,
    index_window: tuple[str, str] | None = None,
    publication_window: tuple[int, int] | None = None,
    transport: Callable[[str, dict[str, str], int], dict[str, Any]] = default_transport,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    endpoint = source["endpoint"]
    params: dict[str, str] = {
        "query.bibliographic": query,
        "rows": str(int(source.get("rows_per_query", 8))),
    }
    if index_window:
        # Rank by relevance inside the index-date window. Sorting by index date instead
        # would return the most recently deposited members of a large fuzzy match set,
        # which is close to arbitrary with respect to the governed question.
        params["filter"] = f"from-index-date:{index_window[0]},until-index-date:{index_window[1]}"
        params["sort"] = "relevance"
    elif publication_window:
        params["filter"] = f"from-pub-date:{publication_window[0]},until-pub-date:{publication_window[1]}"
        params["sort"] = "relevance"
    else:
        raise LivingResearchError("Crossref query requires an index or publication window")
    mailto = os.environ.get("CROSSREF_MAILTO", "").strip()
    if mailto:
        params["mailto"] = mailto
    url = endpoint + "?" + urllib.parse.urlencode(params)
    payload = request_json(
        url,
        user_agent=source["user_agent"],
        timeout=int(source.get("timeout_seconds", 30)),
        retries=int(source.get("max_retries", 3)),
        transport=transport,
        sleep_fn=sleep_fn,
    )
    message = payload.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("items"), list):
        raise LivingResearchError("Crossref response missing message.items")
    items = [item for item in message["items"] if isinstance(item, dict)]
    return items, {"provider": "Crossref", "parameters": params, "rows_returned": len(items)}


def openalex_query(
    query: str,
    source: dict[str, Any],
    start_year: int,
    end_year: int,
    *,
    transport: Callable[[str, dict[str, str], int], dict[str, Any]] = default_transport,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params: dict[str, str] = {
        "search": query,
        "filter": f"from_publication_date:{start_year}-01-01,to_publication_date:{end_year}-12-31",
        "per_page": str(int(source.get("rows_per_query", 8))),
        "sort": "relevance_score:desc",
        "select": "id,doi,display_name,publication_date,type,cited_by_count,authorships,keywords,topics,primary_location",
    }
    key = os.environ.get("OPENALEX_API_KEY", "").strip()
    if key:
        params["api_key"] = key
    mailto = os.environ.get("OPENALEX_MAILTO", "").strip()
    if mailto:
        params["mailto"] = mailto
    url = source["endpoint"] + "?" + urllib.parse.urlencode(params)
    payload = request_json(
        url,
        user_agent=source["user_agent"],
        timeout=int(source.get("timeout_seconds", 30)),
        retries=int(source.get("max_retries", 2)),
        transport=transport,
        sleep_fn=sleep_fn,
    )
    if not isinstance(payload.get("results"), list):
        raise LivingResearchError("OpenAlex response missing results")
    items = [item for item in payload["results"] if isinstance(item, dict)]
    return items, {"provider": "OpenAlex", "parameters": {k: ("<set>" if k == "api_key" else v) for k, v in params.items()}, "rows_returned": len(items)}


def openlibrary_query(
    query: str,
    source: dict[str, Any],
    page: int,
    *,
    transport: Callable[[str, dict[str, str], int], dict[str, Any]] = default_transport,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params = {
        "q": query,
        "fields": "key,title,author_name,first_publish_year,subject,edition_count,isbn,lcc,ddc",
        "sort": "old",
        "limit": str(int(source.get("rows_per_query", 5))),
        "page": str(max(1, page)),
    }
    url = source["endpoint"] + "?" + urllib.parse.urlencode(params)
    payload = request_json(
        url,
        user_agent=source["user_agent"],
        timeout=int(source.get("timeout_seconds", 30)),
        retries=int(source.get("max_retries", 2)),
        transport=transport,
        sleep_fn=sleep_fn,
    )
    docs = payload.get("docs")
    if not isinstance(docs, list):
        raise LivingResearchError("Open Library response missing docs")
    items = [item for item in docs if isinstance(item, dict)]
    return items, {"provider": "Open Library", "parameters": params, "rows_returned": len(items)}


def crossref_text(item: dict[str, Any]) -> str:
    fields = [item.get(k) for k in ("title", "subtitle", "abstract", "subject", "container-title", "publisher")]
    return " ".join(clean_text(x).lower() for x in fields if x)


def openalex_text(item: dict[str, Any]) -> str:
    fields: list[Any] = [item.get("display_name"), item.get("type")]
    for key in ("keywords", "topics"):
        values = item.get(key)
        if isinstance(values, list):
            fields.extend(v.get("display_name") for v in values if isinstance(v, dict))
    return " ".join(clean_text(x).lower() for x in fields if x)


def openlibrary_text(item: dict[str, Any]) -> str:
    return " ".join(clean_text(item.get(k)).lower() for k in ("title", "author_name", "subject", "lcc", "ddc") if item.get(k))


def hits(text: str, terms: Iterable[str]) -> list[str]:
    """Recall-oriented substring match, used for signal and bridge terms."""
    return sorted({term for term in terms if clean_text(term, 200).lower() in text}, key=str.lower)


def boundary_hits(text: str, terms: Iterable[str]) -> list[str]:
    """Precision-oriented whole-word match, used for attention terms.

    Attention terms route candidates toward human review, so a substring match is the
    wrong trade-off: bare `in` lets `correction` fire on `corrections`, `failure` on
    `failures`, and any term on an unrelated journal or publisher name. Signal terms
    keep substring matching because there the cost of a miss outweighs the cost of noise.
    """
    found: set[str] = set()
    for term in terms:
        normalized = clean_text(term, 200).lower()
        if normalized and re.search(rf"(?<!\w){re.escape(normalized)}(?!\w)", text):
            found.add(term)
    return sorted(found, key=str.lower)


def normalize_doi(value: Any) -> str | None:
    doi = clean_text(value, 500).lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    return doi or None


FALLBACK_IDENTITY_MARKER = "-fallback:"


def is_fallback_identity(source_key: str) -> bool:
    """True when the identity is a metadata hash rather than a resolvable provider id."""
    return FALLBACK_IDENTITY_MARKER in source_key


def source_identity(provider: str, item: dict[str, Any]) -> str:
    if provider == "Crossref":
        doi = normalize_doi(item.get("DOI"))
        if doi:
            return f"doi:{doi}"
        stable = {
            "title": clean_text(item.get("title")).lower(),
            "publisher": clean_text(item.get("publisher")).lower(),
            "type": clean_text(item.get("type")).lower(),
            "published": item.get("published") or item.get("issued") or {},
        }
    elif provider == "OpenAlex":
        doi = normalize_doi(item.get("doi"))
        if doi:
            return f"doi:{doi}"
        ident = clean_text(item.get("id"), 500)
        if ident:
            return f"openalex:{ident.rsplit('/', 1)[-1].lower()}"
        stable = {"title": clean_text(item.get("display_name")).lower(), "date": item.get("publication_date")}
    elif provider == "Open Library":
        key = clean_text(item.get("key"), 500)
        if key:
            return f"openlibrary:{key.lower()}"
        stable = {"title": clean_text(item.get("title")).lower(), "year": item.get("first_publish_year")}
    else:
        raise LivingResearchError(f"unknown provider: {provider}")
    encoded = json.dumps(stable, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"{provider.lower().replace(' ', '-')}-fallback:{sha256_text(encoded)}"


def candidate_id(source_key: str) -> str:
    return "FAR-LIT-" + sha256_text(source_key)[:16].upper()


def crossref_source(item: dict[str, Any]) -> dict[str, Any]:
    title = clean_text(item.get("title"))
    authors = []
    if isinstance(item.get("author"), list):
        for author in item["author"][:25]:
            if isinstance(author, dict):
                name = " ".join(x for x in (clean_text(author.get("given"), 200), clean_text(author.get("family"), 200)) if x)
                if name:
                    authors.append(name)
    date = None
    for key in ("published-online", "published-print", "published", "issued"):
        raw = item.get(key)
        if isinstance(raw, dict) and isinstance(raw.get("date-parts"), list) and raw["date-parts"]:
            parts = raw["date-parts"][0]
            if parts:
                try:
                    y = int(parts[0]); m = int(parts[1]) if len(parts) > 1 else 1; d = int(parts[2]) if len(parts) > 2 else 1
                    date = f"{y:04d}-{m:02d}-{d:02d}"
                    break
                except (TypeError, ValueError):
                    pass
    return {
        "provider": "Crossref",
        "doi": normalize_doi(item.get("DOI")),
        "provider_id": normalize_doi(item.get("DOI")),
        "url": clean_text(item.get("URL"), 2000) or None,
        "title": title,
        "authors": authors,
        "published_date": date,
        "work_type": clean_text(item.get("type"), 100) or None,
        "container": clean_text(item.get("container-title"), 500) or None,
        "publisher": clean_text(item.get("publisher"), 500) or None,
    }


def openalex_source(item: dict[str, Any]) -> dict[str, Any]:
    authors = []
    for authorship in item.get("authorships") or []:
        if isinstance(authorship, dict) and isinstance(authorship.get("author"), dict):
            name = clean_text(authorship["author"].get("display_name"), 300)
            if name:
                authors.append(name)
    location = item.get("primary_location") if isinstance(item.get("primary_location"), dict) else {}
    return {
        "provider": "OpenAlex",
        "doi": normalize_doi(item.get("doi")),
        "provider_id": clean_text(item.get("id"), 500) or None,
        "url": clean_text(location.get("landing_page_url"), 2000) or clean_text(item.get("id"), 500) or None,
        "title": clean_text(item.get("display_name")),
        "authors": authors[:25],
        "published_date": clean_text(item.get("publication_date"), 40) or None,
        "work_type": clean_text(item.get("type"), 100) or None,
        "cited_by_count": item.get("cited_by_count") if isinstance(item.get("cited_by_count"), int) else None,
    }


def openlibrary_source(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": "Open Library",
        "doi": None,
        "provider_id": clean_text(item.get("key"), 500) or None,
        "url": ("https://openlibrary.org" + clean_text(item.get("key"), 500)) if item.get("key") else None,
        "title": clean_text(item.get("title")),
        "authors": [clean_text(x, 300) for x in (item.get("author_name") or [])[:25]],
        "published_date": f"{int(item['first_publish_year']):04d}-01-01" if isinstance(item.get("first_publish_year"), int) else None,
        "work_type": "book",
        "edition_count": item.get("edition_count") if isinstance(item.get("edition_count"), int) else None,
    }


def load_state(root: Path, config: dict[str, Any], now: datetime) -> dict[str, Any]:
    path = root / STATE_PATH
    if path.exists():
        state = read_json(path)
    else:
        state = {}
    cursor = state.get("incremental_cursor_utc") or state.get("source_cursor_utc")
    current_year = now.year
    default = {
        "schema_version": "1.0",
        "program_id": "FAR-LIVING-RESEARCH-001",
        "incremental_cursor_utc": cursor,
        "historical": {
            "query_index": 0,
            "window_end_year": current_year,
            "complete": False,
            "completed_utc": None,
        },
        "openlibrary": {"query_index": 0, "page": 1},
        "run_count": int(state.get("run_count", 0)),
        "last_run_id": state.get("last_run_id"),
        "last_run_status": state.get("last_run_status", "NEVER_RUN"),
        "total_unique_candidates": int(state.get("total_unique_candidates", 0)),
        "updated_utc": state.get("updated_utc"),
    }
    if isinstance(state.get("historical"), dict):
        default["historical"].update(state["historical"])
    if isinstance(state.get("openlibrary"), dict):
        default["openlibrary"].update(state["openlibrary"])
    return default


def candidate_path(root: Path, cid: str) -> Path:
    if not re.fullmatch(r"FAR-LIT-[0-9A-F]{16}", cid):
        raise LivingResearchError(f"unsafe candidate id: {cid}")
    return root / CANDIDATE_DIR / f"{cid}.json"


def process_item(
    *,
    root: Path,
    provider: str,
    item: dict[str, Any],
    binding: dict[str, Any],
    signal_terms: list[str],
    min_signal_hits: int,
    lens: dict[str, Any] | None,
    attention_terms: list[str],
    all_claim_ids: list[str],
    questions: dict[str, dict[str, Any]],
    now_iso: str,
    accept_allowed: bool = True,
) -> tuple[dict[str, Any], bool]:
    text_fn = {"Crossref": crossref_text, "OpenAlex": openalex_text, "Open Library": openlibrary_text}[provider]
    text = text_fn(item)
    signal = hits(text, signal_terms)
    bridge = hits(text, (lens or {}).get("bridge_terms", []))
    required_bridge = int((lens or {}).get("min_bridge_hits", 0))
    eligible = len(signal) >= min_signal_hits and len(bridge) >= required_bridge
    accepted = eligible and accept_allowed
    reason = "ACCEPTED_SIGNAL_MATCH" if accepted else (
        "QUERY_ACCEPTANCE_CAP" if eligible and not accept_allowed else
        "INSUFFICIENT_MATHEMATICAL_BRIDGE" if len(signal) >= min_signal_hits and len(bridge) < required_bridge
        else "NO_SIGNAL_TERM"
    )
    source_key = source_identity(provider, item)
    cid = candidate_id(source_key)
    result = {
        "provider": provider,
        "source_key": source_key,
        "candidate_id": cid,
        "decision": "ACCEPT" if accepted else "REJECT",
        "reason": reason,
        "signal_hits": signal,
        "bridge_hits": bridge,
    }
    observed_title = clean_text(item.get("title") if provider != "OpenAlex" else item.get("display_name"))
    if not accepted:
        # Rejected results keep their exact rejection reason and their identity. Where that
        # identity resolves on its own (a DOI, an OpenAlex or Open Library id) the title is
        # dropped: titles dominate report size and every run re-reports the same rejected
        # window. Where `source_identity` fell back to a metadata hash there is nothing to
        # resolve, so the title is kept and the rejection stays reconstructible.
        if is_fallback_identity(source_key):
            result["title"] = observed_title
        return result, False
    result["title"] = observed_title

    source = {
        "Crossref": crossref_source,
        "OpenAlex": openalex_source,
        "Open Library": openlibrary_source,
    }[provider](item)
    path = candidate_path(root, cid)
    was_new = not path.exists()
    if path.exists():
        record = read_json(path)
    else:
        record = {
            "schema_version": "1.0",
            "record_type": "CANDIDATE_LITERATURE",
            "authority": "Research",
            "candidate_id": cid,
            "source_key": source_key,
            "authority_boundary": AUTHORITY_BOUNDARY,
            "sources": [],
            "discovery": {"first_seen_utc": now_iso, "last_seen_utc": now_iso, "query_bindings": []},
            "triage": {"status": "UNREVIEWED_CANDIDATE", "attention_terms": [], "lenses": []},
            "potential_claim_ids": [],
            "lifecycle": {
                "stage": "DISCOVERED",
                "may_change_claim_status": False,
                "may_establish_novelty": False,
                "may_execute_efr": False,
                "may_count_as_external_independence": False,
            },
        }

    sources = record.setdefault("sources", [])
    source_fingerprint = (source.get("provider"), source.get("provider_id"))
    existing = {(s.get("provider"), s.get("provider_id")) for s in sources if isinstance(s, dict)}
    if source_fingerprint not in existing:
        sources.append(source)
        sources.sort(key=lambda s: (s.get("provider") or "", s.get("provider_id") or ""))

    qbinds = record["discovery"].setdefault("query_bindings", [])
    bind_key = (binding["target_id"], binding["query"], binding.get("historical_query_id"), provider)
    existing_binds = {
        (b.get("target_id"), b.get("query"), b.get("historical_query_id"), b.get("provider"))
        for b in qbinds if isinstance(b, dict)
    }
    if bind_key not in existing_binds:
        qbinds.append(binding)
        qbinds.sort(key=lambda b: (b.get("target_id") or "", b.get("query") or "", b.get("provider") or ""))
    record["discovery"]["last_seen_utc"] = now_iso

    # Attention terms are derived, not accumulated. Each provider's contribution is stored
    # on its own source entry and replaced whenever that provider is seen again, and the
    # triage list is recomputed as the union filtered to the currently configured terms.
    # Unioning into the persisted list instead would make a match permanent: a term dropped
    # from the configuration, or one matched by a superseded matcher, could never clear, and
    # the candidate would be published as high-attention forever.
    configured = set(attention_terms)
    for entry in sources:
        if isinstance(entry, dict) and (entry.get("provider"), entry.get("provider_id")) == source_fingerprint:
            entry["attention_terms"] = boundary_hits(text, attention_terms)
    record["triage"]["attention_terms"] = sorted(
        {
            term
            for entry in sources
            if isinstance(entry, dict)
            for term in entry.get("attention_terms", [])
            if term in configured
        },
        key=str.lower,
    )
    if binding.get("lens"):
        record["triage"]["lenses"] = sorted(set(record["triage"].get("lenses", [])) | {binding["lens"]})
    potential = set(record.get("potential_claim_ids", []))
    for target_id in binding.get("target_ids", [binding["target_id"]]):
        potential.update(claim_ids_from_question(questions[target_id], all_claim_ids))
    record["potential_claim_ids"] = [cid_ for cid_ in all_claim_ids if cid_ in potential]
    write_json(path, record)
    return result, was_new


def render_dashboard(root: Path, state: dict[str, Any], run: dict[str, Any]) -> None:
    candidates = sorted((root / CANDIDATE_DIR).glob("FAR-LIT-*.json"))
    high = 0
    philosophical = 0
    historical = 0
    for path in candidates:
        record = read_json(path)
        if record.get("triage", {}).get("attention_terms"):
            high += 1
        lenses = set(record.get("triage", {}).get("lenses", []))
        if lenses & {"philosophy_of_science", "formal_metaphysics", "history_of_logic", "historical_foundations"}:
            philosophical += 1
        if any(b.get("mode") == "historical_backfill" for b in record.get("discovery", {}).get("query_bindings", []) if isinstance(b, dict)):
            historical += 1
    hist = state["historical"]
    text = f"""# Living Research Status

Status: **Research infrastructure; never theory or evidence authority**

{AUTHORITY_BOUNDARY}

- Last run: `{state.get('last_run_id')}`
- Last status: `{state.get('last_run_status')}`
- Total unique candidates: **{len(candidates)}**
- High-attention metadata candidates: **{high}**
- Philosophical / metaphysical / historical-lens candidates: **{philosophical}**
- Historical-backfill candidates: **{historical}**
- Incremental cursor: `{state.get('incremental_cursor_utc')}`
- Historical backfill window end: `{hist.get('window_end_year')}`
- Historical backfill complete: `{hist.get('complete')}`
- Source failures in latest run: **{len(run.get('failures', []))}**

The watcher discovers and routes candidates. It does not adjudicate them, establish novelty,
change FAR-CORE status, execute EFR, or create independent evidence.
"""
    path = root / DASHBOARD_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(
    root: Path,
    *,
    now: datetime | None = None,
    crossref_transport: Callable[[str, dict[str, str], int], dict[str, Any]] = default_transport,
    openalex_transport: Callable[[str, dict[str, str], int], dict[str, Any]] = default_transport,
    openlibrary_transport: Callable[[str, dict[str, str], int], dict[str, Any]] = default_transport,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    now_iso = utc_iso(now)
    config = read_json(root / CONFIG_PATH)
    rq_registry = read_json(root / RQ_PATH)
    threat_registry = read_json(root / THREAT_PATH)
    claim_ledger = read_json(root / CLAIM_PATH)
    questions = validate_bindings(config, rq_registry, threat_registry, claim_ledger)
    claims = claim_index(claim_ledger)
    all_claim_ids = list(claims)
    state = load_state(root, config, now)

    run_id = now.strftime("%Y%m%dT%H%M%SZ") + "-" + os.environ.get("GITHUB_RUN_ID", "local")
    run_record: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": run_id,
        "authority": "Research",
        "authority_boundary": AUTHORITY_BOUNDARY,
        "started_utc": now_iso,
        "status": "RUNNING",
        "queries": [],
        "failures": [],
        "cursor_advanced": False,
        "historical_advanced": False,
    }
    source_cfg = config["sources"]
    crossref_cfg = source_cfg["crossref"]

    overlap_days = int(crossref_cfg.get("overlap_days", 2))
    lookback_days = int(crossref_cfg.get("initial_lookback_days", 14))
    cursor_raw = state.get("incremental_cursor_utc")
    start = parse_utc(cursor_raw) - timedelta(days=overlap_days) if cursor_raw else now - timedelta(days=lookback_days)
    # Crossref's index-date filters take a calendar date. Passing a full timestamp
    # (`2026-08-25T12:42:01Z`) makes every incremental request fail with HTTP 400, which
    # is what run 34227532304 recorded for all 24 incremental queries.
    index_window = (start.date().isoformat(), now.date().isoformat())

    for target in config["targets"]:
        target_id = target["target_id"]
        qsha = sha256_text(clean_text(questions[target_id].get("exact_question")))
        for query in target["queries"]:
            accepted_for_query = 0
            try:
                items, request = crossref_query(
                    query, crossref_cfg, index_window=index_window,
                    transport=crossref_transport, sleep_fn=sleep_fn
                )
            except Exception as exc:
                run_record["failures"].append({"provider": "Crossref", "mode": "incremental", "target_id": target_id, "query": query, "error": f"{type(exc).__name__}: {exc}"})
                continue
            qrec = {"provider": "Crossref", "mode": "incremental", "target_id": target_id, "query": query, "request": request, "results": []}
            for rank, item in enumerate(items, 1):
                binding = {
                    "provider": "Crossref",
                    "mode": "incremental",
                    "target_id": target_id,
                    "target_ids": [target_id],
                    "query": query,
                    "governed_question_sha256": qsha,
                    "candidate_relation": target["candidate_relation"],
                    "lens": "governed_question",
                    "seen_utc": now_iso,
                }
                outcome, _ = process_item(
                    root=root, provider="Crossref", item=item, binding=binding,
                    signal_terms=target["signal_terms"], min_signal_hits=int(target.get("min_signal_hits", 1)),
                    lens={"bridge_terms": [], "min_bridge_hits": 0},
                    attention_terms=config["attention_terms"], all_claim_ids=all_claim_ids,
                    questions=questions, now_iso=now_iso,
                    accept_allowed=accepted_for_query < int(target.get("max_candidates_per_query", 3)),
                )
                outcome["rank"] = rank
                if outcome["decision"] == "ACCEPT":
                    accepted_for_query += 1
                qrec["results"].append(outcome)
            run_record["queries"].append(qrec)

    hist_cfg = config["historical_backfill"]
    hist = state["historical"]
    if not hist.get("complete"):
        historical_queries = hist_cfg["queries"]
        qindex = int(hist.get("query_index", 0)) % len(historical_queries)
        hq = historical_queries[qindex]
        end_year = int(hist.get("window_end_year", now.year))
        width = int(hist_cfg.get("window_years", 10))
        min_year = int(hist_cfg.get("min_year", 1600))
        start_year = max(min_year, end_year - width + 1)
        lens = config["lenses"][hq["lens"]]
        for provider in ("Crossref", "OpenAlex"):
            try:
                if provider == "Crossref":
                    items, request = crossref_query(
                        hq["query"], crossref_cfg, publication_window=(start_year, end_year),
                        transport=crossref_transport, sleep_fn=sleep_fn
                    )
                else:
                    items, request = openalex_query(
                        hq["query"], source_cfg["openalex"], start_year, end_year,
                        transport=openalex_transport, sleep_fn=sleep_fn
                    )
            except Exception as exc:
                run_record["failures"].append({"provider": provider, "mode": "historical_backfill", "historical_query_id": hq["id"], "query": hq["query"], "window": [start_year, end_year], "error": f"{type(exc).__name__}: {exc}"})
                continue
            qrec = {"provider": provider, "mode": "historical_backfill", "historical_query_id": hq["id"], "query": hq["query"], "window": [start_year, end_year], "request": request, "results": []}
            for rank, item in enumerate(items, 1):
                target_id = hq["target_ids"][0]
                qsha = sha256_text(clean_text(questions[target_id].get("exact_question")))
                binding = {
                    "provider": provider,
                    "mode": "historical_backfill",
                    "target_id": target_id,
                    "target_ids": hq["target_ids"],
                    "query": hq["query"],
                    "historical_query_id": hq["id"],
                    "governed_question_sha256": qsha,
                    "candidate_relation": "HISTORICAL_OR_FOUNDATIONAL_CANDIDATE",
                    "lens": hq["lens"],
                    "publication_window": [start_year, end_year],
                    "seen_utc": now_iso,
                }
                outcome, _ = process_item(
                    root=root, provider=provider, item=item, binding=binding,
                    signal_terms=hq["signal_terms"], min_signal_hits=int(hq.get("min_signal_hits", 1)),
                    lens=lens, attention_terms=config["attention_terms"], all_claim_ids=all_claim_ids,
                    questions=questions, now_iso=now_iso,
                )
                outcome["rank"] = rank
                qrec["results"].append(outcome)
            run_record["queries"].append(qrec)

        slice_failed = any(
            f.get("mode") == "historical_backfill" and f.get("historical_query_id") == hq["id"]
            for f in run_record["failures"]
        )
        if not slice_failed:
            qindex += 1
            if qindex >= len(historical_queries):
                qindex = 0
                end_year = start_year - 1
                if end_year < min_year:
                    hist["complete"] = True
                    hist["completed_utc"] = now_iso
                    end_year = min_year
            hist["query_index"] = qindex
            hist["window_end_year"] = end_year
            run_record["historical_advanced"] = True

    ol_cfg = source_cfg.get("openlibrary", {})
    if ol_cfg.get("enabled", True) and state["run_count"] % int(ol_cfg.get("interval_runs", 4)) == 0:
        book_queries = hist_cfg.get("book_queries", [])
        if book_queries:
            ol_state = state["openlibrary"]
            qindex = int(ol_state.get("query_index", 0)) % len(book_queries)
            bq = book_queries[qindex]
            page = int(ol_state.get("page", 1))
            try:
                items, request = openlibrary_query(
                    bq["query"], ol_cfg, page, transport=openlibrary_transport, sleep_fn=sleep_fn
                )
                qrec = {"provider": "Open Library", "mode": "historical_book_backfill", "historical_query_id": bq["id"], "query": bq["query"], "page": page, "request": request, "results": []}
                lens = config["lenses"][bq["lens"]]
                for rank, item in enumerate(items, 1):
                    target_id = bq["target_ids"][0]
                    binding = {
                        "provider": "Open Library",
                        "mode": "historical_backfill",
                        "target_id": target_id,
                        "target_ids": bq["target_ids"],
                        "query": bq["query"],
                        "historical_query_id": bq["id"],
                        "governed_question_sha256": sha256_text(clean_text(questions[target_id].get("exact_question"))),
                        "candidate_relation": "HISTORICAL_PRIMARY_OR_BOOK_CANDIDATE",
                        "lens": bq["lens"],
                        "seen_utc": now_iso,
                    }
                    outcome, _ = process_item(
                        root=root, provider="Open Library", item=item, binding=binding,
                        signal_terms=bq["signal_terms"], min_signal_hits=int(bq.get("min_signal_hits", 1)),
                        lens=lens, attention_terms=config["attention_terms"], all_claim_ids=all_claim_ids,
                        questions=questions, now_iso=now_iso,
                    )
                    outcome["rank"] = rank
                    qrec["results"].append(outcome)
                run_record["queries"].append(qrec)
                next_index = (qindex + 1) % len(book_queries)
                ol_state["query_index"] = next_index
                ol_state["page"] = page + 1 if next_index == 0 else page
            except Exception as exc:
                run_record["failures"].append({"provider": "Open Library", "mode": "historical_book_backfill", "historical_query_id": bq["id"], "query": bq["query"], "page": page, "error": f"{type(exc).__name__}: {exc}"})

    incremental_failed = any(f.get("mode") == "incremental" for f in run_record["failures"])
    if not incremental_failed:
        state["incremental_cursor_utc"] = now_iso
        run_record["cursor_advanced"] = True

    state["run_count"] += 1
    state["last_run_id"] = run_id
    state["last_run_status"] = "PARTIAL_SOURCE_FAILURE" if run_record["failures"] else "SUCCESS"
    state["updated_utc"] = now_iso
    state["total_unique_candidates"] = len(list((root / CANDIDATE_DIR).glob("FAR-LIT-*.json")))
    run_record["status"] = state["last_run_status"]
    run_record["finished_utc"] = now_iso
    write_json(root / STATE_PATH, state)
    write_json(root / RUN_DIR / f"{run_id}.json", run_record)
    render_dashboard(root, state, run_record)
    # Reconcile every unattended candidate-set change into the Research-only corpus input.
    # This executes protected-main code and grants no review or promotion authority.
    from tools.reconcile_research_corpus import write_living
    write_living(root)
    return run_record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    result = run(Path(args.root))
    print(json.dumps({
        "run_id": result["run_id"],
        "status": result["status"],
        "queries": len(result["queries"]),
        "failures": len(result["failures"]),
        "cursor_advanced": result["cursor_advanced"],
        "historical_advanced": result["historical_advanced"],
    }, sort_keys=True))
    return 0 if result["status"] in {"SUCCESS", "PARTIAL_SOURCE_FAILURE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
