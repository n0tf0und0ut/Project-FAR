#!/usr/bin/env python3
"""Bounded research-only neural architecture search with retained evidence.

PyTorch is required for experiments but is not a FAR package dependency.
No generated arbitrary Python, model-provider claims, or production changes.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import itertools
import json
import math
import os
import platform
import random
import time
import traceback
from pathlib import Path

TASKS = ("remember_first", "xor_endpoints", "majority")
OPS = ("attn", "gru", "conv")
BASES = (("identity",), ("attn",), ("gru",), ("conv",))
VERSION = "far-model-architecture-search/0.1"


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def identity(recipe):
    return "+".join(recipe)


def validate_recipe(r, max_blocks):
    if not isinstance(r, (tuple, list)) or not 1 <= len(r) <= max_blocks:
        raise ValueError("invalid recipe length")
    if tuple(r) == ("identity",):
        return ("identity",)
    if any(type(v) is not str or v not in OPS for v in r):
        raise ValueError("unknown mixer")
    return tuple(r)


def positive(p, key, lo, hi):
    v = p[key]
    if type(v) is not int or not lo <= v <= hi:
        raise ValueError(f"{key} must be integer in {lo}..{hi}")
    return v


def validate_protocol(p):
    required = {"version", "study_id", "search_seed", "data_seed", "sequence_length",
                "train_size", "validation_size", "test_size", "width", "steps",
                "batch_size", "learning_rate", "max_candidates", "max_blocks",
                "selection_train_seed", "final_train_seeds", "tasks", "device"}
    if type(p) is not dict or set(p) != required:
        raise ValueError("protocol field set mismatch")
    if p["version"] != VERSION or p["device"] != "cpu" or p["tasks"] != list(TASKS):
        raise ValueError("unsupported protocol version, device, or task family")
    if type(p["study_id"]) is not str or not p["study_id"].strip():
        raise ValueError("study id required")
    for k in ("search_seed", "data_seed", "selection_train_seed"):
        positive(p, k, 0, 2**31 - 1)
    n = positive(p, "sequence_length", 7, 20)
    sizes = [positive(p, k, 16, 65536) for k in ("train_size", "validation_size", "test_size")]
    if sum(sizes) > 2**n:
        raise ValueError("not enough distinct binary sequences for disjoint splits")
    positive(p, "width", 8, 128)
    positive(p, "steps", 1, 3000)
    positive(p, "batch_size", 1, sizes[0])
    positive(p, "max_blocks", 2, 4)
    positive(p, "max_candidates", 4, 24)
    if p["max_candidates"] > 1 + sum(len(OPS)**i for i in range(1, p["max_blocks"]+1)):
        raise ValueError("search budget exceeds operator search space")
    if type(p["learning_rate"]) not in (int, float) or not math.isfinite(p["learning_rate"]) or not 0 < p["learning_rate"] <= 0.1:
        raise ValueError("invalid learning rate")
    seeds = p["final_train_seeds"]
    if type(seeds) is not list or not 2 <= len(seeds) <= 10 or len(set(map(str, seeds))) != len(seeds):
        raise ValueError("final seeds must be 2..10 distinct integers")
    for seed in seeds:
        if type(seed) is not int or not 0 <= seed <= 2**31 - 1:
            raise ValueError("invalid final seed")
    if p["selection_train_seed"] in seeds:
        raise ValueError("selection and final training seeds overlap")
    return p


def splits_for(p):
    n = sum(p[k] for k in ("train_size", "validation_size", "test_size"))
    values = random.Random(p["data_seed"]).sample(range(2**p["sequence_length"]), n)
    a, b = p["train_size"], p["validation_size"]
    return {"train": values[:a], "validation": values[a:a+b], "test": values[a+b:]}


def bits_of(value, length):
    return [(value >> i) & 1 for i in range(length-1, -1, -1)]


def label(bits, task):
    if task == "remember_first":
        return bits[0]
    if task == "xor_endpoints":
        return bits[0] ^ bits[-1]
    if task == "majority":
        return int(sum(bits) > len(bits)//2)
    raise ValueError("unknown task")


def rank(rec):
    return (-rec["validation"]["macro_accuracy"], rec["parameters"], identity(rec["recipe"]))


def next_recipe(records, rng, max_blocks):
    seen = {tuple(x["recipe"]) for x in records}
    top = sorted(records, key=rank)[:2]
    for _ in range(128):
        parent = rng.choice(top)
        recipe = list(parent["recipe"])
        if recipe == ["identity"]:
            recipe = []
        move = rng.choice(("replace", "insert", "delete"))
        if move == "replace" and recipe:
            i = rng.randrange(len(recipe))
            recipe[i] = rng.choice([op for op in OPS if op != recipe[i]])
        elif move == "insert" and len(recipe) < max_blocks:
            recipe.insert(rng.randrange(len(recipe)+1), rng.choice(OPS))
        elif move == "delete" and recipe:
            recipe.pop(rng.randrange(len(recipe)))
        else:
            continue
        candidate = tuple(recipe or ["identity"])
        if candidate not in seen:
            return candidate, identity(parent["recipe"])
    for size in range(1, max_blocks+1):
        for recipe in itertools.product(OPS, repeat=size):
            if recipe not in seen:
                return recipe, "enumeration-fallback"
    raise RuntimeError("search space exhausted")

def make_model(recipe, width, length):
    import torch
    from torch import nn
    from torch.nn import functional as F

    class Mixer(nn.Module):
        def __init__(self, name):
            super().__init__()
            self.name = name
            self.norm, self.ff_norm = nn.LayerNorm(width), nn.LayerNorm(width)
            self.ff = nn.Sequential(nn.Linear(width, 2*width), nn.GELU(), nn.Linear(2*width, width))
            if name == "attn":
                self.qkv, self.proj = nn.Linear(width, 3*width), nn.Linear(width, width)
            elif name == "gru":
                self.rnn = nn.GRU(width, width, batch_first=True)
            elif name == "conv":
                self.conv = nn.Conv1d(width, width, kernel_size=3, padding=2, groups=width)
                self.proj = nn.Linear(width, width)
            else:
                raise ValueError("unknown operation")

        def forward(self, x):
            h = self.norm(x)
            if self.name == "attn":
                q, k, v = self.qkv(h).chunk(3, dim=-1)
                scores = q @ k.transpose(-1, -2) / math.sqrt(width)
                n = h.shape[1]
                mask = torch.triu(torch.ones(n, n, dtype=torch.bool, device=h.device), diagonal=1)
                z = self.proj(torch.softmax(scores.masked_fill(mask, float("-inf")), dim=-1) @ v)
            elif self.name == "gru":
                z, _ = self.rnn(h)
            else:
                z = self.proj(F.gelu(self.conv(h.transpose(1, 2))[:, :, :h.shape[1]].transpose(1, 2)))
            x = x + z
            return x + self.ff(self.ff_norm(x))

    class Model(nn.Module):
        def __init__(self):
            super().__init__()
            self.token = nn.Embedding(2, width)
            self.position = nn.Embedding(length, width)
            self.task = nn.Embedding(len(TASKS), width)
            self.blocks = nn.ModuleList([Mixer(op) for op in recipe if op != "identity"])
            self.norm = nn.LayerNorm(width)
            self.head = nn.Linear(width, 2)

        def forward(self, xs, task_ids):
            positions = torch.arange(xs.shape[1], device=xs.device)
            x = self.token(xs) + self.position(positions)[None, :, :] + self.task(task_ids)[:, None, :]
            for block in self.blocks:
                x = block(x)
            return self.head(self.norm(x[:, -1, :]))

    return Model()


def make_dataset(values, p):
    import torch
    x, t, y = [], [], []
    for i, value in enumerate(values):
        bits = bits_of(value, p["sequence_length"])
        task = i % len(TASKS)
        x.append(bits)
        t.append(task)
        y.append(label(bits, TASKS[task]))
    return (torch.tensor(x, dtype=torch.long), torch.tensor(t, dtype=torch.long), torch.tensor(y, dtype=torch.long))


def evaluate(model, dataset, batch_size):
    import torch
    from torch.nn import functional as F
    x, t, y = dataset
    counts, correct = [0]*len(TASKS), [0]*len(TASKS)
    total_loss = 0.0
    model.eval()
    with torch.inference_mode():
        for start in range(0, len(x), batch_size):
            xs, ts, ys = x[start:start+batch_size], t[start:start+batch_size], y[start:start+batch_size]
            logits = model(xs, ts)
            total_loss += float(F.cross_entropy(logits, ys, reduction="sum").item())
            prediction = logits.argmax(dim=-1)
            for i in range(len(TASKS)):
                mask = ts == i
                counts[i] += int(mask.sum())
                correct[i] += int(((prediction == ys) & mask).sum())
    if not all(counts):
        raise ValueError("unrepresented task family")
    return {"macro_accuracy": sum(c/n for c,n in zip(correct,counts))/len(TASKS),
            "micro_accuracy": sum(correct)/sum(counts), "cross_entropy": total_loss/sum(counts),
            "by_task": {name: {"correct":correct[i],"count":counts[i],"accuracy":correct[i]/counts[i]}
                        for i,name in enumerate(TASKS)}}


def fit(recipe, p, datasets, seed, split):
    import torch
    from torch.nn import functional as F
    if split not in ("validation", "test"):
        raise ValueError("invalid evaluation split")
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    model = make_model(recipe, p["width"], p["sequence_length"])
    count = sum(param.numel() for param in model.parameters())
    optimizer = torch.optim.AdamW(model.parameters(), lr=p["learning_rate"], weight_decay=0.01)
    x, tasks, y = datasets["train"]
    rng = torch.Generator().manual_seed(seed+314159)
    before = time.monotonic()
    last_loss = 0.0
    for _ in range(p["steps"]):
        model.train()
        ix = torch.randint(len(x), (p["batch_size"],), generator=rng)
        optimizer.zero_grad(set_to_none=True)
        loss = F.cross_entropy(model(x[ix], tasks[ix]), y[ix])
        if not bool(torch.isfinite(loss)):
            raise RuntimeError("nonfinite loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        last_loss = float(loss.detach())
    return {"recipe":list(recipe),"seed":seed,"parameters":count,"steps":p["steps"],
            "last_batch_loss":last_loss,"elapsed_seconds":round(time.monotonic()-before,4),
            split:evaluate(model,datasets[split],p["batch_size"])}

def journal_event(path, event, **data):
    row = {"event": event, "at": dt.datetime.now(dt.timezone.utc).isoformat(), **data}
    with path.open("ab") as h:
        h.write(encoded(row) + b"\n")
        h.flush()
        os.fsync(h.fileno())


def write_once(path, data):
    with path.open("xb") as h:
        h.write(data)
        h.flush()
        os.fsync(h.fileno())


def run(p, dest, protocol_bytes):
    import torch
    validate_protocol(p)
    journal = Path(str(dest) + ".journal.jsonl")
    if dest.exists() or journal.exists() or Path(str(dest)+".failure.json").exists():
        raise FileExistsError("cannot overwrite result or previous attempt evidence")
    dest.parent.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    splits = splits_for(p)
    datasets = {name: make_dataset(ids,p) for name,ids in splits.items()}
    source_sha = digest(Path(__file__).read_bytes())
    base = {"study_id":p["study_id"],"protocol_sha256":digest(protocol_bytes),"source_sha256":source_sha}
    journal_event(journal,"study_started",**base)
    results, holdouts = [], []
    rng = random.Random(p["search_seed"])
    try:
        for slot in range(p["max_candidates"]):
            recipe, parent = (BASES[slot],None) if slot < 4 else next_recipe(results,rng,p["max_blocks"])
            journal_event(journal,"validation_started",slot=slot,recipe=list(recipe),parent=parent)
            result = fit(recipe,p,datasets,p["selection_train_seed"],"validation")
            result.update({"slot":slot,"parent":parent})
            results.append(result)
            journal_event(journal,"validation_completed",slot=slot,result=result)
        winner = min(results,key=rank)
        selection = {"recipe":winner["recipe"],"slot":winner["slot"],"selection_on":"validation_only"}
        journal_event(journal,"selection_locked",selection=selection)
        final_recipes = list(dict.fromkeys([*BASES,tuple(winner["recipe"])]))
        for recipe in final_recipes:
            for seed in p["final_train_seeds"]:
                journal_event(journal,"holdout_started",recipe=list(recipe),seed=seed)
                result = fit(recipe,p,datasets,seed,"test")
                holdouts.append(result)
                journal_event(journal,"holdout_completed",result=result)
        journal_event(journal,"study_complete",selection=selection)
        report = {"status":"COMPLETE_RESEARCH_PILOT","scope":"tiny authored synthetic sequences; not transformer-scale discovery",
                  "study_id":p["study_id"],"protocol":p,**{k:v for k,v in base.items() if k!="study_id"},
                  "source_environment":{"python":platform.python_version(),"torch":torch.__version__,"device":"cpu","threads":torch.get_num_threads()},
                  "split_sha256":digest(encoded(splits)),"split_sizes":{key:len(val) for key,val in splits.items()},
                  "validation_records":results,"selection":selection,"final_records":holdouts,
                  "journal_sha256":digest(journal.read_bytes()),
                  "limitations":["single authored task generator","test inputs not externally administered",
                                 "related training seeds and shared holdout examples","no search for new primitive operators",
                                 "no independently established novelty","no broad capability or scaling claim"]}
        report["report_sha256"] = digest(encoded(report))
        write_once(dest,encoded(report)+b"\n")
        return report
    except Exception as exc:
        journal_event(journal,"study_failed",error=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()[-2000:])
        failure={"status":"FAILED_OR_INCOMPLETE",**base,"completed_validations":results,
                 "completed_holdouts":holdouts,"error":str(exc),"journal_sha256":digest(journal.read_bytes())}
        write_once(Path(str(dest)+".failure.json"),encoded(failure)+b"\n")
        raise


def check_metrics(m, count):
    if set(m["by_task"]) != set(TASKS):
        raise ValueError("invalid task family coverage")
    totals = []
    for name in TASKS:
        task=m["by_task"][name]
        c,n=task["correct"],task["count"]
        if type(c) is not int or type(n) is not int or n < 1 or not 0 <= c <= n:
            raise ValueError("invalid task counts")
        if abs(task["accuracy"]-c/n) > 1e-12:
            raise ValueError("task accuracy does not agree with counts")
        totals.append((c,n))
    if sum(n for _,n in totals) != count:
        raise ValueError("incomplete task evaluation")
    if abs(m["micro_accuracy"] - sum(c for c,_ in totals)/count) > 1e-12:
        raise ValueError("incorrect micro accuracy")
    if abs(m["macro_accuracy"] - sum(c/n for c,n in totals)/len(TASKS)) > 1e-12:
        raise ValueError("incorrect macro accuracy")
    if any(type(m[k]) not in (float,int) or not math.isfinite(m[k]) for k in ("micro_accuracy","macro_accuracy","cross_entropy")):
        raise ValueError("nonfinite metrics")
    if not 0 <= m["macro_accuracy"] <= 1 or not 0 <= m["micro_accuracy"] <= 1 or m["cross_entropy"] < 0:
        raise ValueError("out-of-bounds metrics")

def verify(report, journal=None, local_source=False):
    if report.get("status") != "COMPLETE_RESEARCH_PILOT":
        raise ValueError("non-complete study")
    if report["report_sha256"] != digest(encoded({k:v for k,v in report.items() if k!="report_sha256"})):
        raise ValueError("report integrity failure")
    p=validate_protocol(report["protocol"])
    if report["protocol_sha256"] != digest(encoded(p)+b"\n"):
        raise ValueError("protocol integrity failure")
    if local_source and report["source_sha256"] != digest(Path(__file__).read_bytes()):
        raise ValueError("source integrity failure")
    s=splits_for(p)
    if report["split_sha256"] != digest(encoded(s)) or report["split_sizes"] != {k:len(v) for k,v in s.items()}:
        raise ValueError("data split integrity failure")
    rs=report["validation_records"]
    if len(rs) != p["max_candidates"]:
        raise ValueError("missing candidate runs")
    rng=random.Random(p["search_seed"])
    for i, record in enumerate(rs):
        candidate,parent=(BASES[i],None) if i < 4 else next_recipe(rs[:i],rng,p["max_blocks"])
        if (record["slot"] != i or record["seed"] != p["selection_train_seed"] or
            record["steps"] != p["steps"] or record["parent"] != parent or
            validate_recipe(record["recipe"],p["max_blocks"]) != candidate or record["parameters"] < 1):
            raise ValueError("candidate sequence or budget mismatch")
        check_metrics(record["validation"],p["validation_size"])
    winner=min(rs,key=rank)
    choice={"recipe":winner["recipe"],"slot":winner["slot"],"selection_on":"validation_only"}
    if choice != report["selection"]:
        raise ValueError("invalid winner selection")
    recipes=list(dict.fromkeys([*BASES,tuple(winner["recipe"])]))
    expected=[(r,seed) for r in recipes for seed in p["final_train_seeds"]]
    final=report["final_records"]
    if len(final) != len(expected):
        raise ValueError("incomplete holdout runs")
    for record,(recipe,seed) in zip(final,expected):
        if (tuple(record["recipe"]) != recipe or record["seed"] != seed or
            record["steps"] != p["steps"] or record["parameters"] < 1):
            raise ValueError("incorrect holdout run coverage")
        check_metrics(record["test"],p["test_size"])
    if journal is not None:
        if digest(journal) != report["journal_sha256"]:
            raise ValueError("journal integrity failure")
        events=[json.loads(line) for line in journal.splitlines()]
        if events[0]["event"] != "study_started" or events[-1]["event"] != "study_complete":
            raise ValueError("incomplete journal")
        starts=[e for e in events if e["event"]=="holdout_started"]
        v=[e["result"] for e in events if e["event"]=="validation_completed"]
        h=[e["result"] for e in events if e["event"]=="holdout_completed"]
        locks=[e["selection"] for e in events if e["event"]=="selection_locked"]
        if v!=rs or h!=final or locks!=[choice] or len(starts)!=len(expected):
            raise ValueError("evidence journal does not match report")


def summarize(report):
    scores={}
    for record in report["final_records"]:
        scores.setdefault(identity(record["recipe"]),[]).append(record["test"]["macro_accuracy"])
    return {"winner_on_validation":identity(report["selection"]["recipe"]),
            "mean_test_macro_accuracy":{k:round(sum(v)/len(v),5) for k,v in scores.items()},
            "seeds_per_architecture":len(report["protocol"]["final_train_seeds"]),
            "interpretation":"Bounded internal synthetic pilot; neither architecture novelty nor general reliability established."}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    run_parser=sub.add_parser("run")
    run_parser.add_argument("--protocol",type=Path,required=True)
    run_parser.add_argument("--out",type=Path,required=True)
    p_parser=sub.add_parser("check-protocol")
    p_parser.add_argument("--protocol",type=Path,required=True)
    v_parser=sub.add_parser("verify")
    v_parser.add_argument("--report",type=Path,required=True)
    v_parser.add_argument("--journal",type=Path)
    v_parser.add_argument("--check-local-source",action="store_true")
    args=parser.parse_args(argv)
    if args.command in ("run","check-protocol"):
        raw=args.protocol.read_bytes()
        p=validate_protocol(json.loads(raw))
        if raw!=encoded(p)+b"\n":
            raise ValueError("protocol must use exact canonical JSON and one LF")
        if args.command=="run":
            result=run(p,args.out,raw)
            verify(result,Path(str(args.out)+".journal.jsonl").read_bytes(),local_source=True)
            print(json.dumps(summarize(result),indent=2))
        else:
            print("protocol valid",digest(raw))
    else:
        result=json.loads(args.report.read_text())
        verify(result,args.journal.read_bytes() if args.journal else None,args.check_local_source)
        print(json.dumps(summarize(result),indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
