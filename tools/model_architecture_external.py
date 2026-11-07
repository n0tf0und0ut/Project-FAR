#!/usr/bin/env python3
"""Research-only externally authored dataset evaluation for known neural mixers.

Datasets are *bundled* scikit-learn UCI subsets, not official CLRS/NAS-Bench-360.
A complete result is required to compute any selection or comparative verdict.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
import traceback

VERSION = "far-mas-external/0.3"
FAMILIES = ("two_attn", "one_attn", "gru", "conv")
DATASETS = ("digits", "breast_cancer")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def file_sha(p):
    return sha(Path(p).read_bytes())


def check(p):
    fields = {"version", "study_id", "datasets", "split_seed", "scales", "steps_budgets",
              "seeds", "batch_size", "learning_rate", "max_param_relative_error",
              "max_mac_relative_error", "training_threads", "comparison", "device",
              "selection_policy", "precommit_source_sha256", "expected_data_sha256", "expected_split_sha256", "acceptance"}
    if type(p) is not dict or set(p) != fields or p["version"] != VERSION:
        raise ValueError("protocol field set or version changed")
    if p["datasets"] != list(DATASETS) or p["device"] != "cpu":
        raise ValueError("dataset/device drift")
    if type(p["study_id"]) is not str or not p["study_id"]:
        raise ValueError("study id absent")
    for k in ("split_seed", "batch_size", "training_threads"):
        if type(p[k]) is not int or not 1 <= p[k] <= 2**31 - 1:
            raise ValueError("bad positive integer "+k)
    for key,low,high in (("scales",8,128),("steps_budgets",4,1000),("seeds",1,2**31-1)):
        v=p[key]
        if type(v) is not list or len(v)<2 or len(v)>4 or len(set(v)) != len(v) or any(type(x) is not int or not low<=x<=high for x in v):
            raise ValueError("bad "+key)
    if p["comparison"] != list(FAMILIES) or p["selection_policy"] != "mean_validation_accuracy_then_cost_then_name":
        raise ValueError("condition or selection drift")
    for k in ("learning_rate", "max_param_relative_error", "max_mac_relative_error"):
        if type(p[k]) not in (int,float) or not math.isfinite(p[k]):
            raise ValueError("bad numeric field "+k)
    if not 0 < p["learning_rate"] < .1 or not 0 < p["max_param_relative_error"] <= .5 or not 0 < p["max_mac_relative_error"] <= .5:
        raise ValueError("invalid numeric bounds")
    a=p["acceptance"]
    if (type(a) is not dict or set(a)!={"primary_scale","primary_steps","min_test_gain","max_selection_regret"} or
        a["primary_scale"] != max(p["scales"]) or a["primary_steps"] != max(p["steps_budgets"]) or
        type(a["min_test_gain"]) not in (int,float) or not 0<=a["min_test_gain"]<.3 or
        type(a["max_selection_regret"]) not in (int,float) or not 0<=a["max_selection_regret"]<.3):
        raise ValueError("preregistered primary screen invalid")
    for key in ("expected_data_sha256", "expected_split_sha256"):
        r=p[key]
        if type(r) is not dict or set(r)!=set(DATASETS) or any(type(z) is not str or len(z)!=64 or any(c not in "0123456789abcdef" for c in z) for z in r.values()):
            raise ValueError("frozen dataset identity invalid: "+key)
    if type(p["precommit_source_sha256"]) is not str or len(p["precommit_source_sha256"]) != 64 or any(c not in "0123456789abcdef" for c in p["precommit_source_sha256"]):
        raise ValueError("bad frozen source hash")
    return p


def read_dataset(name, split_seed):
    import numpy as np
    from sklearn import datasets, model_selection, preprocessing
    import sklearn
    if name not in DATASETS:
        raise ValueError("dataset name not registered")
    if name == "digits":
        source=datasets.load_digits()
        rows=8
        cols=8
        classes=10
    else:
        source=datasets.load_breast_cancer()
        rows=30
        cols=1
        classes=2
    data=np.ascontiguousarray(source.data, dtype="<f8")
    labels=np.ascontiguousarray(source.target, dtype="<i8")
    if len(data) != len(labels) or data.shape[1] != rows*cols or sorted(np.unique(labels).tolist()) != list(range(classes)):
        raise ValueError("external dataset shape or classes changed")
    raw_sha=sha(data.tobytes(order="C") + labels.tobytes(order="C"))
    indices=np.arange(len(labels),dtype=np.int64)
    # Stratification preserves all classes; validation and test remain unseen during training.
    trainval,test=model_selection.train_test_split(indices,test_size=.2,stratify=labels,random_state=split_seed)
    train,val=model_selection.train_test_split(trainval,test_size=.25,stratify=labels[trainval],random_state=split_seed+1)
    ids={"train":train.tolist(),"validation":val.tolist(),"test":test.tolist()}
    if len(set(train) | set(val) | set(test)) != len(labels) or (set(train)&set(val)) or (set(train)&set(test)) or (set(val)&set(test)):
        raise RuntimeError("overlap/coverage of data splits")
    scaler=preprocessing.StandardScaler().fit(data[train])
    norm=np.ascontiguousarray(scaler.transform(data).astype("<f4"))
    tensors={k:(norm[np.asarray(v)].reshape(-1,rows,cols),labels[np.asarray(v)].astype("int64")) for k,v in ids.items()}
    return {"id":name,"source":"scikit-learn bundled UCI dataset", "sklearn_version":sklearn.__version__,
            "raw_sha256":raw_sha,"split_sha256":sha(canonical(ids)),"split_indices":ids,
            "shape":[len(labels), rows*cols],"tokens":rows,"token_features":cols,"classes":classes,
            "scaler_fit_on":"train_only","split_sizes":{k:len(v) for k,v in ids.items()}}, tensors


def model(family,width,n_tokens,token_features,classes):
    import torch
    from torch import nn
    from torch.nn import functional as F
    if family not in FAMILIES or width < 4:
        raise ValueError("invalid model family")
    class Block(nn.Module):
        def __init__(self,mode):
            super().__init__()
            self.mode=mode
            self.pre=nn.LayerNorm(width)
            self.post=nn.LayerNorm(width)
            self.ff=nn.Sequential(nn.Linear(width,width*2),nn.GELU(),nn.Linear(width*2,width))
            if mode == "attn":
                self.qkv=nn.Linear(width,width*3)
                self.proj=nn.Linear(width,width)
            elif mode == "gru":
                self.recurrent=nn.GRU(width,width,batch_first=True)
            else:
                self.depthwise=nn.Conv1d(width,width,3,padding=1,groups=width)
                self.proj=nn.Linear(width,width)
        def forward(self,x):
            a=self.pre(x)
            if self.mode == "attn":
                q,k,v=self.qkv(a).chunk(3,dim=-1)
                z=self.proj(torch.softmax((q@k.transpose(-2,-1))/math.sqrt(width),dim=-1)@v)
            elif self.mode=="gru":
                z,_=self.recurrent(a)
            else:
                z=self.proj(F.gelu(self.depthwise(a.transpose(1,2)).transpose(1,2)))
            z=x+z
            return z+self.ff(self.post(z))
    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.project=nn.Linear(token_features,width)
            self.position=nn.Parameter(torch.zeros(1,n_tokens,width))
            modes={"two_attn":("attn","attn"),"one_attn":("attn",),"gru":("gru",),"conv":("conv",)}[family]
            self.blocks=nn.ModuleList([Block(x) for x in modes])
            self.final=nn.LayerNorm(width)
            self.classifier=nn.Linear(width,classes)
        def forward(self,x):
            z=self.project(x)+self.position
            for block in self.blocks:
                z=block(z)
            return self.classifier(self.final(z).mean(dim=1))
    return Net()


def mac_estimate(family,width,n_tokens,token_features,classes):
    """Estimated forward linear/attention/conv multiply-accumulates per input.
    Omits layer normalization, activation, softmax, recurrent gate elementwise ops.
    This is NOT measured FLOPs and CANNOT establish actual compute equivalence.
    """
    base=n_tokens*token_features*width + width*classes
    if family == "two_attn":
        return base+2*(8*n_tokens*width**2+2*n_tokens*n_tokens*width)
    if family == "one_attn":
        return base+(8*n_tokens*width**2+2*n_tokens*n_tokens*width)
    if family == "gru":
        return base+10*n_tokens*width**2
    if family == "conv":
        return base+(5*n_tokens*width**2+3*n_tokens*width)
    raise ValueError("unknown family")


def specs(n_tokens,token_features,classes,base_width,p):
    import torch
    d={}
    anchor=model("two_attn",base_width,n_tokens,token_features,classes)
    tp=sum(x.numel() for x in anchor.parameters())
    tm=mac_estimate("two_attn",base_width,n_tokens,token_features,classes)
    for family in FAMILIES:
        if family == "two_attn":
            width=base_width
        else:
            options=[]
            for w in range(max(8,base_width),min(192,base_width*3)+1):
                params=sum(x.numel() for x in model(family,w,n_tokens,token_features,classes).parameters())
                mac=mac_estimate(family,w,n_tokens,token_features,classes)
                dp=abs(params-tp)/tp
                dm=abs(mac-tm)/tm
                options.append((max(dp,dm),dp+dm,w))
            width=min(options)[2]
        params=sum(x.numel() for x in model(family,width,n_tokens,token_features,classes).parameters())
        mac=mac_estimate(family,width,n_tokens,token_features,classes)
        pr=(params-tp)/tp
        mr=(mac-tm)/tm
        d[family]={"family":family,"width":width,"parameters":params,"estimated_forward_macs":mac,
                   "parameter_relative_difference":pr,"estimated_mac_relative_difference":mr,
                   "within_registered_cost_bounds":abs(pr)<=p["max_param_relative_error"] and abs(mr)<=p["max_mac_relative_error"]}
    return d


def fingerprint(model):
    import numpy as np
    import torch
    h=hashlib.sha256()
    with torch.no_grad():
        for name,v in sorted(model.state_dict().items()):
            t=v.detach().cpu().contiguous()
            h.update(name.encode()+b"\x00"+str(tuple(t.shape)).encode()+b"\x00"+str(t.dtype).encode()+b"\x00"+t.numpy().tobytes())
    return h.hexdigest()


def predict(model,x,batch_size):
    import torch
    model.eval()
    outputs=[]
    with torch.inference_mode():
        for b in range(0,len(x),batch_size):
            outputs.extend(model(x[b:b+batch_size]).argmax(dim=-1).cpu().tolist())
    return outputs


def grade(pred,truth,classes):
    if len(pred)!=len(truth) or any(type(y) is not int or y<0 or y>=classes for y in pred):
        raise ValueError("invalid prediction encoding")
    good=sum(int(a==int(b)) for a,b in zip(pred,truth))
    per_class={str(i):{"count":int(sum(int(v==i) for v in truth)),
                       "correct":int(sum(int(y==i and p==i) for p,y in zip(pred,truth)))} for i in range(classes)}
    if any(v["count"]<1 for v in per_class.values()):
        raise ValueError("missing class in evaluation")
    return {"accuracy":good/len(truth),"correct":good,"count":len(truth),
            "macro_recall":sum(v["correct"]/v["count"] for v in per_class.values())/classes,
            "per_class":per_class}


def reference_baselines(desc, datasets, split_seed):
    """Fixed simple baselines: external task relevance, not compute-matched arms."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC
    from sklearn.neighbors import KNeighborsClassifier
    t = datasets["train"]
    train_x, train_y = t[0].reshape(len(t[0]), -1), t[1]
    conditions = {
        "logistic_regression": LogisticRegression(max_iter=2000, C=1.0, solver="lbfgs"),
        "rbf_svm": SVC(C=1.0, gamma="scale", kernel="rbf"),
        "knn5": KNeighborsClassifier(n_neighbors=5),
    }
    observed = {}
    for name, estimator in conditions.items():
        before = time.monotonic()
        estimator.fit(train_x, train_y)
        outcome = {"training_seconds": round(time.monotonic()-before, 6)}
        for split in ("validation", "test"):
            xx,yy=datasets[split]
            pred=[int(v) for v in estimator.predict(xx.reshape(len(xx), -1))]
            outcome[split+"_predictions"]=pred
            outcome[split+"_metrics"]=grade(pred,yy.tolist(),desc["classes"])
        observed[name]=outcome
    return observed


def train_one(spec,ds,p,steps,seed):
    import torch
    from torch.nn import functional as F
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    n_tokens=ds["tokens"]
    m=ds["token_features"]
    classes=ds["classes"]
    net=model(spec["family"],spec["width"],n_tokens,m,classes)
    opt=torch.optim.AdamW(net.parameters(),lr=p["learning_rate"],weight_decay=.01)
    train_x,train_y=ds["tensors"]["train"]
    rng=torch.Generator().manual_seed(seed+9007)
    t0=time.monotonic()
    net.train()
    for _ in range(steps):
        idx=torch.randint(len(train_y),(p["batch_size"],),generator=rng)
        opt.zero_grad(set_to_none=True)
        loss=F.cross_entropy(net(train_x[idx]),train_y[idx])
        if not torch.isfinite(loss).item():
            raise ValueError("nonfinite training loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(),1.)
        opt.step()
    sec=round(time.monotonic()-t0,6)
    val=predict(net,ds["tensors"]["validation"][0],p["batch_size"])
    return net,{"train_seconds":sec,"last_training_loss":float(loss.detach()),
                "validation_predictions":val,
                "validation_metrics":grade(val,ds["tensors"]["validation"][1].tolist(),classes)}


def event(path,entry):
    record={"timestamp_utc":dt.datetime.now(dt.timezone.utc).isoformat(),**entry}
    with Path(path).open("ab") as f:
        f.write(canonical(record)+b"\n")
        f.flush()
        os.fsync(f.fileno())


def write_once(path,raw):
    with Path(path).open("xb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())


def finish_analysis(records,p,reference_baselines=None):
    analysis={}
    for dataset in DATASETS:
        for scale in p["scales"]:
            for steps in p["steps_budgets"]:
                group=[r for r in records if r["dataset"]==dataset and r["scale"]==scale and r["steps"]==steps]
                if len(group)!=len(FAMILIES)*len(p["seeds"]):
                    raise ValueError("incomplete group")
                averages={family:{"validation":sum(z["validation_metrics"]["accuracy"] for z in group if z["family"]==family)/len(p["seeds"]),
                                  "test":sum(z["test_metrics"]["accuracy"] for z in group if z["family"]==family)/len(p["seeds"]),
                                  "parameters":next(z["parameters"] for z in group if z["family"]==family),
                                  "estimated_forward_macs":next(z["estimated_forward_macs"] for z in group if z["family"]==family),
                                  "time_seconds_mean":sum(z["train_seconds"] for z in group if z["family"]==family)/len(p["seeds"])} for family in FAMILIES}
                selected=min(FAMILIES,key=lambda family:(-averages[family]["validation"],averages[family]["estimated_forward_macs"],family))
                key=f"{dataset}/width-{scale}/steps-{steps}"
                analysis[key]={"chosen_by_validation":selected,"test_of_selected":averages[selected]["test"],
                               "best_test_seen_post_selection":max(x["test"] for x in averages.values()),
                               "selection_regret_descriptive":max(x["test"] for x in averages.values())-averages[selected]["test"],
                               "comparison":averages}
    if reference_baselines is not None:
        for name in DATASETS:
            baselines=reference_baselines[name]
            selected_simple=min(baselines,key=lambda k:(-baselines[k]["validation_metrics"]["accuracy"],k))
            analysis[name+"/simple_comparators"]={"best_by_validation":selected_simple,
                "best_baseline_test_accuracy":baselines[selected_simple]["test_metrics"]["accuracy"],
                "others":{k:{"validation":v["validation_metrics"]["accuracy"],"test":v["test_metrics"]["accuracy"]} for k,v in baselines.items()},
                "not_compute_matched":True}
        a=p["acceptance"]
        primary={}
        for name in DATASETS:
            comparison=analysis[f'{name}/width-{a["primary_scale"]}/steps-{a["primary_steps"]}']
            simple=analysis[name+"/simple_comparators"]
            advantage=comparison["test_of_selected"]-simple["best_baseline_test_accuracy"]
            primary[name]={"chosen_neural":comparison["chosen_by_validation"],
                           "best_simple":simple["best_by_validation"],"heldout_accuracy_difference":advantage,
                           "selection_regret":comparison["selection_regret_descriptive"],
                           "passes_internal_screen":advantage>=a["min_test_gain"] and comparison["selection_regret_descriptive"]<=a["max_selection_regret"]}
        analysis["primary_screen"]={"criteria":a,"by_dataset":primary,
                                    "passes_both":all(x["passes_internal_screen"] for x in primary.values()),
                                    "not_external_adjudication_or_architecture_novelty":True}
    return analysis


def run(p,raw,out):
    import numpy as np
    import torch
    import sklearn
    check(p)
    if file_sha(__file__)!=p["precommit_source_sha256"]:
        raise ValueError("source hash mismatch; frozen code cannot be changed")
    out=Path(out)
    journal=Path(str(out)+".journal.jsonl")
    failure=Path(str(out)+".failed.json")
    if any(f.exists() for f in (out,journal,failure)):
        raise FileExistsError("prior complete/incomplete evidence cannot be overwritten")
    out.parent.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(p["training_threads"])
    sources={"python":platform.python_version(),"torch":torch.__version__,"numpy":np.__version__,
             "scikit_learn":sklearn.__version__,"device":"cpu","threads":torch.get_num_threads(),
             "source_sha256":file_sha(__file__),"protocol_sha256":sha(raw)}
    event(journal,{"event":"start", "study_id":p["study_id"],"environment":sources})
    records=[]
    dataset_manifest={}
    simple_results={}
    try:
        for name in DATASETS:
            desc,data=read_dataset(name,p["split_seed"])
            if desc["raw_sha256"]!=p["expected_data_sha256"][name] or desc["split_sha256"]!=p["expected_split_sha256"][name]:
                raise ValueError("frozen dataset/split mismatch: "+name)
            dataset_manifest[name]=desc
            d={"tokens":desc["tokens"],"token_features":desc["token_features"],"classes":desc["classes"],
               "tensors":{k:(torch.from_numpy(x).float(),torch.from_numpy(y).long()) for k,(x,y) in data.items()}}
            for scale in p["scales"]:
                candidates=specs(desc["tokens"],desc["token_features"],desc["classes"],scale,p)
                if any(not val["within_registered_cost_bounds"] for val in candidates.values()):
                    raise ValueError("parameter/MAC controls exceed frozen threshold")
                for steps in p["steps_budgets"]:
                    staged=[]
                    for family in FAMILIES:
                        spec=candidates[family]
                        for seed in p["seeds"]:
                            key={"dataset":name,"scale":scale,"steps":steps,"family":family,"seed":seed}
                            event(journal,{"event":"train_started",**key,"spec":spec})
                            net,info=train_one(spec,d,p,steps,seed)
                            rec={**key,**spec,**info,"checkpoint_sha256":fingerprint(net)}
                            staged.append((rec,net))
                            event(journal,{"event":"training_completed", "record_without_test":rec})
                    # Frozen evaluation policy: no test prediction until all candidates for this group
                    # have been trained and *validation-only selection* has been journaled.
                    averages={family:sum(r["validation_metrics"]["accuracy"] for r,_ in staged if r["family"]==family)/len(p["seeds"]) for family in FAMILIES}
                    selected=min(FAMILIES,key=lambda family:(-averages[family],candidates[family]["estimated_forward_macs"],family))
                    event(journal,{"event":"selection_locked", "dataset":name,"scale":scale,"steps":steps,
                                   "selected":selected,"average_validation_accuracies":averages})
                    for rec,net in staged:
                        xp,yp=d["tensors"]["test"]
                        pred=predict(net,xp,p["batch_size"])
                        rec["test_predictions"]=pred
                        rec["test_metrics"]=grade(pred,yp.tolist(),desc["classes"])
                        records.append(rec)
                        event(journal,{"event":"test_completed", "record":rec})
            # Fixed simple baseline estimates are generated only after neural selection locks.
            simple_results[name]=reference_baselines(desc,{k:(x.numpy(),y.numpy()) for k,(x,y) in d["tensors"].items()},p["split_seed"])
            event(journal,{"event":"simple_baselines_completed","dataset":name,"results":simple_results[name]})
        analysis=finish_analysis(records,p,simple_results)
        event(journal,{"event":"complete","records":len(records)})
        result={"status":"COMPLETED_RESEARCH_ONLY","study_id":p["study_id"],"protocol":p,
                "environment":sources,"datasets":dataset_manifest,"records":records,"simple_baselines":simple_results,"analysis":analysis,
                "journal_sha256":file_sha(journal),
                "limitations":["Not official CLRS-30/NAS-Bench-360 benchmark data or their scoring contracts",
                               "Published datasets but internally stratified re-splits/evaluation, not independent adjudication",
                               "MAC estimates omit nonlinearities/normalization; not measured FLOPs or equal total training compute",
                               "2 small bundled UCI datasets, no out-of-distribution evaluation or architectural novelty"]}
        result["report_sha256"]=sha(canonical(result))
        write_once(out,canonical(result)+b"\n")
        return result
    except Exception as e:
        event(journal,{"event":"failed","error_type":type(e).__name__,"error":str(e),"traceback":traceback.format_exc()[-3000:]})
        write_once(failure,canonical({"status":"FAILED_OR_INCOMPLETE","study_id":p["study_id"],"completed":records,
                                      "journal_sha256":file_sha(journal),"error_type":type(e).__name__,"error":str(e)})+b"\n")
        raise


def verify(result,journal_bytes=None):
    if result.get("status")!="COMPLETED_RESEARCH_ONLY" or result.get("report_sha256")!=sha(canonical({k:v for k,v in result.items() if k!="report_sha256"})):
        raise ValueError("result integrity invalid")
    p=check(result["protocol"])
    if result["environment"]["source_sha256"]!=p["precommit_source_sha256"]:
        raise ValueError("unmatched frozen source")
    keys=[(r["dataset"],r["scale"],r["steps"],r["family"],r["seed"]) for r in result["records"]]
    expected=[(name,scale,steps,family,seed) for name in DATASETS for scale in p["scales"] for steps in p["steps_budgets"] for family in FAMILIES for seed in p["seeds"]]
    if keys!=expected:
        raise ValueError("missing, reordered, duplicate or substituted trial")
    for name in DATASETS:
        desc,tensors=read_dataset(name,p["split_seed"])
        d=result["datasets"][name]
        if desc!=d or desc["raw_sha256"]!=p["expected_data_sha256"][name] or desc["split_sha256"]!=p["expected_split_sha256"][name]:
            raise ValueError("dataset identity/split/normalization mismatch")
        for scale in p["scales"]:
            xspec=specs(desc["tokens"],desc["token_features"],desc["classes"],scale,p)
            for rec in (r for r in result["records"] if r["dataset"]==name and r["scale"]==scale):
                target=tensors["test"][1].tolist()
                validation_target=tensors["validation"][1].tolist()
                required=xspec[rec["family"]]
                if any(rec[k]!=required[k] for k in required) or rec["steps"] not in p["steps_budgets"]:
                    raise ValueError("model size/cost/substitution mismatch")
                if rec["validation_metrics"]!=grade(rec["validation_predictions"],validation_target,desc["classes"]):
                    raise ValueError("invalid validation grade")
                if rec["test_metrics"]!=grade(rec["test_predictions"],target,desc["classes"]):
                    raise ValueError("invalid heldout grade")
    for name in DATASETS:
        _,data=read_dataset(name,p["split_seed"])
        for key,r in result["simple_baselines"][name].items():
            if key not in ("logistic_regression","rbf_svm","knn5"):
                raise ValueError("unknown simple comparator")
            for split in ("validation","test"):
                expected=grade(r[split+"_predictions"],data[split][1].tolist(),result["datasets"][name]["classes"])
                if r[split+"_metrics"] != expected:
                    raise ValueError("incorrect simple comparator score")
    if result["analysis"]!=finish_analysis(result["records"],p,result["simple_baselines"]):
        raise ValueError("selection/metric analysis mismatch")
    if journal_bytes is not None:
        if sha(journal_bytes)!=result["journal_sha256"]:
            raise ValueError("journal checksum invalid")
        events=[json.loads(row) for row in journal_bytes.splitlines()]
        if not events or events[0]["event"]!="start" or events[-1]["event"]!="complete":
            raise ValueError("journal incomplete")
        v=[e["record"] for e in events if e["event"]=="test_completed"]
        if v!=result["records"]:
            raise ValueError("journal/report mismatch")
        locks=[e for e in events if e["event"]=="selection_locked"]
        if len(locks)!=len(p["scales"])*len(p["steps_budgets"])*len(DATASETS):
            raise ValueError("missing validation locks")
        for e in locks:
            key=f'{e["dataset"]}/width-{e["scale"]}/steps-{e["steps"]}'
            if e["selected"]!=result["analysis"][key]["chosen_by_validation"]:
                raise ValueError("selection lock mismatch")


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("check")
    a.add_argument("--protocol",type=Path,required=True)
    a=sub.add_parser("run")
    a.add_argument("--protocol",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True)
    a=sub.add_parser("verify")
    a.add_argument("--result",type=Path,required=True)
    a.add_argument("--journal",type=Path)
    args=ap.parse_args(argv)
    if args.cmd in ("run","check"):
        raw=args.protocol.read_bytes()
        p=check(json.loads(raw))
        if raw!=canonical(p)+b"\n":
            raise ValueError("noncanonical frozen protocol")
        if args.cmd=="check":
            print("VALID",sha(raw))
        else:
            r=run(p,raw,args.out)
            verify(r,Path(str(args.out)+".journal.jsonl").read_bytes())
            print(json.dumps(r["analysis"],indent=2))
    else:
        r=json.loads(args.result.read_text())
        verify(r,args.journal.read_bytes() if args.journal else None)
        print("VERIFIED",len(r["records"]))

if __name__=="__main__":
    main()
