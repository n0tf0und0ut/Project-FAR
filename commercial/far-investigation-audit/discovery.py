"""Bounded optional Tavily discovery. Hits are candidates, never evidence by themselves."""
from __future__ import annotations
import json
import os
from acquire import AcquisitionError, safe_url, resolve_public, _PinnedHTTPS


class DiscoveryError(ValueError):
    pass


def tavily_search(queries: list[str], *, allow_network: bool, requester=None,
                  max_queries: int = 3, max_results: int = 2) -> dict:
    if not allow_network:
        raise DiscoveryError("network discovery requires explicit authorization")
    if not 1 <= len(queries) <= max_queries <= 3 or not 1 <= max_results <= 3:
        raise DiscoveryError("query or result budget exceeded")
    if any(not isinstance(q, str) or not 3 <= len(q.strip()) <= 240 for q in queries):
        raise DiscoveryError("invalid search query")
    key = os.environ.get("TAVILY_API_KEY")
    if not key and requester is None:
        raise DiscoveryError("TAVILY_API_KEY not configured")
    receipt = {"provider": "tavily", "queries": [], "results": [], "coverage_complete": False,
               "semantic_relevance_verified": False, "source_authenticity_verified": False}
    seen = set()
    for query in queries:
        payload = {"api_key": key or "TEST_INJECTION", "query": query, "search_depth": "basic",
                   "max_results": max_results, "include_answer": False, "include_raw_content": False}
        if requester is None:
            raw = json.dumps(payload).encode()
            # Fixed API host; DNS checked/pinned; do not follow provider redirects
            # with credentials (unlike urllib's automatic redirect handler).
            try:
                ip = resolve_public("api.tavily.com")[0]
                conn = _PinnedHTTPS("api.tavily.com", ip, timeout=12)
                try:
                    conn.request("POST", "/search", body=raw, headers={
                        "Content-Type": "application/json", "Accept": "application/json",
                        "Content-Length": str(len(raw)), "Accept-Encoding": "identity"})
                    response = conn.getresponse()
                    if response.status != 200:
                        raise DiscoveryError("search provider refused request")
                    data = response.read(120_001)
                finally:
                    conn.close()
                if len(data) > 120_000:
                    raise DiscoveryError("search response exceeds byte cap")
                result = json.loads(data)
            except (OSError, ValueError, AcquisitionError) as exc:
                if isinstance(exc, DiscoveryError):
                    raise
                raise DiscoveryError("search provider request failed") from exc
        else:
            result = requester(payload)
        if not isinstance(result, dict) or not isinstance(result.get("results"), list):
            raise DiscoveryError("search provider returned malformed response")
        receipt["queries"].append(query)
        for x in result["results"][:max_results]:
            if not isinstance(x, dict) or not isinstance(x.get("url"), str):
                continue
            try:
                safe_url(x["url"])
            except (AcquisitionError, ValueError):
                continue
            url = x["url"]
            if url in seen:
                continue
            seen.add(url)
            receipt["results"].append({"url": url, "title": str(x.get("title", ""))[:200],
                                       "snippet": str(x.get("content", ""))[:800],
                                       "status": "UNVERIFIED_DISCOVERY_LEAD"})
    return receipt
