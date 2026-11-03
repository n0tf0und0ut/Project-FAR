"""Verify the published pilot archive without downloads, extraction or inference.

This checks retained bytes, frozen-source identity, slot accounting and grades.
Tokenizer/checkpoint replay and independent model regeneration remain separate.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

from tools.weight_space_pilot import ROOT, canonical, read, sha, schedule, source_receipt
from tools.weight_space_replay import independent_grade, summarize

DEFAULT = ROOT / "research/weight-space/results/smol135m-v01-manifest.json"


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def check(manifest_path=DEFAULT):
    manifest = read(manifest_path)
    archive = manifest["archive"]
    path = ROOT / archive["path"]
    data = path.read_bytes()
    if len(data) != archive["size"] or sha(data) != archive["sha256"]:
        raise ValueError("archive bytes differ from publication commitment")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or len(names) != archive["members"]:
            raise ValueError("duplicate or incorrect archive member count")
        for name in names:
            p = PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts or str(p) != name or "\\" in name:
                raise ValueError("noncanonical archive member")
        inner = strict_json(z.read("manifest.json"))
        if inner != {k: v for k, v in manifest.items() if k != "archive"}:
            raise ValueError("inner and published manifests differ")
        entries = inner["files"]
        expected = [e["path"] for e in entries]
        if len(expected) != len(set(expected)) or set(names) != set(expected) | {"manifest.json"}:
            raise ValueError("missing, extra or duplicate manifest file")
        for entry in entries:
            content = z.read(entry["path"])
            if len(content) != entry["size"] or sha(content) != entry["sha256"]:
                raise ValueError("archive member bytes differ: " + entry["path"])
        revision = inner["frozen_source_commit"]
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError("invalid frozen source identity")
        reg = strict_json(z.read("attempt/registration.json"))
        if reg["source_commit"] != revision or reg["observations"] != "LIVE_PRETRAINED_MODEL":
            raise ValueError("registration identity mismatch")
        protocol_path = ROOT / "research/weight-space/protocol-v0.1.json"
        protocol = read(protocol_path)
        source = source_receipt(protocol, protocol_path)
        if source != reg["source_files"] or sha(protocol_path.read_bytes()) != reg["protocol_sha256"]:
            raise ValueError("working source differs from measured source")
        for name, digest in source.items():
            committed = subprocess.check_output(["git", "show", revision + ":" + name], cwd=ROOT)
            if sha(committed) != digest:
                raise ValueError("frozen source byte mismatch")
        tasks = read(ROOT / protocol["tasks"]["path"])
        expected_slots = schedule(protocol, tasks)
        slot_names = {f"attempt/slot-{i:04d}.json" for i in range(len(expected_slots))}
        if slot_names != {n for n in names if n.startswith("attempt/slot-")}:
            raise ValueError("incomplete or extra scored slots")
        if any(n.startswith("attempt/failure-") for n in names):
            raise ValueError("failed attempt cannot be a completed publication")
        completion = strict_json(z.read("attempt/completion.json"))
        if completion["completed_slots"] != len(expected_slots):
            raise ValueError("completion slot count differs")
        lookup = {t["id"]: t for t in tasks}
        rows = []
        for i, slot in enumerate(expected_slots):
            row = strict_json(z.read(f"attempt/slot-{i:04d}.json"))
            if row["index"] != i or (row["task_id"], row["seed"], row["arm"]) != slot:
                raise ValueError("slot identity mismatch")
            if row["text_sha256"] != sha(row["text"].encode()):
                raise ValueError("text commitment mismatch")
            task = lookup[row["task_id"]]
            if row["grade"] != independent_grade(task, row["text"], row["output_ids"], row["hit_token_limit"]):
                raise ValueError("grade differs from raw output")
            rows.append(row)
        development = []
        for task in tasks:
            if task["split"] == "development":
                row = strict_json(z.read("attempt/development-" + task["id"] + ".json"))
                if row["grade"] != independent_grade(task, row["text"], row["output_ids"], row["hit_token_limit"]):
                    raise ValueError("development grade differs")
                development.append(row)
        counts = inner["new_model_observations"]
        if (counts["scored_generations"] != len(rows) or
                counts["development_generations"] != len(development) or
                inner["actual_raw_files"] != sum(n.startswith("attempt/") for n in names)):
            raise ValueError("publication counts differ from archive")
        computed = summarize(protocol, tasks, rows)
        # CPython 3.12 changed float sum(). Reconstruct cost totals with explicit
        # correctly rounded summation on every Python version. Keep every grade,
        # integer count, statistical result and recorded evidence byte exact.
        for arm in protocol["arms"]:
            arm_rows = [r for r in rows if r["arm"] == arm]
            computed["arms"][arm]["cpu_seconds"] = math.fsum(r["cpu_seconds"] for r in arm_rows)
            computed["arms"][arm]["generation_seconds"] = math.fsum(r["elapsed_seconds"] for r in arm_rows)
        recorded = strict_json(z.read("attempt/analysis.json"))
        published = read(manifest_path.with_name("smol135m-v01-analysis.json"))
        if recorded != published or any(recorded.get(k) != v for k, v in computed.items()):
            raise ValueError("published analysis differs from reconstructed grades")
        loops = sum(r["grade"]["repeated_suffix"] for r in development)
        if recorded["development"] != {"total": len(development),
                "correct": sum(r["grade"]["correct"] for r in development),
                "repetition_proxy_count": loops} or recorded["WSP_HLOOP"]["testable"] != (loops >= 2):
            raise ValueError("development testability mismatch")
    return {"status": "PUBLICATION_CONSISTENCY_VERIFIED", "archive_sha256": sha(data),
            "source_commit": revision, "members_verified": len(names),
            "scored_records_regraded": len(rows), "development_records_regraded": len(development),
            "new_model_observations": 0, "checkpoint_tokenizer_replay": "SEPARATE_CHECK",
            "independent_model_regeneration": "NOT_PERFORMED", "production_eligible": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT)
    print(json.dumps(check(parser.parse_args().manifest), indent=2))
