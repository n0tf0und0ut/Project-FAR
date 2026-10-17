#!/usr/bin/env python3
"""Fail-closed, dependency-aware reconciliation for the governed FAR Research corpus.

The program automates validation and recomputation over human-governed semantic
inputs.  It never infers source meaning, verifies a paper by URL/DOI existence,
or promotes scientific status.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
CORPUS = Path("research/corpus/corpus-v1.0.json")
REVIEWED_INPUTS = Path("research/corpus/reviewed-inputs-v1.0.json")
OUTPUT = Path("research/corpus/synthesis-v1.0.json")
STATUS = Path("docs/research/current-research-frontier.md")
LIVING_RECONCILIATION = Path("research/living/corpus-reconciliation-v1.0.json")
SCHEMA = Path("schemas/far-research-corpus-v1.schema.json")
REVIEW_SCHEMA = Path("schemas/far-reviewed-input-v1.schema.json")
LEVELS = {"EVIDENCE", "INFERENCE", "HYPOTHESIS", "UNRESOLVED"}
RELATIONS = {"SUPPORTS", "CONTRADICTS", "QUALIFIES", "CORRECTS", "SUPERSEDES", "UNRESOLVED"}
POSITIVE_REPLACEMENTS = {"REPLACE_EQUIVALENT", "REPLACE_NARROWER"}
ARCHITECTURE_CLASSES = {
    "already_representable_enforceable", "representable_assurance_incomplete",
    "existing_extension_point", "genuine_architecture_gap", "contradiction", "unresolved",
}
SOURCE_SUFFIXES = {".json", ".md", ".yaml", ".yml", ".bib", ".csv"}
REVIEWED_PRIMARY_SUFFIXES = SOURCE_SUFFIXES | {".bin", ".pdf"}


class DuplicateKeyError(ValueError):
    pass


def _object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_bytes(raw: bytes, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_object_no_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
        raise ValueError(f"invalid JSON {label}: {exc}") from exc


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def safe_path(root: Path, relative: str, *, suffixes: set[str] | None = None) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"unsafe path: {relative}")
    path = root / candidate
    if path.is_symlink():
        raise ValueError(f"symlink input forbidden: {relative}")
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes repository: {relative}") from exc
    if suffixes is not None and path.suffix.lower() not in suffixes:
        raise ValueError(f"unexpected source file type: {relative}")
    return path


def load_json(path: Path, root: Path = ROOT) -> dict[str, Any]:
    resolved = safe_path(root, path.as_posix(), suffixes={".json"})
    value = strict_json_bytes(resolved.read_bytes(), path.as_posix())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def file_record(path: Path, root: Path = ROOT) -> dict[str, Any]:
    resolved = safe_path(root, path.as_posix())
    return {"path": path.as_posix(), "sha256": digest(resolved.read_bytes()), "size": resolved.stat().st_size}


def dynamic_dependencies(data: dict[str, Any], root: Path = ROOT) -> list[dict[str, Any]]:
    """Bind mutable generated state by its current bytes, never as immutable evidence."""
    records = []
    for dependency in data.get("dynamic_dependencies", []):
        path = safe_path(root, dependency["path"], suffixes={".json"})
        if not path.is_file():
            raise ValueError(f"missing dynamic dependency: {dependency['id']}")
        payload = strict_json_bytes(path.read_bytes(), dependency["path"])
        if payload.get(dependency["format_field"]) != dependency["format_value"]:
            raise ValueError(f"dynamic dependency format mismatch: {dependency['id']}")
        records.append({
            **dependency,
            "sha256": digest(path.read_bytes()),
            "size": path.stat().st_size,
            "evidence_usable": False,
        })
    return sorted(records, key=lambda row: row["id"])


def inventory(data: dict[str, Any], root: Path = ROOT) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for category in ("required_declared_globs", "automatic_lead_globs", "snapshot_globs", "semantic_input_globs"):
        for pattern in data["inventory_rules"][category]:
            if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
                raise ValueError(f"unsafe inventory pattern: {pattern}")
            for raw in glob.glob(str(root / pattern), recursive=True):
                path = Path(raw)
                if path.is_symlink():
                    raise ValueError(f"symlink inventory input forbidden: {path.relative_to(root)}")
                if path.is_file():
                    relative = path.relative_to(root)
                    record = file_record(relative, root)
                    record["category"] = category
                    records[relative.as_posix()] = record
    return [records[key] for key in sorted(records)]


def saturation_observations(root: Path = ROOT) -> list[dict[str, Any]]:
    relative = Path("research/corpus/snapshots/pr-571/research/saturation-falsification-001/findings-v1.0.json")
    path = safe_path(root, relative.as_posix(), suffixes={".json"})
    if not path.exists():
        return []
    payload = strict_json_bytes(path.read_bytes(), relative.as_posix())
    observations = []
    for finding in payload["findings"]:
        observations.append({
            "id": f"OBS-PR571-{finding['id']}", "proposition_id": finding["id"],
            "epistemic_class": "EVIDENCE", "statement": finding["evidence"],
            "scope": payload["campaign_conclusion"]["scope"], "scope_key": "saturation_v05_seven_attacks",
            "relation": "SUPPORTS", "relation_targets": [], "target_kind": "NONE",
            "replacement_effect": "NONE", "uncertainty": finding.get("minimal_repair", "bounded unmerged Research result"),
            "mechanism_ids": ["MEC-SATURATION-ATTACKS"], "dependencies": [], "history": [],
            "external_source_ids": finding["source_ids"], "architecture_disposition": finding["disposition"],
            "literal_mapping": finding["baseline_mapping"],
        })
    return observations


def _candidate_manifest_leads(root: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    relative = Path("research/corpus/snapshots/pr-490-manifest-v1.0.json")
    path = root / relative
    if path.exists():
        manifest = strict_json_bytes(path.read_bytes(), relative.as_posix())
        for item in manifest.get("candidate_blobs", []):
            candidate_id = Path(item["path"]).stem
            rows[candidate_id] = {
                "id": candidate_id, "path": item["path"], "sha256": item["sha256"],
                "git_blob": item["git_blob"], "external_identifier": None,
                "review_status": "DISCOVERED_PR490", "evidence_usable": False,
                "snapshot_head": manifest["head_sha"],
            }
    return rows


def living_leads(root: Path = ROOT) -> list[dict[str, Any]]:
    rows = _candidate_manifest_leads(root)
    for path in sorted((root / "research/living/inbox/candidates").glob("FAR-LIT-*.json")):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"unsafe living candidate: {path}")
        payload = strict_json_bytes(path.read_bytes(), str(path.relative_to(root)))
        candidate_id = payload.get("id", path.stem)
        row = rows.get(candidate_id, {"id": candidate_id})
        row.update({
            "current_repository_path": str(path.relative_to(root)),
            "current_repository_sha256": digest(path.read_bytes()),
            "external_identifier": payload.get("source_key"), "review_status": "DISCOVERED",
            "evidence_usable": False,
        })
        rows[candidate_id] = row
    external = root / "research/corpus/external"
    receipts = {path.stem: path for path in external.glob("*.json") if path.is_file() or path.is_symlink()} if external.exists() else {}
    blobs = {path.stem: path for path in external.glob("*.bin") if path.is_file() or path.is_symlink()} if external.exists() else {}
    if set(receipts) != set(blobs):
        raise ValueError(
            "external receipt/blob pairing mismatch: "
            f"orphan_blobs={sorted(set(blobs) - set(receipts))} "
            f"orphan_receipts={sorted(set(receipts) - set(blobs))}"
        )
    seen_external_sha256: set[str] = set()
    for stem in sorted(receipts):
        path = receipts[stem]
        blob = blobs[stem]
        if path.is_symlink() or blob.is_symlink() or not path.is_file() or not blob.is_file():
            raise ValueError(f"unsafe external frozen input: {path.relative_to(root)}")
        payload = strict_json_bytes(path.read_bytes(), str(path.relative_to(root)))
        blob_bytes = blob.read_bytes()
        blob_sha256 = digest(blob_bytes)
        receipt_sha256 = payload.get("sha256")
        if blob_sha256 != receipt_sha256 or len(blob_bytes) != payload.get("size"):
            raise ValueError(f"external frozen-byte receipt mismatch: {path.relative_to(root)}")
        if receipt_sha256 in seen_external_sha256:
            raise ValueError(f"duplicate external frozen-byte identity: {receipt_sha256}")
        seen_external_sha256.add(receipt_sha256)
        if stem != receipt_sha256:
            raise ValueError(
                "external receipt/blob identity mismatch: "
                f"stem={stem} receipt_sha256={receipt_sha256}"
            )
        rows[stem] = {
            "id": stem, "path": str(path.relative_to(root)), "sha256": digest(path.read_bytes()),
            "blob_path": str(blob.relative_to(root)), "blob_sha256": blob_sha256,
            "external_identifier": payload.get("origin"), "review_status": payload.get("review_status", "DISCOVERY_LEAD"),
            # Receipt flags never promote a lead. Only reviewed-input registry entries create evidence sources.
            "evidence_usable": False,
        }
    return [rows[key] for key in sorted(rows)]


def reviewed_sources(data: dict[str, Any], root: Path = ROOT) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    registry_path = Path(data["reviewed_input_registry"])
    try:
        registry = load_json(registry_path, root)
        schema = load_json(REVIEW_SCHEMA, ROOT)
    except (OSError, ValueError) as exc:
        return [], [str(exc)]
    errors.extend(f"review schema: {error.message}" for error in jsonschema.Draft202012Validator(schema).iter_errors(registry))
    corpus_schema = load_json(SCHEMA, ROOT)
    observation_schema = {**corpus_schema["$defs"]["observation"], "$defs": corpus_schema["$defs"]}
    observation_validator = jsonschema.Draft202012Validator(observation_schema)
    sources = []
    seen: set[str] = set()
    for entry in registry.get("entries", []):
        for observation in entry.get("observations", []):
            errors.extend(f"review observation schema: {error.message}" for error in observation_validator.iter_errors(observation))
        entry_id = entry.get("id")
        if entry_id in seen:
            errors.append(f"duplicate reviewed input identity: {entry_id}")
        seen.add(entry_id)
        try:
            candidate = safe_path(root, entry["candidate"]["path"], suffixes={".json"})
            primary = safe_path(root, entry["primary_evidence"]["path"], suffixes=REVIEWED_PRIMARY_SUFFIXES)
            review = safe_path(root, entry["review"]["path"], suffixes={".json", ".md"})
            for label, path, expected in (("candidate", candidate, entry["candidate"]["sha256"]), ("primary evidence", primary, entry["primary_evidence"]["sha256"]), ("review", review, entry["review"]["sha256"])):
                if not path.is_file() or digest(path.read_bytes()) != expected:
                    errors.append(f"reviewed input {entry_id} {label} hash mismatch")
            if entry["review"]["status"] != "VERIFIED_FOR_CORPUS":
                errors.append(f"reviewed input {entry_id} lacks VERIFIED_FOR_CORPUS review")
            if not entry["primary_evidence"].get("independently_verified"):
                errors.append(f"reviewed input {entry_id} primary evidence not independently verified")
        except (KeyError, ValueError) as exc:
            errors.append(f"reviewed input {entry_id}: {exc}")
            continue
        sources.append({
            "id": f"SRC-REVIEWED-{entry_id}", "source_identity": entry_id,
            "path": entry["primary_evidence"]["path"], "sha256": entry["primary_evidence"]["sha256"],
            "version": entry["primary_evidence"]["version"], "external_identifier": entry["primary_evidence"]["external_identifier"],
            "evidence_class": entry["evidence_class"], "kind": "reviewed_external_primary_evidence",
            "current_availability": "available", "historical_availability": "PRESENT",
            "evidence_usable": True, "material": True, "scope": entry["scope"], "history": [entry["review"]],
            "supersedes": [], "corrects": [], "observations": entry["observations"],
            "review_status": "VERIFIED_FOR_CORPUS", "primary_evidence_verified": True,
        })
    return sources, errors


def _cycles(graph: dict[str, list[str]], label: str) -> list[str]:
    errors: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(node: str) -> None:
        if node in visiting:
            errors.append(f"circular {label} at {node}")
            return
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph.get(node, []):
            visit(dependency)
        visiting.remove(node)
        visited.add(node)
    for node in graph:
        visit(node)
    return errors


def validate(data: dict[str, Any], root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        schema = load_json(SCHEMA, ROOT)
        errors.extend(f"schema: {error.message}" for error in jsonschema.Draft202012Validator(schema).iter_errors(data))
        reviewed, review_errors = reviewed_sources(data, root)
        errors.extend(review_errors)
        sources_list = list(data.get("sources", [])) + reviewed
        inv = inventory(data, root)
    except (OSError, ValueError) as exc:
        return [str(exc)]
    identity: dict[str, str] = {}
    for kind, rows in (("source", sources_list), ("dynamic dependency", data.get("dynamic_dependencies", [])), ("mechanism", data.get("mechanism_catalog", [])), ("conclusion", data.get("conclusion_rules", [])), ("frontier", data.get("frontier_rules", []))):
        for row in rows:
            row_id = row.get("id")
            if row_id in identity:
                errors.append(f"duplicate identity {row_id}")
            identity[row_id] = kind
    dynamic_paths = [row.get("path") for row in data.get("dynamic_dependencies", [])]
    if len(dynamic_paths) != len(set(dynamic_paths)):
        errors.append("duplicate dynamic dependency path")
    try:
        dynamic_dependencies(data, root)
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
    sources = {source["id"]: source for source in sources_list}
    mechanisms = {mechanism["id"]: mechanism for mechanism in data.get("mechanism_catalog", [])}
    conclusions = {conclusion["id"]: conclusion for conclusion in data.get("conclusion_rules", [])}
    observations = {observation["id"]: observation for source in sources_list for observation in source.get("observations", [])}
    proposition_ids = {observation["proposition_id"] for observation in observations.values()}
    if sum(len(source.get("observations", [])) for source in sources_list) != len(observations):
        errors.append("duplicate observation identity")
    declared_paths = {source.get("path") for source in sources.values() if source.get("path")}
    declared_paths.update(item.get("path") for item in data.get("dynamic_dependencies", []))
    for record in inv:
        if record["category"] == "required_declared_globs" and record["path"] not in declared_paths:
            errors.append(f"unclassified material input: {record['path']}")
    source_graph: dict[str, list[str]] = {}
    observation_history_graph: dict[str, list[str]] = {}
    observation_dependency_graph: dict[str, list[str]] = {}
    for source in sources.values():
        source_graph[source["id"]] = source.get("supersedes", []) + source.get("corrects", [])
        if any(reference not in sources for reference in source_graph[source["id"]]):
            errors.append(f"source history has unknown reference: {source['id']}")
        path_text = source.get("path")
        if source.get("current_availability") == "available":
            try:
                allowed_suffixes = REVIEWED_PRIMARY_SUFFIXES if source.get("kind") == "reviewed_external_primary_evidence" else SOURCE_SUFFIXES
                path = safe_path(root, path_text, suffixes=allowed_suffixes)
                if not path.is_file() or digest(path.read_bytes()) != source.get("sha256"):
                    errors.append(f"source hash mismatch: {source['id']}")
            except (TypeError, ValueError) as exc:
                errors.append(str(exc))
        if source.get("evidence_usable") and (source.get("review_status") not in {"GOVERNED_REPOSITORY_SOURCE", "VERIFIED_FOR_CORPUS"} or not source.get("primary_evidence_verified")):
            errors.append(f"source lacks governed evidence verification: {source['id']}")
        if source.get("kind") in {"ai_summary", "scheduled_task_summary", "living_inbox_snapshot"} and source.get("evidence_usable"):
            errors.append(f"discovery metadata promoted as evidence: {source['id']}")
        for observation in source.get("observations", []):
            observation_id = observation["id"]
            targets = observation.get("relation_targets", [])
            relation = observation.get("relation")
            observation_dependency_graph[observation_id] = observation.get("dependencies", [])
            if any(reference not in observations for reference in observation_dependency_graph[observation_id]):
                errors.append(f"observation has unknown dependency: {observation_id}")
            if relation in {"CORRECTS", "SUPERSEDES"}:
                observation_history_graph[observation_id] = targets
                if not targets or observation.get("target_kind") != "OBSERVATION" or any(target not in observations for target in targets):
                    errors.append(f"invalid {relation} targets: {observation_id}")
                if observation.get("replacement_effect") not in {"INVALIDATE_ONLY", *POSITIVE_REPLACEMENTS}:
                    errors.append(f"invalid replacement effect: {observation_id}")
                if observation.get("replacement_effect") == "INVALIDATE_ONLY" and observation.get("mechanism_ids"):
                    errors.append(f"invalidate-only history cannot support mechanisms: {observation_id}")
            else:
                observation_history_graph[observation_id] = []
                if relation == "SUPPORTS" and targets:
                    errors.append(f"SUPPORTS cannot target another finding: {observation_id}")
                if relation in {"CONTRADICTS", "QUALIFIES", "UNRESOLVED"}:
                    known = observations if observation.get("target_kind") == "OBSERVATION" else proposition_ids if observation.get("target_kind") == "PROPOSITION" else set()
                    if not targets or any(target not in known for target in targets):
                        errors.append(f"invalid {relation} targets: {observation_id}")
                if observation.get("replacement_effect") != "NONE":
                    errors.append(f"non-history relation has replacement effect: {observation_id}")
            if observation.get("epistemic_class") == "EVIDENCE" and not source.get("evidence_usable"):
                errors.append(f"evidence observation lacks usable source: {observation_id}")
            if relation == "SUPPORTS" and observation.get("epistemic_class") == "UNRESOLVED":
                errors.append(f"UNRESOLVED observation cannot SUPPORT: {observation_id}")
            if any(mechanism not in mechanisms for mechanism in observation.get("mechanism_ids", [])):
                errors.append(f"observation has unknown mechanism: {observation_id}")
    errors.extend(_cycles(source_graph, "source correction/supersession"))
    errors.extend(_cycles(observation_history_graph, "observation correction/supersession"))
    errors.extend(_cycles(observation_dependency_graph, "observation dependency"))
    aliases: dict[str, str] = {}
    for mechanism in mechanisms.values():
        for label in [mechanism["name"], *mechanism.get("aliases", [])]:
            normalized = re.sub(r"[^a-z0-9]+", "", label.lower())
            if normalized in aliases and aliases[normalized] != mechanism["id"]:
                errors.append(f"duplicate mechanism alias: {mechanism['id']} and {aliases[normalized]}")
            aliases[normalized] = mechanism["id"]
        if mechanism.get("architecture_class") == "genuine_architecture_gap" and not mechanism.get("gap_proof"):
            errors.append(f"unproved genuine architecture gap: {mechanism['id']}")
    conclusion_graph = {conclusion["id"]: conclusion.get("depends_on_conclusions", []) for conclusion in conclusions.values()}
    for conclusion in conclusions.values():
        if any(reference not in conclusions for reference in conclusion_graph[conclusion["id"]]):
            errors.append(f"conclusion has unknown dependency: {conclusion['id']}")
        if set(conclusion.get("required_scope_keys", {})) != set(conclusion.get("required_mechanisms", [])):
            errors.append(f"conclusion scope contract mismatch: {conclusion['id']}")
        for mechanism, scope in conclusion.get("required_scope_keys", {}).items():
            if mechanism not in mechanisms or scope not in mechanisms[mechanism].get("accepted_scope_keys", []):
                errors.append(f"conclusion scope not admitted by mechanism: {conclusion['id']}:{mechanism}:{scope}")
    errors.extend(_cycles(conclusion_graph, "conclusion dependency"))
    for frontier in data.get("frontier_rules", []):
        if any(reference not in conclusions for reference in frontier.get("conclusion_ids", [])):
            errors.append(f"frontier has unknown conclusion: {frontier['id']}")
    errors.extend(validate_snapshots(root))
    return sorted(set(errors))


def validate_snapshots(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    pr571_path = root / "research/corpus/snapshots/pr-571-manifest-v1.0.json"
    if pr571_path.exists():
        try:
            manifest = strict_json_bytes(pr571_path.read_bytes(), str(pr571_path.relative_to(root)))
            if not re.fullmatch(r"[0-9a-f]{40}", manifest.get("head_sha", "")) or not re.fullmatch(r"[0-9a-f]{40}", manifest.get("base_sha", "")):
                errors.append("PR #571 invalid ref identity")
            files = manifest.get("files", [])
            if manifest.get("file_inventory_sha256") != digest(canonical(files)):
                errors.append("PR #571 file inventory digest mismatch")
            snapshot_root = root / "research/corpus/snapshots/pr-571"
            listed = {item["path"] for item in files}
            actual = {
                path.relative_to(snapshot_root).as_posix()
                for path in snapshot_root.rglob("*")
                if path.is_file()
            } if snapshot_root.exists() else set()
            if listed != actual:
                errors.append(
                    "PR #571 snapshot manifest coverage mismatch: "
                    f"unlisted={sorted(actual - listed)} missing={sorted(listed - actual)}"
                )
            required_extractor_inputs = {
                "research/saturation-falsification-001/findings-v1.0.json"
            }
            if not required_extractor_inputs <= listed:
                errors.append(
                    "PR #571 extractor input omitted from manifest: "
                    f"{sorted(required_extractor_inputs - listed)}"
                )
            for item in files:
                path = safe_path(root, "research/corpus/snapshots/pr-571/" + item["path"])
                if not path.is_file() or digest(path.read_bytes()) != item["sha256"] or path.stat().st_size != item["size"]:
                    errors.append(f"PR #571 snapshot drift: {item['path']}")
        except (KeyError, ValueError) as exc:
            errors.append(str(exc))
    pr490_path = root / "research/corpus/snapshots/pr-490-manifest-v1.0.json"
    if pr490_path.exists():
        try:
            manifest = strict_json_bytes(pr490_path.read_bytes(), str(pr490_path.relative_to(root)))
            if not re.fullmatch(r"[0-9a-f]{40}", manifest.get("head_sha", "")) or not re.fullmatch(r"[0-9a-f]{40}", manifest.get("tree_sha", "")):
                errors.append("PR #490 invalid ref identity")
            blobs = manifest.get("candidate_blobs", [])
            if manifest.get("candidate_inventory_sha256") != digest(canonical(blobs)) or manifest.get("state_inventory_sha256") != digest(canonical(manifest.get("state_blobs", []))):
                errors.append("PR #490 inventory digest mismatch")
            if manifest.get("candidate_count") != len(blobs) or len({item.get("path") for item in blobs}) != len(blobs):
                errors.append("PR #490 candidate inventory incomplete or duplicate")
            for item in blobs:
                if not re.fullmatch(r"[0-9a-f]{40}", item.get("git_blob", "")) or not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")):
                    errors.append(f"PR #490 invalid content identity: {item.get('path')}")
        except ValueError as exc:
            errors.append(str(exc))
    return errors


def _transitively_invalidated(active_observations: dict[str, dict[str, Any]]) -> set[str]:
    history = {observation_id: observation["relation_targets"] for observation_id, observation in active_observations.items() if observation["relation"] in {"CORRECTS", "SUPERSEDES"}}
    targeted = {target for targets in history.values() for target in targets}
    roots = [observation_id for observation_id in history if observation_id not in targeted]
    invalidated: set[str] = set()
    stack = [target for root in roots for target in history[root]]
    while stack:
        target = stack.pop()
        if target in invalidated:
            continue
        invalidated.add(target)
        stack.extend(history.get(target, []))
    return invalidated


def derive(data: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    reviewed, review_errors = reviewed_sources(data, root)
    if review_errors:
        raise ValueError("; ".join(review_errors))
    sources = list(data["sources"]) + reviewed
    source_by_id = {source["id"]: source for source in sources}
    source_active = {
        source["id"]: source["current_availability"] == "available" and source["evidence_usable"]
        for source in sources
    }
    # Governed correction/supersession history remains operative after later withdrawal;
    # withdrawal cannot silently resurrect a retired source.
    source_history = {source["id"]: source.get("corrects", []) + source.get("supersedes", []) for source in sources if source.get("review_status") in {"GOVERNED_REPOSITORY_SOURCE", "VERIFIED_FOR_CORPUS"} and source.get("primary_evidence_verified")}
    retired_sources: set[str] = set()
    stack = [target for targets in source_history.values() for target in targets]
    while stack:
        target = stack.pop()
        if target in retired_sources:
            continue
        retired_sources.add(target)
        stack.extend(source_history.get(target, []))
    for target in retired_sources:
        if target in source_active:
            source_active[target] = False
    observations: dict[str, dict[str, Any]] = {}
    observation_source: dict[str, str] = {}
    for source in sources:
        rows = list(source.get("observations", []))
        if source.get("auto_extractor") == "saturation_falsification_001" and source_active[source["id"]]:
            rows += saturation_observations(root)
        for observation in rows:
            observations[observation["id"]] = observation
            observation_source[observation["id"]] = source["id"]
    initially_active = {observation_id: observation for observation_id, observation in observations.items() if source_active[observation_source[observation_id]]}
    # Explicit UNRESOLVED observations may preserve missing-input uncertainty even when
    # their source is unavailable. These remain non-supporting signals, never evidence.
    uncertainty_only = {
        observation_id: observation
        for observation_id, observation in observations.items()
        if observation["relation"] == "UNRESOLVED"
        and not source_active[observation_source[observation_id]]
        and source_by_id[observation_source[observation_id]].get("current_availability") != "available"
    }
    history_observations = {observation_id: observation for observation_id, observation in observations.items() if source_by_id[observation_source[observation_id]].get("review_status") in {"GOVERNED_REPOSITORY_SOURCE", "VERIFIED_FOR_CORPUS"} and source_by_id[observation_source[observation_id]].get("primary_evidence_verified")}
    invalidated = _transitively_invalidated(history_observations)
    active = {observation_id: observation for observation_id, observation in initially_active.items() if observation_id not in invalidated}
    # A support observation whose declared dependencies are no longer active cannot support
    # downstream synthesis. Compute to a fixed point so staleness propagates transitively.
    dependency_inactive: set[str] = set()
    changed = True
    while changed:
        changed = False
        for observation_id, observation in active.items():
            if observation_id in dependency_inactive:
                continue
            if any(
                dependency not in active or dependency in dependency_inactive
                for dependency in observation.get("dependencies", [])
            ):
                dependency_inactive.add(observation_id)
                changed = True
    proposition_for_observation = {observation_id: observation["proposition_id"] for observation_id, observation in observations.items()}
    supports: dict[str, list[str]] = defaultdict(list)
    contradictions: dict[str, list[str]] = defaultdict(list)
    qualifications: dict[str, list[str]] = defaultdict(list)
    unresolved: dict[str, list[str]] = defaultdict(list)
    signal_observations = {**active, **uncertainty_only}
    for observation_id, observation in signal_observations.items():
        relation = observation["relation"]
        if observation_id in dependency_inactive:
            unresolved[observation["proposition_id"]].append(observation_id)
            continue
        if relation == "SUPPORTS" or (relation in {"CORRECTS", "SUPERSEDES"} and observation["replacement_effect"] in POSITIVE_REPLACEMENTS):
            supports[observation["proposition_id"]].append(observation_id)
        for target in observation.get("relation_targets", []):
            proposition = proposition_for_observation[target] if observation["target_kind"] == "OBSERVATION" else target
            if relation == "CONTRADICTS": contradictions[proposition].append(observation_id)
            elif relation == "QUALIFIES": qualifications[proposition].append(observation_id)
            elif relation == "UNRESOLVED": unresolved[proposition].append(observation_id)
    proposition_ids = sorted({observation["proposition_id"] for observation in observations.values()})
    findings = []
    mechanism_signals: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for proposition_id in proposition_ids:
        support_ids = supports[proposition_id]
        support_rows = [active[observation_id] for observation_id in support_ids]
        statements = {(row["statement"], row["scope_key"]) for row in support_rows}
        if len(statements) > 1:
            state = "AMBIGUOUS_ACTIVE_SUPPORT"
        elif contradictions[proposition_id]:
            state = "CONTRADICTED"
        elif qualifications[proposition_id]:
            state = "QUALIFIED"
        elif unresolved[proposition_id] or not support_ids:
            state = "UNRESOLVED" if unresolved[proposition_id] else "NO_ACTIVE_SUPPORT"
        else:
            state = "SUPPORTED"
        mechanism_ids = sorted({mechanism for row in support_rows for mechanism in row.get("mechanism_ids", [])} | {mechanism for observation_id in contradictions[proposition_id] + qualifications[proposition_id] + unresolved[proposition_id] for mechanism in signal_observations[observation_id].get("mechanism_ids", [])})
        for mechanism in mechanism_ids:
            mechanism_signals[mechanism][state].add(proposition_id)
        findings.append({
            "id": proposition_id, "state": state,
            "active_support_observation_ids": sorted(support_ids),
            "contradiction_observation_ids": sorted(contradictions[proposition_id]),
            "qualification_observation_ids": sorted(qualifications[proposition_id]),
            "qualification_details": [{"observation_id": observation_id, "statement": signal_observations[observation_id]["statement"], "scope": signal_observations[observation_id]["scope"], "scope_key": signal_observations[observation_id]["scope_key"]} for observation_id in sorted(qualifications[proposition_id])],
            "contradiction_details": [{"observation_id": observation_id, "statement": signal_observations[observation_id]["statement"], "scope": signal_observations[observation_id]["scope"], "scope_key": signal_observations[observation_id]["scope_key"]} for observation_id in sorted(contradictions[proposition_id])],
            "unresolved_observation_ids": sorted(unresolved[proposition_id]),
            "unresolved_details": [{"observation_id": observation_id, "statement": signal_observations[observation_id]["statement"], "scope": signal_observations[observation_id]["scope"], "scope_key": signal_observations[observation_id]["scope_key"]} for observation_id in sorted(unresolved[proposition_id])],
            "historical_inactive_observation_ids": sorted(observation_id for observation_id, observation in observations.items() if observation["proposition_id"] == proposition_id and observation_id not in active and observation_id not in uncertainty_only),
            "statements_and_scopes": sorted([{"statement": statement, "scope_key": scope} for statement, scope in statements], key=lambda row: (row["scope_key"], row["statement"])),
            "mechanism_ids": mechanism_ids,
            "dependency_sha256": digest(canonical({
                "signals": [
                    {
                        "id": observation_id,
                        "observation": observations[observation_id],
                        "source_id": observation_source[observation_id],
                        "source_sha256": source_by_id[observation_source[observation_id]].get("sha256"),
                    }
                    for observation_id in sorted(set(support_ids + contradictions[proposition_id] + qualifications[proposition_id] + unresolved[proposition_id]))
                ],
                "invalidated": sorted(invalidated),
                "dependency_inactive": sorted(dependency_inactive),
            })),
        })
    mechanisms = []
    mechanism_by_id: dict[str, dict[str, Any]] = {}
    for definition in sorted(data["mechanism_catalog"], key=lambda row: row["id"]):
        signal = mechanism_signals[definition["id"]]
        if signal["CONTRADICTED"]:
            state = "CONTRADICTED"
        elif signal["AMBIGUOUS_ACTIVE_SUPPORT"]:
            state = "AMBIGUOUS"
        elif signal["QUALIFIED"]:
            state = "QUALIFIED"
        elif signal["UNRESOLVED"]:
            state = "UNRESOLVED"
        elif signal["SUPPORTED"]:
            state = "SUPPORTED"
        else:
            state = "NO_ACTIVE_SUPPORT"
        support_pairs = sorted({
            (active[observation_id]["scope_key"], active[observation_id]["epistemic_class"])
            for finding in findings
            if finding["state"] == "SUPPORTED" and definition["id"] in finding["mechanism_ids"]
            for observation_id in finding["active_support_observation_ids"]
            if definition["id"] in active[observation_id].get("mechanism_ids", [])
        })
        support_scopes = sorted({scope for scope, _ in support_pairs})
        finding_ids = sorted({proposition for values in signal.values() for proposition in values})
        row = {**definition, "state": state, "support_scope_keys": support_scopes, "support_scope_epistemic_classes": [{"scope_key": scope, "epistemic_class": level} for scope, level in support_pairs], "finding_ids": finding_ids}
        row["dependency_sha256"] = digest(canonical({
            "state": state,
            "support_scopes": support_scopes,
            "findings": [finding for finding in findings if finding["id"] in finding_ids],
        }))
        mechanisms.append(row)
        mechanism_by_id[row["id"]] = row
    conclusion_by_id: dict[str, dict[str, Any]] = {}
    pending = {rule["id"]: rule for rule in data["conclusion_rules"]}
    while pending:
        ready = [rule for rule in pending.values() if all(dependency in conclusion_by_id for dependency in rule["depends_on_conclusions"])]
        if not ready:
            raise ValueError("conclusion dependency cycle")
        for rule in ready:
            blocked: dict[str, str] = {}
            for mechanism_id in rule["required_mechanisms"]:
                mechanism = mechanism_by_id[mechanism_id]
                required_scope = rule["required_scope_keys"][mechanism_id]
                if mechanism["state"] != "SUPPORTED":
                    blocked[mechanism_id] = mechanism["state"]
                elif required_scope not in mechanism["support_scope_keys"]:
                    blocked[mechanism_id] = "SCOPE_NOT_SUPPORTED"
                else:
                    admissible = {"EVIDENCE": {"EVIDENCE"}, "INFERENCE": {"EVIDENCE", "INFERENCE"}, "HYPOTHESIS": {"EVIDENCE", "INFERENCE", "HYPOTHESIS"}, "UNRESOLVED": {"EVIDENCE", "INFERENCE", "HYPOTHESIS"}}[rule["result_class"]]
                    scoped_classes = {item["epistemic_class"] for item in mechanism["support_scope_epistemic_classes"] if item["scope_key"] == required_scope}
                    if not (scoped_classes & admissible):
                        blocked[mechanism_id] = "EPISTEMIC_CEILING"
            epistemic_rank = {"EVIDENCE": 0, "INFERENCE": 1, "HYPOTHESIS": 2, "UNRESOLVED": 3}
            dependency_blocks: dict[str, str] = {}
            for dependency in rule["depends_on_conclusions"]:
                dependency_class = conclusion_by_id[dependency]["epistemic_class"]
                if dependency_class == "UNRESOLVED":
                    dependency_blocks[dependency] = "UNRESOLVED"
                elif epistemic_rank[dependency_class] > epistemic_rank[rule["result_class"]]:
                    dependency_blocks[dependency] = "EPISTEMIC_CEILING"
            stale_dependencies = sorted(dependency_blocks)
            supported = not blocked and not dependency_blocks
            row = {
                "id": rule["id"], "epistemic_class": rule["result_class"] if supported else "UNRESOLVED",
                "disposition": rule["supported_disposition"] if supported else rule["missing_disposition"],
                "statement": rule["statement"] if supported else "Synthesis unresolved: required support is missing, narrowed, qualified, contradicted, ambiguous, corrected/superseded, or transitively stale.",
                "required_mechanisms": rule["required_mechanisms"], "required_scope_keys": rule["required_scope_keys"],
                "depends_on_conclusions": rule["depends_on_conclusions"], "blocked_mechanisms": blocked,
                "stale_dependencies": stale_dependencies, "dependency_blocks": dependency_blocks, "counterevidence": rule["counterevidence"],
            }
            row["dependency_sha256"] = digest(canonical({"mechanisms": [mechanism_by_id[mechanism] for mechanism in rule["required_mechanisms"]], "dependencies": [conclusion_by_id[dependency] for dependency in rule["depends_on_conclusions"]], "rule": rule}))
            conclusion_by_id[row["id"]] = row
            del pending[rule["id"]]
    conclusions = [conclusion_by_id[rule["id"]] for rule in data["conclusion_rules"]]
    frontier = []
    for rule in data["frontier_rules"]:
        linked = [conclusion_by_id[conclusion] for conclusion in rule["conclusion_ids"]]
        epistemic_class = "UNRESOLVED" if any(conclusion["epistemic_class"] == "UNRESOLVED" for conclusion in linked) else rule["epistemic_class"]
        frontier.append({
            **rule, "epistemic_class": epistemic_class,
            "status": "OPEN" if epistemic_class in {"UNRESOLVED", "HYPOTHESIS"} else rule["status_if_current"],
            "dependency_sha256": digest(canonical(linked)),
        })
    inv = inventory(data, root)
    dynamic = dynamic_dependencies(data, root)
    leads = living_leads(root)
    completeness = {
        "inventory": {"status": "COMPLETE_RELATIVE_TO_DECLARED_RULES_AND_FROZEN_MANIFESTS", "scope": data["completeness_contract"]["inventory_scope"]},
        "evidence": {"status": "INCOMPLETE_UNVERIFIED_LEADS_PRESENT" if leads else "COMPLETE_FOR_REGISTERED_VERIFIED_SOURCES_ONLY", "scope": data["completeness_contract"]["evidence_scope"]},
        "search": {"status": "BOUNDED_NOT_GLOBAL", "scope": data["completeness_contract"]["search_scope"]},
        "synthesis": {"status": "COMPLETE_FOR_ACTIVE_GOVERNED_SEMANTIC_INPUTS", "scope": data["completeness_contract"]["synthesis_scope"]},
        "global_open_world": {"status": "UNESTABLISHED", "scope": data["completeness_contract"]["global_scope"]},
    }
    return {
        "format_version": "far-research-synthesis/1.2", "authority": "Research",
        "generator_sha256": digest(Path(__file__).read_bytes()), "schema_sha256": digest((ROOT / SCHEMA).read_bytes()),
        "review_schema_sha256": digest((ROOT / REVIEW_SCHEMA).read_bytes()), "review_registry_sha256": digest((root / Path(data["reviewed_input_registry"])).read_bytes()),
        "corpus_sha256": digest(canonical(data)), "inventory": inv, "inventory_sha256": digest(canonical(inv)),
        "dynamic_dependencies": dynamic, "dynamic_dependencies_sha256": digest(canonical(dynamic)),
        "synthesis_input_sha256": digest(canonical({"corpus": digest(canonical(data)), "inventory": digest(canonical(inv)), "dynamic_dependencies": digest(canonical(dynamic))})),
        "completeness": completeness,
        "sources": [{"id": source["id"], "source_identity": source["source_identity"], "path": source.get("path"), "sha256": source.get("sha256"), "version": source.get("version"), "external_identifier": source.get("external_identifier"), "current_availability": source["current_availability"], "historical_availability": source["historical_availability"], "evidence_usable": source["evidence_usable"], "review_status": source["review_status"], "active": source_active[source["id"]]} for source in sources],
        "observations": [{**observations[observation_id], "source_id": observation_source[observation_id], "source_sha256": source_by_id[observation_source[observation_id]].get("sha256"), "active": observation_id in active, "uncertainty_signal": observation_id in uncertainty_only, "historical_inactive": observation_id not in active and observation_id not in uncertainty_only, "invalidated_by_history": observation_id in invalidated, "dependency_inactive": observation_id in dependency_inactive} for observation_id in sorted(observations)],
        "observation_state": {"active": sorted(active), "uncertainty_signals": sorted(uncertainty_only), "historical_inactive": sorted(set(observations) - set(active) - set(uncertainty_only)), "invalidated_by_history": sorted(invalidated), "dependency_inactive": sorted(dependency_inactive)},
        "normalized_findings": findings, "mechanisms": mechanisms, "conclusions": conclusions, "frontier": frontier,
        "untrusted_leads": leads, "untrusted_lead_count": len(leads), "nonclaims": data["nonclaims"],
        "automation_boundary": {
            "automatic": ["inventory", "schema and semantic validation", "normalization of declared observations", "relation/history evaluation", "mechanism deduplication", "dependency recomputation", "stale-output detection", "lead reconciliation", "deterministic view generation"],
            "curator_governed": ["primary-source verification", "atomic finding decomposition", "semantic relation assignment", "scope keys", "mechanism mapping", "conclusion rules", "scientific acceptance", "promotion"],
        },
    }


def markdown(result: dict[str, Any]) -> str:
    completeness = result["completeness"]
    lines = [
        "# Current FAR research frontier", "",
        "Status: **Generated dependency-aware Research synthesis; not scientific promotion authority**", "",
        f"Corpus identity: `{result['corpus_sha256']}`", f"Inventory identity: `{result['inventory_sha256']}`", f"Synthesis-input identity: `{result['synthesis_input_sha256']}`", "",
        "## Bounded completeness", "",
        "| Dimension | Status | Meaning |", "|---|---|---|",
    ]
    for key in ("inventory", "evidence", "search", "synthesis", "global_open_world"):
        item = completeness[key]
        lines.append(f"| `{key}` | `{item['status']}` | {item['scope']} |")
    lines += [
        "", f"The declared inventory contains **{len(result['inventory'])} paths** and **{result['untrusted_lead_count']} untrusted leads**. Inventory closure is repository-bounded and does not imply evidence, search, synthesis, or global completeness.",
        "", "## Automation boundary", "",
        "The system automatically validates and recomputes only over declared semantic inputs. Human-governed review must verify primary evidence and assign findings, relations, scopes, mechanisms, and conclusion rules. Discovery metadata, summaries, URLs, and DOI presence cannot self-promote into evidence.",
        "", "## Reconciled conclusions", "", "| Conclusion | Class | Disposition | Result |", "|---|---|---|---|",
    ]
    for conclusion in result["conclusions"]:
        lines.append(f"| `{conclusion['id']}` | **{conclusion['epistemic_class']}** | `{conclusion['disposition']}` | {conclusion['statement']} |")
    lines += ["", "## Deduplicated mechanism comparison", "", "| Mechanism | State | Classification | Literal comparison |", "|---|---|---|---|"]
    for mechanism in result["mechanisms"]:
        lines.append(f"| `{mechanism['id']}` {mechanism['name']} | `{mechanism['state']}` | `{mechanism['architecture_class']}` | {mechanism['literal_comparison']} |")
    lines += ["", "## Frontier", ""]
    for frontier in result["frontier"]:
        lines += [f"### {frontier['id']}: {frontier['question']}", "", f"**{frontier['epistemic_class']} — {frontier['status']}.** {frontier['next_evidence']}", ""]
    lines += ["## Nonclaims", "", *[f"- {nonclaim}" for nonclaim in result["nonclaims"]]]
    return "\n".join(lines) + "\n"


def write_living(root: Path = ROOT) -> dict[str, Any]:
    leads = living_leads(root)
    output = {
        "format_version": "far-living-corpus-reconciliation/1.1", "authority": "Research",
        "candidate_count": len(leads), "candidate_set_sha256": digest(canonical(leads)), "candidates": leads,
        "review_bridge": "research/corpus/reviewed-inputs-v1.0.json", "promotion_authority": False,
    }
    path = root / LIVING_RECONCILIATION
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(output))
    return output


def freeze_external(path: Path, origin: str, root: Path = ROOT) -> None:
    raw = path.read_bytes()
    sha256 = digest(raw)
    directory = root / "research/corpus/external"
    directory.mkdir(parents=True, exist_ok=True)
    blob = directory / f"{sha256}.bin"
    if blob.exists() and blob.read_bytes() != raw:
        raise ValueError("SHA-256 collision")
    blob.write_bytes(raw)
    receipt = {
        "format_version": "far-frozen-input/1.1", "sha256": sha256, "size": len(raw), "origin": origin,
        "authority": "discovery_lead", "executable": False, "primary_evidence_verified": False,
        "review_status": "DISCOVERY_LEAD", "review_bridge": "research/corpus/reviewed-inputs-v1.0.json",
    }
    (directory / f"{sha256}.json").write_bytes(canonical(receipt))
    write_living(root)
    print(blob.relative_to(root))


def expected_outputs(data: dict[str, Any], root: Path = ROOT) -> dict[Path, bytes]:
    result = derive(data, root)
    return {OUTPUT: canonical(result), STATUS: markdown(result).encode()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--living-loop", action="store_true")
    parser.add_argument("--ingest", type=Path)
    parser.add_argument("--origin", default="outside_scheduler")
    args = parser.parse_args()
    if args.ingest:
        freeze_external(args.ingest, args.origin)
        return 0
    if args.living_loop:
        write_living()
    try:
        data = load_json(CORPUS)
        errors = validate(data)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        outputs = expected_outputs(data)
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    if args.write:
        for path, raw in outputs.items():
            (ROOT / path).write_bytes(raw)
    else:
        for path, raw in outputs.items():
            if not (ROOT / path).is_file() or (ROOT / path).read_bytes() != raw:
                print(f"stale generated output: {path}", file=sys.stderr)
                return 1
    result = strict_json_bytes(outputs[OUTPUT], str(OUTPUT))
    print(f"research corpus valid: corpus={result['corpus_sha256']} inventory={result['inventory_sha256']} findings={len(result['normalized_findings'])} leads={result['untrusted_lead_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
