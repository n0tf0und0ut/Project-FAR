#!/usr/bin/env python3
"""Post-execution verifier 1.1 for FAR-MAS-EXTERNAL-003 reports and archives.

Optional scikit-learn is required for actual outcome regrading; archive digest
checks operate without PyTorch. The prospectively frozen runner stays unchanged.
Untrusted archive members are never extracted. Internal consistency is not an
external attestation that an operator's fully coordinated history is truthful.
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


VERIFICATION_VERSION="1.1"
REQUIRED={"RESULTS-V0.3.json","RESULTS-V0.3.json.journal.jsonl",
          "model_architecture_external.py","protocol-v0.3.json",
          "preregistration-v0.3.md","test_model_architecture_external.py",
          "v0.3-execution.stdout.log","v0.3-exit-code.txt",
          "v0.3-replay-preflight-import-failure.txt","v0.3-replay-preflight.json",
          "v0.3-replay-full.json","v0.3-replay.stdout.log","v0.3-replay-exit.txt",
          "model_architecture_external_replay.py","check_model_architecture_external_archive.py",
          "test_model_architecture_external_evidence.py","RESULTS-V0.3.md"}


def verify_report(result,journal_bytes=None,protocol_bytes=None):
    """Bind duplicated configuration before invoking the frozen score verifier."""
    p=ex.check(result["protocol"])
    raw=ex.canonical(p)+b"\n"
    env=result["environment"]
    if ex.sha(raw)!=env["protocol_sha256"]:
        raise ValueError("embedded protocol digest mismatch")
    if protocol_bytes is not None and raw!=protocol_bytes:
        raise ValueError("embedded protocol differs from registered protocol")
    if result["study_id"]!=p["study_id"]:
        raise ValueError("report/protocol study identity mismatch")
    if ex.canonical([env["device"],env["threads"]])!=ex.canonical([p["device"],p["training_threads"]]):
        raise ValueError("recorded execution configuration mismatch")
    if env["source_sha256"]!=p["precommit_source_sha256"] or env["source_sha256"]!=ex.file_sha(ex.__file__):
        raise ValueError("frozen execution source mismatch")
    if journal_bytes is not None:
        if ex.sha(journal_bytes)!=result["journal_sha256"]:
            raise ValueError("journal checksum invalid")
        events=[json.loads(row) for row in journal_bytes.splitlines()]
        if not events or events[0].get("event")!="start":
            raise ValueError("journal start absent")
        if ex.canonical(events[0].get("environment"))!=ex.canonical(env):
            raise ValueError("journal start environment mismatch")
        if events[0].get("study_id")!=result["study_id"]:
            raise ValueError("journal start study identity mismatch")
    ex.verify(result,journal_bytes)


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
        verify_report(report,journal,z.read("protocol-v0.3.json"))
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
                full["original_journal_sha256"]!=report["journal_sha256"] or
                full["study_id"]!=report["study_id"] or
                full["source_sha256"]!=report["environment"]["source_sha256"] or
                ex.canonical(full["threads_restored"])!=ex.canonical(report["environment"]["threads"])):
                raise ValueError("saved deterministic replay did not cover all original trials")
            expected=[{"index":i,"key":[record[k] for k in ("dataset","scale","steps","family","seed")],
                       "checkpoint_sha256":record["checkpoint_sha256"],
                       "validation_predictions_match":True,"test_predictions_match":True}
                      for i,record in enumerate(report["records"])]
            if ex.canonical(full["records"])!=ex.canonical(expected):
                raise ValueError("saved replay trial identities or coverage mismatch")
        return {"study_id":report["study_id"],"n_scored":len(report["records"]),
                "original_report_sha256":report["report_sha256"],
                "original_journal_sha256":report["journal_sha256"],
                "primary_pass":report["analysis"]["primary_screen"]["passes_both"],
                "full_replay_receipt":require_replay}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    inputs=p.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--archive",type=Path)
    inputs.add_argument("--report",type=Path)
    p.add_argument("--journal",type=Path)
    p.add_argument("--protocol",type=Path)
    p.add_argument("--expected-sha256",type=str)
    a=p.parse_args()
    if a.report:
        if not a.journal or a.expected_sha256:
            p.error("--report requires --journal; --expected-sha256 applies only to --archive")
        report=json.loads(a.report.read_bytes())
        verify_report(report,a.journal.read_bytes(),a.protocol.read_bytes() if a.protocol else None)
        print(json.dumps({"verification_version":VERIFICATION_VERSION,"study_id":report["study_id"],
                          "n_scored":len(report["records"]),"original_report_sha256":report["report_sha256"]},sort_keys=True))
        return
    if a.journal or a.protocol:
        p.error("--journal and --protocol apply only to --report")
    raw=base64.b64decode(a.archive.read_bytes(),validate=False)
    if a.expected_sha256 and ex.sha(raw)!=a.expected_sha256:
        raise ValueError("archive outer SHA-256 mismatch")
    print(json.dumps(parse_archive(raw),sort_keys=True,indent=2))

if __name__=="__main__":
    main()
