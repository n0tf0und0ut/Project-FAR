"""Source → proposed interpretations → bounded audit → report, replayable offline.

External lookup and LLM proposals are optional, untrusted, explicitly budgeted.
The default fully local path returns a truthful scoped result, including unknowns.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from acquire import (AcquisitionError, fetch_https, fetch_youtube_captions, parse_captions,
                     normalize_html, MAX_TRANSCRIPT)
from discovery import tavily_search, DiscoveryError
from engine import InvalidBundle, audit, canonical, digest, timestamp
from proposals import compile_proposal, heuristic_proposal, openai_proposal
from local_media import read_local_file
from presentation import render_markdown
from diagnostics import critical_questions

MAX_INPUT = 190_000
MAX_EVIDENCE_SOURCES = 8


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _loaded_source(config: dict, *, permit_network: bool, source_fetcher, yt_fetcher, permit_files: bool = False, permit_model: bool = False, transcription_client=None) -> tuple[str, dict, dict]:
    kind = config.get("kind")
    if kind in {"pdf_file", "media_file"}:
        if not permit_files:
            raise InvalidBundle("local file paths are disabled in server requests")
        if not isinstance(config.get("path"), str):
            raise InvalidBundle("local file path missing")
        extracted = read_local_file(kind, config["path"], permit_model=permit_model,
                                    transcription_client=transcription_client)
        return extracted["text"], extracted, config
    if kind not in {"text", "html", "srt", "vtt", "url", "youtube"}:
        raise InvalidBundle("source kind must be text, html, srt, vtt, url or youtube")
    if kind in {"text", "html", "srt", "vtt"}:
        raw = config.get("text")
        if not isinstance(raw, str) or not raw.strip() or len(raw.encode("utf-8")) > MAX_INPUT:
            raise InvalidBundle("source text missing or over limit")
        extracted = ({"text": normalize_html(raw)} if kind == "html" else
                     parse_captions(raw) if kind in {"srt", "vtt"} else {"text": raw})
        meta = {"raw_sha256": digest(raw.encode("utf-8")), "extraction": kind + "_provided_v1",
                "raw_snapshot_utf8": raw,
                "external_authenticity_verified": False}
        if "cues" in extracted:
            meta["cues"] = extracted["cues"]
        return extracted["text"], meta, config
    url = config.get("url")
    if not isinstance(url, str):
        raise InvalidBundle("remote URL required")
    if kind == "youtube":
        extracted = yt_fetcher(url, permit_network=permit_network)
    else:
        extracted = source_fetcher(url, permit_network=permit_network)
    if len(extracted["text"].encode("utf-8")) > MAX_INPUT:
        raise InvalidBundle("extracted source text over limit")
    # Live acquisition completes after the source bytes have been retrieved.
    return extracted["text"], {**extracted, "captured_at": _now()}, config


def investigate(config: dict, *, permit_network: bool = False,
                source_fetcher=fetch_https, yt_fetcher=fetch_youtube_captions,
                model_client=None, search_requester=None, permit_model: bool = False,
                permit_files: bool = False, transcription_client=None) -> dict:
    """Return the complete bounded investigation package without durable side effects."""
    if not isinstance(config, dict):
        raise InvalidBundle("request must be object")
    try:
        if len(canonical(config)) > 450_000:
            raise InvalidBundle("investigation request over byte cap")
    except (TypeError, ValueError, RecursionError) as exc:
        raise InvalidBundle("request is not finite valid JSON") from exc
    requested = config.get("captured_at", _now())
    timestamp(requested, "captured_at")
    primary_cfg = config.get("source")
    if not isinstance(primary_cfg, dict):
        raise InvalidBundle("primary source configuration missing")
    evidence_configs = config.get("evidence_sources", [])
    if (not isinstance(evidence_configs, list) or len(evidence_configs) > MAX_EVIDENCE_SOURCES
            or any(not isinstance(source, dict) for source in evidence_configs)):
        raise InvalidBundle("invalid or over-cap evidence source list")
    if permit_network and "captured_at" in config and (
        primary_cfg.get("kind") in {"url", "youtube"} or config.get("discovery") or
        any(x.get("kind") == "url" for x in evidence_configs)
    ):
        raise InvalidBundle("remote acquisition cannot be assigned a user-declared historical capture time")
    inv_id = config.get("investigation_id", "investigation")
    if not isinstance(inv_id, str) or not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,80}", inv_id):
        raise InvalidBundle("invalid investigation ID")
    text, primary_provenance, _ = _loaded_source(primary_cfg, permit_network=permit_network,
                                                source_fetcher=source_fetcher, yt_fetcher=yt_fetcher,
                                                permit_files=permit_files, permit_model=permit_model,
                                                transcription_client=transcription_client)
    source_texts = {"primary": text}
    meta = {"primary": {"origin_id": primary_cfg.get("origin_id"), "publication_date_verified": False,
                        "origin_verified": False,
                        "captured_at": primary_provenance.get("captured_at", requested)}}
    publications = {"primary": primary_cfg.get("published_at")}
    acquisitions = [{"source_id": "primary", **primary_provenance}]
    for i, scfg in enumerate(evidence_configs):
        if scfg.get("kind") not in {"text", "html", "url", "srt", "vtt", "pdf_file"}:
            raise InvalidBundle("evidence source kind unsupported")
        source, provenance, _ = _loaded_source(scfg, permit_network=permit_network,
                                                source_fetcher=source_fetcher, yt_fetcher=yt_fetcher,
                                                permit_files=permit_files, permit_model=permit_model,
                                                transcription_client=transcription_client)
        name = f"ev{i+1}"
        source_texts[name] = source
        publications[name] = scfg.get("published_at")
        meta[name] = {"origin_id": scfg.get("origin_id"), "publication_date_verified": False,
                      "origin_verified": False,
                      "captured_at": provenance.get("captured_at", requested)}
        acquisitions.append({"source_id": name, **provenance})
    discovery = None
    if config.get("discovery"):
        if config["discovery"] != "tavily":
            raise InvalidBundle("unsupported discovery provider")
        qs = config.get("queries")
        if not isinstance(qs, list):
            qs = [x["quote"][:240] for x in heuristic_proposal(text)["claims"][:3]]
        try:
            discovery = tavily_search(qs, allow_network=permit_network, requester=search_requester)
        except DiscoveryError as exc:
            raise InvalidBundle("discovery unavailable: " + str(exc)) from exc
        # Explicitly enabled source expansion fetches a bounded subset of leads,
        # preserving the distinction between a discovery snippet and source bytes.
        if config.get("expand_discovery"):
            for lead in discovery["results"][:4]:
                if len(source_texts) >= MAX_EVIDENCE_SOURCES + 1:
                    break
                try:
                    found = source_fetcher(lead["url"], permit_network=permit_network)
                except AcquisitionError as exc:
                    lead["fetch_status"] = "FAILED: " + str(exc)[:100]
                    continue
                sid = f"discovery{len(source_texts)}"
                found = {**found, "captured_at": _now()}
                source_texts[sid] = found["text"]
                publications[sid] = None
                meta[sid] = {"origin_id": None, "publication_date_verified": False,
                             "origin_verified": False, "captured_at": found["captured_at"]}
                acquisitions.append({"source_id": sid, **found})
                lead["fetch_status"] = "SNAPSHOT_RECORDED_UNAUTHENTICATED"
                lead["source_id"] = sid
    mode = config.get("proposal_mode", "heuristic")
    if mode == "heuristic":
        proposal = heuristic_proposal(text, {k: v for k,v in source_texts.items() if k != "primary"})
    elif mode == "supplied":
        proposal = config.get("proposal")
    elif mode == "openai":
        if not permit_model:
            raise InvalidBundle("external model requires explicit opt-in")
        proposal = openai_proposal(text, {k:v for k,v in source_texts.items() if k != "primary"},
                                  model=config.get("model", "gpt-4.1"), client=model_client)
    else:
        raise InvalidBundle("unknown proposal mode")
    # Bind exact acquisition records, including method and archived bytes,
    # into the hashed audit input. Not an external authenticity guarantee.
    for item in acquisitions:
        meta[item["source_id"]]["acquisition_sha256"] = digest(canonical(item))
    bundle = compile_proposal(proposal, source_texts, investigation_id=inv_id, captured_at=requested,
                              published_at_by_source=publications, source_meta=meta)
    # Bind even unexpanded network-discovery receipts into the immutable audit
    # identity; a removable, self-rehashable delivery file is insufficient.
    bundle["discovery_sha256"] = digest(canonical(discovery)) if discovery is not None else None
    result = audit(bundle)
    questions = critical_questions(bundle["claims"])
    # Advisory critical questions are a separately hashed adjunct, not part of
    # accepted formal audit or a counterfeit new assurance status.
    # Proposal notes/cue offsets remain outside formal report and cannot alter its outcome.
    rendered = render_markdown(bundle, result, acquisition=acquisitions, discovery=discovery,
                               questions=questions)
    # Model proposals and externally transcribed media transmit source material
    # to a provider even when the separate web-retrieval flag is disabled.
    # Network provenance must account for both trust boundaries.
    external_provider_used = (
        mode == "openai" or
        any(item.get("extraction") ==
            "external_speech_transcription_gpt_4o_transcribe_v1"
            for item in acquisitions)
    )
    manifest = {"schema": "far-investigation-delivery/0.3", "investigation_id": inv_id,
                "generated_at": requested, "method": proposal.get("method", mode),
                "input_sha256": result["input_sha256"], "report_sha256": result["report_sha256"],
                "report_md_sha256": digest(rendered.encode("utf-8")),
                "source_snapshots_sha256": {s["id"]: s["sha256"] for s in bundle["sources"]},
                "network_used": bool(
                    external_provider_used or
                    (permit_network and (
                        primary_cfg.get("kind") in ("url", "youtube") or
                        any(s.get("kind") == "url" for s in evidence_configs) or discovery))),
                "open_world_completeness": "UNESTABLISHED", "semantic_mapping_independently_verified": False,
                "end_to_end_production_quality": "UNESTABLISHED"}
    return {"bundle": bundle, "audit": result, "report_md": rendered, "manifest": manifest,
            "acquisition": acquisitions, "discovery": discovery, "proposal": proposal,
            "critical_questions": questions}
