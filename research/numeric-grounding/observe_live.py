"""Read-only observation of the frozen numeric-grounding push-run and evidence.

This does not run a model or revise any preregistered experiment input.
"""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
import zipfile

FROZEN_LAUNCH_SHA = "2b6a52f6c5fdc7d55240a358c42fe45818571672"
REPO = "n0tf0und0ut/Project-FAR"
WORKFLOW = "numeric-grounding-live-v01.yml"
OUT = Path("artifacts/numeric-grounding-live-observation.json")


def fetch(url, token, limit=10_000_000):
    headers={"Accept":"application/vnd.github+json",
             "X-GitHub-Api-Version":"2022-11-28",
             "User-Agent":"FAR-research-evidence-observer"}
    if token:
        headers["Authorization"]="Bearer "+token
    req=urllib.request.Request(url,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=30) as res:
            raw=res.read(limit+1)
    except urllib.error.HTTPError as exc:
        if exc.code==401 and token:
            return fetch(url,None,limit)
        raise
    if len(raw)>limit:
        raise ValueError("GitHub evidence response exceeds byte budget")
    return raw


def record(value):
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
    print(json.dumps(value,sort_keys=True))
    return 0


def main():
    token=os.getenv("GH_TOKEN")
    if not token:
        return record({"status":"OBSERVER_NOT_AUTHORIZED","launch_sha":FROZEN_LAUNCH_SHA})
    root=f"https://api.github.com/repos/{REPO}/actions"
    try:
        payload=json.loads(fetch(root+"/workflows/"+WORKFLOW+"/runs?event=push&per_page=100",token))
        matches=[r for r in payload.get("workflow_runs",[]) if r.get("head_sha")==FROZEN_LAUNCH_SHA and r.get("event")=="push"]
        if not matches:
            return record({"status":"LAUNCH_RUN_NOT_VISIBLE","launch_sha":FROZEN_LAUNCH_SHA})
        if len(matches)>1:
            return record({"status":"AMBIGUOUS_LAUNCH_RUNS","launch_sha":FROZEN_LAUNCH_SHA,
                           "run_ids":sorted(r["id"] for r in matches)})
        run=matches[0]
        base={"launch_sha":FROZEN_LAUNCH_SHA,"run_id":run["id"],
              "url":run.get("html_url"),"workflow_status":run.get("status"),
              "workflow_conclusion":run.get("conclusion")}
        if run.get("status")!="completed":
            return record({"status":"RUN_IN_PROGRESS",**base})
        artifacts=json.loads(fetch(root+f"/runs/{run['id']}/artifacts?per_page=100",token))
        relevant=[a for a in artifacts.get("artifacts",[])
                  if a.get("name")==f"numeric-grounding-live-v01-raw-{run['id']}" and not a.get("expired")]
        if len(relevant)!=1:
            return record({"status":"COMPLETED_WITHOUT_READABLE_EVIDENCE",**base,
                           "artifact_count":len(relevant)})
        artifact=relevant[0]
        raw=fetch(artifact["archive_download_url"],token,limit=30_000_000)
        digest=hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as dirname:
            target=Path(dirname)
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                names=z.namelist()
                if len(names)!=len(set(names)):
                    raise ValueError("duplicate artifact ZIP names")
                for item in z.infolist():
                    name=PurePosixPath(item.filename)
                    if name.is_absolute() or not name.parts or any(x in ("..",".") for x in name.parts):
                        raise ValueError("unsafe ZIP member")
                    if item.is_dir():
                        continue
                    if item.file_size>1_000_000:
                        raise ValueError("oversized evidence member")
                    destination=target.joinpath(*name.parts)
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    destination.write_bytes(z.read(item))
            analyses=list(target.rglob("analysis.json"))
            state=list(target.rglob("state.json"))
            if len(analyses)!=1:
                summary={"status":"INCOMPLETE_EXPERIMENT","state":json.loads(state[0].read_text()) if len(state)==1 else None}
            else:
                result=subprocess.run([sys.executable,"research/numeric-grounding/live_pilot.py",
                                       "analyze","--output",str(analyses[0].parent)],
                                      capture_output=True,text=True,timeout=150)
                if result.returncode:
                    summary={"status":"REPLAY_FAILED","reason":result.stderr[-2500:]}
                else:
                    replay=json.loads(result.stdout)
                    summary={"status":"REPLAY_VERIFIED_BOUNDED_RESULT",
                             "paired_records":replay["paired_records"],
                             "summary":replay["summary"],
                             "registered_exploratory_gate_passed":replay["registered_exploratory_gate_passed"],
                             "nonclaims":{"general_reliability":replay["general_reliability"],
                                          "external_accuracy":replay["external_accuracy"]}}
        return record({**base,"artifact_sha256":digest,**summary})
    except Exception as exc:
        return record({"status":"OBSERVER_ERROR","launch_sha":FROZEN_LAUNCH_SHA,
                       "error_type":type(exc).__name__,"message":str(exc)[:500]})


if __name__=="__main__":
    raise SystemExit(main())
