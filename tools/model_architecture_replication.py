#!/usr/bin/env python3
"""Registered matched-capacity replication of FAR-MAS-PILOT-001.

Uses the existing frozen MAS v0.1 model definitions, without changing them.
No model-generated Python or remote services. This is research, not product code.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import platform
import sys
import time
import traceback
from pathlib import Path

import model_architecture_search as mas

VERSION = "far-mas-matched-replication/0.2"
OPS = {
    "stacked-attn": ("attn", "attn"),
    "wide-attn": ("attn",),
    "wide-gru": ("gru",),
    "wide-conv": ("conv",),
}


def encode(x):
    return mas.encoded(x)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def atomic_create(path, raw):
    path = Path(path)
    with path.open("xb") as out:
        out.write(raw)
        out.flush()
        os.fsync(out.fileno())


def event(path, data):
    with path.open("ab") as out:
        out.write(encode({"time": dt.datetime.now(dt.timezone.utc).isoformat(), **data})+b"\n")
        out.flush()
        os.fsync(out.fileno())


def protocol_check(p):
    fields = {"version", "study_id", "model_source_sha256", "data_seed", "lengths",
              "train_size", "validation_size", "test_size", "width_baseline", "width_limits",
              "batch_size", "steps_budgets", "seeds", "learning_rate", "conditions",
              "primary_metric", "acceptance", "device"}
    if type(p) is not dict or set(p) != fields or p["version"] != VERSION or p["device"] != "cpu":
        raise ValueError("unrecognized protocol")
    if type(p["model_source_sha256"]) is not str or len(p["model_source_sha256"]) != 64:
        raise ValueError("invalid source binding")
    if type(p["study_id"]) is not str or not p["study_id"].strip():
        raise ValueError("study id required")
    if type(p["data_seed"]) is not int or p["data_seed"] < 0:
        raise ValueError("bad data seed")
    if type(p["lengths"]) is not list or len(p["lengths"]) != 2 or len(set(p["lengths"])) != 2 or any(type(x) is not int or x < 7 or x > 20 for x in p["lengths"]):
        raise ValueError("two distinct lengths required")
    if type(p["width_baseline"]) is not int or p["width_baseline"] < 8:
        raise ValueError("bad base width")
    limits=p["width_limits"]
    if type(limits) is not list or len(limits) != 2 or any(type(x) is not int for x in limits) or limits[0] < 8 or limits[1] > 128 or limits[0] >= limits[1]:
        raise ValueError("bad width limits")
    for key in ("train_size", "validation_size", "test_size", "batch_size"):
        if type(p[key]) is not int or not 1 <= p[key] <= 65536:
            raise ValueError("invalid count: "+key)
    if p["batch_size"] > p["train_size"] or p["test_size"] < 30:
        raise ValueError("invalid batch/evaluation count")
    if sum(p[x] for x in ("train_size", "validation_size", "test_size")) > 2**min(p["lengths"]):
        raise ValueError("insufficient unique sequences")
    if (type(p["steps_budgets"]) is not list or len(p["steps_budgets"]) != 2 or
        len(set(p["steps_budgets"])) != 2 or any(type(x) is not int or x < 1 or x > 3000 for x in p["steps_budgets"])):
        raise ValueError("two distinct fixed training budgets required")
    if (type(p["seeds"]) is not list or len(p["seeds"]) != 5 or
        len(set(p["seeds"])) != 5 or any(type(x) is not int or x < 0 or x >= 2**31 for x in p["seeds"])):
        raise ValueError("five common seeds required")
    if type(p["learning_rate"]) not in (int,float) or not math.isfinite(p["learning_rate"]) or not 0 < p["learning_rate"] <= .1:
        raise ValueError("bad LR")
    if p["conditions"] != list(OPS) or p["primary_metric"] != "held_out_macro_accuracy":
        raise ValueError("condition or metric drift")
    a=p["acceptance"]
    if set(a) != {"primary_length", "primary_steps", "min_mean_gain", "min_positive_paired_seeds", "min_task_gain"} or a["primary_length"] not in p["lengths"] or a["primary_steps"] not in p["steps_budgets"]:
        raise ValueError("invalid preregistered primary")
    if type(a["min_mean_gain"]) not in (float,int) or not 0 <= a["min_mean_gain"] < .5 or type(a["min_task_gain"]) not in (float,int) or not -.5 <= a["min_task_gain"] <= 0 or type(a["min_positive_paired_seeds"]) is not int or not 1 <= a["min_positive_paired_seeds"] <= 5:
        raise ValueError("invalid gate")
    return p


def model_specs(p, length):
    import torch
    target=sum(x.numel() for x in mas.make_model(OPS["stacked-attn"],p["width_baseline"],length).parameters())
    out=[]
    for condition,ops in OPS.items():
        if condition == "stacked-attn":
            width=p["width_baseline"]
        else:
            width=min(range(p["width_limits"][0],p["width_limits"][1]+1),
                      key=lambda w: (abs(sum(t.numel() for t in mas.make_model(ops,w,length).parameters())-target),w))
        params=sum(x.numel() for x in mas.make_model(ops,width,length).parameters())
        out.append({"id":condition,"recipe":list(ops),"width":width,"parameters":params,
                    "difference_from_stacked_fraction":(params-target)/target})
    return out


def splits(p,length):
    import random
    size=sum(p[k] for k in ("train_size","validation_size","test_size"))
    items=random.Random(p["data_seed"]+length).sample(range(2**length),size)
    a,b=p["train_size"],p["validation_size"]
    return {"train":items[:a],"validation":items[a:a+b],"test":items[a+b:]}


def bitpack(numbers):
    return bytes(sum((int(b) << (7-(i%8))) for i,b in enumerate(numbers[j:j+8])) for j in range(0,len(numbers),8)).hex()


def bitunpack(value,n):
    try:
        raw=bytes.fromhex(value)
    except (ValueError,TypeError):
        raise ValueError("invalid packed predictions") from None
    if len(raw) != (n+7)//8 or (n%8 and raw[-1] & ((1 << (8-n%8))-1)):
        raise ValueError("noncanonical packed prediction length/padding")
    return [bool(raw[i//8] & (1 << (7-i%8))) for i in range(n)]


def tensor_fingerprint(model):
    import torch
    digest=hashlib.sha256()
    with torch.no_grad():
        for name,t in sorted(model.state_dict().items()):
            cpu=t.detach().contiguous().cpu()
            digest.update(name.encode()+b"\x00")
            digest.update(str(tuple(cpu.shape)).encode()+b"\x00")
            digest.update(str(cpu.dtype).encode()+b"\x00")
            digest.update(cpu.numpy().tobytes())
    return digest.hexdigest()


def predict_all(model, dataset, batch_size):
    import torch
    x,t,y=dataset
    model.eval()
    results=[]
    with torch.inference_mode():
        for begin in range(0,len(x),batch_size):
            results.extend(int(v) for v in model(x[begin:begin+batch_size],t[begin:begin+batch_size]).argmax(-1))
    return results


def fit(spec,p,length,steps,seed,ds):
    import torch
    from torch.nn import functional as F
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    model=mas.make_model(spec["recipe"],spec["width"],length)
    optimizer=torch.optim.AdamW(model.parameters(),lr=p["learning_rate"],weight_decay=.01)
    x,t,y=ds["train"]
    generator=torch.Generator().manual_seed(seed+314159)
    start=time.monotonic()
    for _ in range(steps):
        model.train()
        ix=torch.randint(len(x),(p["batch_size"],),generator=generator)
        optimizer.zero_grad(set_to_none=True)
        loss=F.cross_entropy(model(x[ix],t[ix]),y[ix])
        if not bool(torch.isfinite(loss)):
            raise RuntimeError("nonfinite training loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
        optimizer.step()
    results={"condition":spec["id"],"recipe":spec["recipe"],"width":spec["width"],
             "parameters":spec["parameters"],"length":length,"steps":steps,"seed":seed,
             "weight_sha256":tensor_fingerprint(model),"train_seconds":round(time.monotonic()-start,5)}
    for split in ("validation","test"):
        pred=predict_all(model,ds[split],p["batch_size"])
        metrics=mas.evaluate(model,ds[split],p["batch_size"])
        results[split] = {"metrics":metrics,"predictions_bits":bitpack(pred)}
    return results


def report_metrics(records,p):
    a=p["acceptance"]
    selected=[r for r in records if r["length"]==a["primary_length"] and r["steps"]==a["primary_steps"]]
    grouped={name:{r["seed"]:r for r in selected if r["condition"]==name} for name in OPS}
    if any(set(v)!=set(p["seeds"]) for v in grouped.values()):
        raise ValueError("incomplete primary comparison")
    pairs=[]
    for seed in p["seeds"]:
        r=grouped["stacked-attn"][seed]["test"]["metrics"]
        c=grouped["wide-attn"][seed]["test"]["metrics"]
        pairs.append(r["macro_accuracy"]-c["macro_accuracy"])
    gain=sum(pairs)/len(pairs)
    task_deltas={name:sum(grouped["stacked-attn"][s]["test"]["metrics"]["by_task"][name]["accuracy"]-
                           grouped["wide-attn"][s]["test"]["metrics"]["by_task"][name]["accuracy"] for s in p["seeds"])/len(p["seeds"])
                 for name in mas.TASKS}
    passed=(gain>=a["min_mean_gain"] and sum(d>0 for d in pairs)>=a["min_positive_paired_seeds"] and min(task_deltas.values())>=a["min_task_gain"])
    return {"primary_gain":gain,"paired_seed_gains":pairs,"positive_seed_count":sum(d>0 for d in pairs),
            "mean_per_family_gains":task_deltas,"predeclared_screen_passed":passed,
            "screen_is_not_scientific_significance_or_general_reliability":True}


def run(p, destination, protocol_raw):
    import torch
    protocol_check(p)
    if sha(Path(mas.__file__).read_bytes())!=p["model_source_sha256"]:
        raise ValueError("original model implementation does not match frozen identity")
    destination=Path(destination)
    journal=Path(str(destination)+".journal.jsonl")
    failure=Path(str(destination)+".failure.json")
    if any(x.exists() for x in (destination,journal,failure)):
        raise FileExistsError("existing result or failed attempt: no replacement allowed")
    destination.parent.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(1)
    started={"protocol_sha256":sha(protocol_raw),"replication_source_sha256":sha(Path(__file__).read_bytes()),
             "model_source_sha256":p["model_source_sha256"],"study_id":p["study_id"]}
    event(journal,{"event":"started",**started})
    completed=[]
    try:
        all_splits={}
        for length in p["lengths"]:
            groups=splits(p,length)
            all_splits[str(length)]=sha(encode(groups))
            if sum(map(len,groups.values()))!=len(set(sum(groups.values(),[]))):
                raise ValueError("split overlap")
            ds={k:mas.make_dataset(v,{"sequence_length":length}) for k,v in groups.items()}
            for steps in p["steps_budgets"]:
                for spec in model_specs(p,length):
                    for seed in p["seeds"]:
                        key={"length":length,"steps":steps,"condition":spec["id"],"seed":seed}
                        event(journal,{"event":"attempt_started",**key})
                        rec=fit(spec,p,length,steps,seed,ds)
                        completed.append(rec)
                        event(journal,{"event":"attempt_completed","record":rec})
        analysis=report_metrics(completed,p)
        event(journal,{"event":"finished","analysis":analysis})
        report={"status":"COMPLETE_RESEARCH_REPLICATION","protocol":p,**started,"split_sha256":all_splits,
                "environment":{"torch":torch.__version__,"python":platform.python_version(),"platform":platform.platform(),"threads":torch.get_num_threads()},
                "records":completed,"analysis":analysis,"journal_sha256":sha(journal.read_bytes()),
                "scope":"fixed known operators, authored binary tasks, CPU steps-matched; no architecture invention, no external generalization"}
        report["report_sha256"]=sha(encode(report))
        atomic_create(destination,encode(report)+b"\n")
        return report
    except BaseException as exc:
        event(journal,{"event":"failed","error":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()[-1500:]})
        atomic_create(failure,encode({"status":"FAILED_OR_INCOMPLETE",**started,"completed":completed,
                                      "error":str(exc),"journal_sha256":sha(journal.read_bytes())})+b"\n")
        raise


def validate_report(report, journal=None, replay=False):
    import torch
    if report["status"]!="COMPLETE_RESEARCH_REPLICATION" or report["report_sha256"]!=sha(encode({k:v for k,v in report.items() if k!="report_sha256"})):
        raise ValueError("report digest or status mismatch")
    p=protocol_check(report["protocol"])
    if report["protocol_sha256"]!=sha(encode(p)+b"\n"):
        raise ValueError("protocol SHA mismatch")
    if report["model_source_sha256"]!=p["model_source_sha256"]:
        raise ValueError("model source identity mismatch")
    if replay and (report["replication_source_sha256"]!=sha(Path(__file__).read_bytes()) or report["model_source_sha256"]!=sha(Path(mas.__file__).read_bytes())):
        raise ValueError("source changed since execution")
    expected=[]
    all_splits={}
    for length in p["lengths"]:
        split=splits(p,length)
        all_splits[str(length)]=sha(encode(split))
        ds={k:mas.make_dataset(v,{"sequence_length":length}) for k,v in split.items()}
        for steps in p["steps_budgets"]:
            for spec in model_specs(p,length):
                for seed in p["seeds"]:
                    expected.append((length,steps,spec,seed,ds))
    if all_splits!=report["split_sha256"] or len(expected)!=len(report["records"]):
        raise ValueError("missing or altered split / run")
    for r,(length,steps,spec,seed,ds) in zip(report["records"],expected):
        if any((r[key]!=val for key,val in {"condition":spec["id"],"recipe":spec["recipe"],"width":spec["width"],"parameters":spec["parameters"],"length":length,"steps":steps,"seed":seed}.items())):
            raise ValueError("model coverage / identity drift")
        for split in ("validation","test"):
            x,t,y=ds[split]
            bits=bitunpack(r[split]["predictions_bits"],len(x))
            counts=[]
            for i,name in enumerate(mas.TASKS):
                ix=[j for j,c in enumerate(t.tolist()) if c==i]
                counts.append({"correct":sum(int(bits[j])==int(y[j]) for j in ix),"count":len(ix)})
                claimed=r[split]["metrics"]["by_task"][name]
                if claimed["correct"]!=counts[-1]["correct"] or claimed["count"]!=len(ix) or abs(claimed["accuracy"]-counts[-1]["correct"]/len(ix))>1e-12:
                    raise ValueError("predictions inconsistent with task metrics")
            mac=sum(c["correct"]/c["count"] for c in counts)/3
            mic=sum(c["correct"] for c in counts)/len(x)
            if abs(r[split]["metrics"]["macro_accuracy"]-mac)>1e-12 or abs(r[split]["metrics"]["micro_accuracy"]-mic)>1e-12:
                raise ValueError("macro/micro scores not supported by predictions")
        if replay:
            actual=fit(spec,p,length,steps,seed,ds)
            if actual["weight_sha256"]!=r["weight_sha256"] or any(actual[s]["predictions_bits"]!=r[s]["predictions_bits"] for s in ("validation","test")):
                raise ValueError("exact deterministic training replay mismatch")
    if report_metrics(report["records"],p)!=report["analysis"]:
        raise ValueError("analysis mismatch")
    if journal is not None:
        if report["journal_sha256"]!=sha(journal):
            raise ValueError("journal SHA mismatch")
        entries=[json.loads(line) for line in journal.splitlines()]
        if len([e for e in entries if e["event"]=="attempt_started"])!=len(expected) or [e["record"] for e in entries if e["event"]=="attempt_completed"]!=report["records"] or entries[0]["event"]!="started" or entries[-1]["event"]!="finished":
            raise ValueError("journal coverage mismatch")


def main():
    arg=argparse.ArgumentParser(description=__doc__)
    cmd=arg.add_subparsers(dest="command",required=True)
    cp=cmd.add_parser("check-protocol")
    cp.add_argument("--protocol",required=True,type=Path)
    rp=cmd.add_parser("run")
    rp.add_argument("--protocol",required=True,type=Path)
    rp.add_argument("--out",required=True,type=Path)
    vp=cmd.add_parser("verify")
    vp.add_argument("--report",required=True,type=Path)
    vp.add_argument("--journal",type=Path)
    vp.add_argument("--replay",action="store_true")
    a=arg.parse_args()
    if a.command in ("check-protocol","run"):
        raw=a.protocol.read_bytes()
        p=protocol_check(json.loads(raw))
        if raw!=encode(p)+b"\n":
            raise ValueError("protocol must be canonical JSON + one LF")
        if a.command=="check-protocol":
            print("valid preregistration",sha(raw))
        else:
            res=run(p,a.out,raw)
            validate_report(res,Path(str(a.out)+".journal.jsonl").read_bytes())
            print(json.dumps(res["analysis"],indent=2))
    else:
        res=json.loads(a.report.read_text())
        validate_report(res,a.journal.read_bytes() if a.journal else None,a.replay)
        print("validated",res["study_id"],len(res["records"]),"records")

if __name__=="__main__":
    main()
