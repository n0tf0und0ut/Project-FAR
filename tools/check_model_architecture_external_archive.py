#!/usr/bin/env python3
"""Post-execution verifier 1.2 for FAR-MAS-EXTERNAL-003 reports and archives.

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
import math
from pathlib import Path
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import model_architecture_external as ex


VERIFICATION_VERSION="1.2"
COMPARATORS={"logistic_regression","rbf_svm","knn5"}
TRIAL_FIELDS=("dataset","scale","steps","family","seed")
SPEC_FIELDS=("family","width","parameters","estimated_forward_macs","parameter_relative_difference",
             "estimated_mac_relative_difference","within_registered_cost_bounds")
REQUIRED={"RESULTS-V0.3.json","RESULTS-V0.3.json.journal.jsonl",
          "model_architecture_external.py","protocol-v0.3.json",
          "preregistration-v0.3.md","test_model_architecture_external.py",
          "v0.3-execution.stdout.log","v0.3-exit-code.txt",
          "v0.3-replay-preflight-import-failure.txt","v0.3-replay-preflight.json",
          "v0.3-replay-full.json","v0.3-replay.stdout.log","v0.3-replay-exit.txt",
          "model_architecture_external_replay.py","check_model_architecture_external_archive.py",
          "test_model_architecture_external_evidence.py","RESULTS-V0.3.md"}


def decode_json(raw):
    def unique(pairs):
        out={}
        for key,value in pairs:
            if key in out:
                raise ValueError("duplicate JSON key: "+key)
            out[key]=value
        return out
    return json.loads(raw,object_pairs_hook=unique)


def _report_matrix(result,p):
    datasets=set(p["datasets"])
    if set(result["datasets"])!=datasets or set(result["simple_baselines"])!=datasets:
        raise ValueError("registered dataset/comparator matrix mismatch")
    expected=[(name,scale,steps,family,seed) for name in p["datasets"] for scale in p["scales"]
              for steps in p["steps_budgets"] for family in p["comparison"] for seed in p["seeds"]]
    keys=[tuple(r[k] for k in TRIAL_FIELDS) for r in result["records"]]
    if ex.canonical(keys)!=ex.canonical(expected):
        raise ValueError("registered neural trial matrix mismatch")
    for name in p["datasets"]:
        desc=result["datasets"][name]
        splits=desc["split_indices"]
        if set(splits)!={"train","validation","test"}:
            raise ValueError("registered cohort matrix mismatch")
        indices=[i for cohort in splits.values() for i in cohort]
        if (type(desc["shape"][0]) is not int or desc["shape"][0]!=len(indices) or
            any(type(i) is not int for i in indices) or sorted(indices)!=list(range(len(indices))) or
            ex.canonical(desc["split_sizes"])!=ex.canonical({k:len(v) for k,v in splits.items()})):
            raise ValueError("cohort partition/count mismatch")
        baselines=result["simple_baselines"][name]
        if set(baselines)!=COMPARATORS:
            raise ValueError("registered comparator matrix mismatch")
        fields={"training_seconds","validation_predictions","validation_metrics","test_predictions","test_metrics"}
        if any(type(v) is not dict or set(v)!=fields for v in baselines.values()):
            raise ValueError("comparator cohort/result fields mismatch")
        neural=[r for r in result["records"] if r["dataset"]==name]
        durations=[v["training_seconds"] for v in baselines.values()]+[r["train_seconds"] for r in neural]
        for value in durations:
            try:
                valid=type(value) in (int,float) and math.isfinite(value) and value>=0
            except OverflowError:
                valid=False
            if not valid:
                raise ValueError("observed training duration must be a finite nonnegative real")
        outcomes=list(baselines.values())+neural
        for outcome in outcomes:
            for split in ("validation","test"):
                predictions=outcome[split+"_predictions"]
                if type(predictions) is not list or len(predictions)!=len(splits[split]):
                    raise ValueError("evaluation cohort prediction count mismatch")
    return dict(zip(expected,result["records"]))


def _journal_matrix(result,p,events,records):
    expected=set(records)
    groups={key[:3] for key in expected}
    started={};trained={};locks={};finished=set();baseline=set()
    for i,e in enumerate(events):
        op=e["event"]
        if op in ("train_started","training_completed","test_completed"):
            row=e if op=="train_started" else e["record_without_test" if op=="training_completed" else "record"]
            key=tuple(row[k] for k in TRIAL_FIELDS)
            if key not in expected:
                raise ValueError("journal trial substitution")
            group=key[:3]
            record=records[key]
            if ex.canonical(key)!=ex.canonical(tuple(record[k] for k in TRIAL_FIELDS)):
                raise ValueError("journal trial identity encoding mismatch")
            if op=="train_started":
                if key in started or ex.canonical(e["spec"])!=ex.canonical({k:record[k] for k in SPEC_FIELDS}):
                    raise ValueError("duplicate/substituted train start")
                started[key]=i
            elif op=="training_completed":
                reduced={k:v for k,v in record.items() if k not in ("test_predictions","test_metrics")}
                if key not in started or started[key]>=i or key in trained or ex.canonical(row)!=ex.canonical(reduced):
                    raise ValueError("training completion identity/order mismatch")
                trained[key]=i
            else:
                if (key in finished or group not in locks or key not in trained or trained[key]>=locks[group] or
                    locks[group]>=i or ex.canonical(row)!=ex.canonical(record)):
                    raise ValueError("test identity/order mismatch")
                finished.add(key)
        elif op=="selection_locked":
            group=(e["dataset"],e["scale"],e["steps"])
            if group not in groups or group in locks or {k for k in trained if k[:3]==group}!={k for k in expected if k[:3]==group}:
                raise ValueError("selection lock before complete registered training matrix")
            averages={family:sum(records[k]["validation_metrics"]["accuracy"] for k in records
                                 if k[:3]==group and k[3]==family)/len(p["seeds"]) for family in p["comparison"]}
            analysis=result["analysis"][f'{group[0]}/width-{group[1]}/steps-{group[2]}']
            if e["selected"]!=analysis["chosen_by_validation"] or ex.canonical(e["average_validation_accuracies"])!=ex.canonical(averages):
                raise ValueError("validation selection evidence mismatch")
            locks[group]=i
        elif op=="simple_baselines_completed":
            name=e["dataset"]
            if name not in p["datasets"] or name in baseline or {k for k in finished if k[0]==name}!={k for k in expected if k[0]==name}:
                raise ValueError("duplicate/substituted/incomplete baseline control event")
            if ex.canonical(e["results"])!=ex.canonical(result["simple_baselines"][name]):
                raise ValueError("journal/report baseline results mismatch")
            baseline.add(name)
        elif op=="start":
            if i!=0:
                raise ValueError("duplicate journal start")
        elif op=="complete":
            if i!=len(events)-1 or ex.canonical(e["records"])!=ex.canonical(len(expected)):
                raise ValueError("journal completion count/order mismatch")
        else:
            raise ValueError("unknown/incomplete journal stage")
    if (set(started)!=expected or set(trained)!=expected or finished!=expected or set(locks)!=groups or
        baseline!=set(p["datasets"]) or events[-1]["event"]!="complete"):
        raise ValueError("journal registered stage matrix incomplete")


def verify_report(result,journal_bytes=None,protocol_bytes=None):
    """Require complete exposure and journal agreement before frozen-score regrading."""
    if journal_bytes is None:
        raise ValueError("current verification requires the original execution journal")
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
    records=_report_matrix(result,p)
    if ex.sha(journal_bytes)!=result["journal_sha256"]:
        raise ValueError("journal checksum invalid")
    events=[decode_json(row) for row in journal_bytes.splitlines()]
    if not events or events[0].get("event")!="start":
        raise ValueError("journal start absent")
    if ex.canonical(events[0].get("environment"))!=ex.canonical(env):
        raise ValueError("journal start environment mismatch")
    if events[0].get("study_id")!=result["study_id"]:
        raise ValueError("journal start study identity mismatch")
    _journal_matrix(result,p,events,records)
    ex.verify(result,journal_bytes)


def parse_archive(raw, require_replay=True):
    # Treat ZIP itself as untrusted. No zip.extract / filesystem writes.
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or any(name.startswith("/") or ".." in Path(name).parts or "\\" in name for name in names):
            raise ValueError("unsafe or duplicate archive members")
        if set(names)!=REQUIRED|{"manifest.json"}:
            raise ValueError("archive missing/extraneous members")
        man=decode_json(z.read("manifest.json"))
        if set(man)!=REQUIRED or any(man[n]!=ex.sha(z.read(n)) for n in REQUIRED):
            raise ValueError("archive member integrity mismatch")
        report=decode_json(z.read("RESULTS-V0.3.json"))
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
        if require_replay:
            full=decode_json(z.read("v0.3-replay-full.json"))
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
        report=decode_json(a.report.read_bytes())
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
