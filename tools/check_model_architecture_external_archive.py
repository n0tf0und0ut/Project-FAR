#!/usr/bin/env python3
"""Cold-reconstruct original FAR-MAS-EXTERNAL-003 evidence and event ordering.

Optional scikit-learn is required for actual outcome regrading; archive digest
checks operate without PyTorch. Untrusted archive members are never extracted.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import model_architecture_external as ex


REQUIRED={"RESULTS-V0.3.json","RESULTS-V0.3.json.journal.jsonl",
          "model_architecture_external.py","protocol-v0.3.json",
          "preregistration-v0.3.md","test_model_architecture_external.py",
          "v0.3-execution.stdout.log","v0.3-exit-code.txt",
          "v0.3-replay-preflight-import-failure.txt","v0.3-replay-preflight.json",
          "v0.3-replay-full.json","v0.3-replay.stdout.log","v0.3-replay-exit.txt",
          "model_architecture_external_replay.py","check_model_architecture_external_archive.py",
          "test_model_architecture_external_evidence.py","RESULTS-V0.3.md"}


def parse_archive(raw, require_replay=True):
    # Treat ZIP itself as untrusted. No zip.extract / filesystem writes.
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or any(name.startswith("/") or ".." in Path(name).parts or "\\" in name for name in names):
            raise ValueError("unsafe or duplicate archive members")
        if set(names)!=REQUIRED|{"manifest.json"}:
            raise ValueError("archive missing/extraneous members")
        man=json.loads(z.read("manifest.json"))
        if set(man)!=REQUIRED or any(man[n]!=ex.sha(z.read(n)) for n in REQUIRED):
            raise ValueError("archive member integrity mismatch")
        report=json.loads(z.read("RESULTS-V0.3.json"))
        journal=z.read("RESULTS-V0.3.json.journal.jsonl")
        if z.read("model_architecture_external.py")!=Path(ex.__file__).read_bytes():
            raise ValueError("local verifier source differs from archived frozen model")
        if ex.sha(z.read("model_architecture_external.py"))!=report["environment"]["source_sha256"]:
            raise ValueError("source not bound to report")
        if ex.sha(z.read("protocol-v0.3.json"))!=report["environment"]["protocol_sha256"]:
            raise ValueError("registered protocol not bound to original result")
        if z.read("v0.3-exit-code.txt").strip()!=b"0":
            raise ValueError("original run did not exit successfully")
        ex.verify(report,journal)
        events=[json.loads(x) for x in journal.splitlines()]
        started={}
        trained={}
        locks={}
        finished=set()
        baseline=set()
        for i,e in enumerate(events):
            op=e["event"]
            if op in ("train_started","training_completed","test_completed"):
                k=(e.get("dataset"),e.get("scale"),e.get("steps"),e.get("family"),e.get("seed")) if op=="train_started" else tuple(e["record_without_test" if op=="training_completed" else "record"][x] for x in ("dataset","scale","steps","family","seed"))
                group=k[:3]
                if op=="train_started":
                    if k in started:
                        raise ValueError("duplicate train start")
                    started[k]=i
                elif op=="training_completed":
                    if k not in started or started[k]>=i or k in trained:
                        raise ValueError("training ended without unique earlier start")
                    trained[k]=(i,e["record_without_test"])
                else:
                    if k in finished or group not in locks or k not in trained or trained[k][0]>=locks[group] or locks[group]>=i:
                        raise ValueError("test occurred before source training or validation lock")
                    reduced={key:value for key,value in e["record"].items() if key not in ("test_predictions","test_metrics")}
                    if reduced!=trained[k][1]:
                        raise ValueError("unverified training/test record correspondence")
                    finished.add(k)
            elif op=="selection_locked":
                group=(e["dataset"],e["scale"],e["steps"])
                if group in locks or len([k for k in trained if k[:3]==group])!=12:
                    raise ValueError("selection was not after all candidate trainings")
                locks[group]=i
            elif op=="simple_baselines_completed":
                if e["dataset"] in baseline or len([k for k in finished if k[0]==e["dataset"]])!=48:
                    raise ValueError("simple controls published before neural evaluation completed")
                baseline.add(e["dataset"])
        # chronological constraints: since locks stored as a set, track their ordinals separately
        if len(started)!=96 or len(trained)!=96 or len(finished)!=96 or len(locks)!=8 or baseline!=set(ex.DATASETS):
            raise ValueError("journal stage coverage incomplete")
        if require_replay:
            full=json.loads(z.read("v0.3-replay-full.json"))
            if (full["status"]!="FULL_MATCH" or full["n_replayed"]!=96 or full["n_expected"]!=96 or
                full["original_report_sha256"]!=report["report_sha256"] or
                full["original_journal_sha256"]!=report["journal_sha256"]):
                raise ValueError("saved deterministic replay did not cover all original trials")
        return {"study_id":report["study_id"],"n_scored":len(report["records"]),
                "original_report_sha256":report["report_sha256"],
                "original_journal_sha256":report["journal_sha256"],
                "primary_pass":report["analysis"]["primary_screen"]["passes_both"],
                "full_replay_receipt":require_replay}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--expected-sha256",type=str)
    a=p.parse_args()
    raw=base64.b64decode(a.archive.read_bytes(),validate=False)
    if a.expected_sha256 and ex.sha(raw)!=a.expected_sha256:
        raise ValueError("archive outer SHA-256 mismatch")
    print(json.dumps(parse_archive(raw),sort_keys=True,indent=2))

if __name__=="__main__":
    main()
