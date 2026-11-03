#!/usr/bin/env python3
"""Post-execution independent *mechanical* replay of FAR-MAS-EXTERNAL-003.

Retrains every recorded model with the frozen source/configuration; not scientific
independence or a replacement experimental trial. Leaves original evidence intact.
"""
from __future__ import annotations
import argparse
import json
import os
import platform
from pathlib import Path
import sys
import traceback

# Running directly from repository root is supported without installing FAR.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import model_architecture_external as ex
from tools import check_model_architecture_external_archive as audit


def replay(result, journal, max_runs=None):
    audit.verify_report(result,journal)
    import numpy as np
    import sklearn
    import torch
    env=result["environment"]
    current={"python":platform.python_version(),"torch":torch.__version__,"numpy":np.__version__,
             "scikit_learn":sklearn.__version__,"device":"cpu"}
    for key,val in current.items():
        if val != env[key]:
            raise ValueError(f"environment mismatch: {key}: {val} != {env[key]}")
    if ex.file_sha(ex.__file__) != env["source_sha256"]:
        raise ValueError("current model source differs from prospectively frozen source")
    if env["threads"] != result["protocol"]["training_threads"]:
        raise ValueError("recorded thread configuration inconsistent")
    torch.set_num_threads(env["threads"])
    if torch.get_num_threads() != env["threads"]:
        raise ValueError("thread configuration cannot be restored")
    torch.use_deterministic_algorithms(True)
    count=0
    observations=[]
    total=len(result["records"])
    for record in result["records"]:
        if max_runs is not None and count>=max_runs:
            break
        name=record["dataset"]
        desc,datasets=ex.read_dataset(name,result["protocol"]["split_seed"])
        ds={"tokens":desc["tokens"],"token_features":desc["token_features"],"classes":desc["classes"],
            "tensors":{k:(torch.from_numpy(x).float(),torch.from_numpy(y).long()) for k,(x,y) in datasets.items()}}
        spec=ex.specs(desc["tokens"],desc["token_features"],desc["classes"],record["scale"],result["protocol"])[record["family"]]
        net,got=ex.train_one(spec,ds,result["protocol"],record["steps"],record["seed"])
        state=ex.fingerprint(net)
        pred=ex.predict(net,ds["tensors"]["test"][0],result["protocol"]["batch_size"])
        if state!=record["checkpoint_sha256"] or got["validation_predictions"]!=record["validation_predictions"] or pred!=record["test_predictions"]:
            raise ValueError(f"model-state or prediction mismatch at slot {count}: {name}/{record['scale']}/{record['steps']}/{record['family']}/{record['seed']}")
        observations.append({"index":count,"key":[name,record["scale"],record["steps"],record["family"],record["seed"]],
                             "checkpoint_sha256":state,"validation_predictions_match":True,"test_predictions_match":True})
        count+=1
    if max_runs is None or max_runs>=total:
        for name in ex.DATASETS:
            desc,data=ex.read_dataset(name,result["protocol"]["split_seed"])
            calculated=ex.reference_baselines(desc,data,result["protocol"]["split_seed"])
            for baseline,values in calculated.items():
                saved=result["simple_baselines"][name][baseline]
                for split in ("test", "validation"):
                    if values[split+"_predictions"]!=saved[split+"_predictions"]:
                        raise ValueError(f"simple comparator reconstruction mismatch: {name}/{baseline}/{split}")
        status="FULL_MATCH"
    else:
        status="PREFLIGHT_PARTIAL_MATCH_NOT_FULL_REPLICATION"
    return {"status":status,"study_id":result["study_id"],"n_replayed":count,"n_expected":total,
            "source_sha256":env["source_sha256"],"original_report_sha256":result["report_sha256"],
            "original_journal_sha256":result["journal_sha256"],"threads_restored":torch.get_num_threads(),
            "records":observations,
            "disclaimer":"same-runtime deterministic reconstruction, not independent scientific replication"}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--journal",type=Path,required=True)
    p.add_argument("--receipt",type=Path,required=True)
    p.add_argument("--preflight-runs",type=int,default=None)
    args=p.parse_args()
    if args.receipt.exists() or Path(str(args.receipt)+".failure.json").exists():
        raise FileExistsError("immutable replay receipt exists")
    original=json.loads(args.report.read_text())
    original_journal=args.journal.read_bytes()
    try:
        out=replay(original,original_journal,max_runs=args.preflight_runs)
        ex.write_once(args.receipt,ex.canonical(out)+b"\n")
        print("REPLAY",out["status"],out["n_replayed"],"/",out["n_expected"])
    except Exception as err:
        ex.write_once(Path(str(args.receipt)+".failure.json"),ex.canonical({"status":"REPLAY_FAILED","error":str(err),
             "error_type":type(err).__name__,"traceback":traceback.format_exc()[-2000:]})+b"\n")
        raise


if __name__=="__main__":
    main()
