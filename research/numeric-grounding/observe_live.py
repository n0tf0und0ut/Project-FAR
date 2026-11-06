"""Read-only replay of the preserved original numeric-grounding push-run evidence.

The default verifies the exact original artifact retrieved through authenticated
GitHub download. --remote independently queries that same launch. Neither path
runs a model or revises any preregistered experiment input or original raw byte.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
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
PRESERVED_ARCHIVE = Path(__file__).with_name("original-live-42090379885.zip.b64")
PRESERVED_SHA256 = "b731cfb1730f443d0f06eff07535fe23cf09c16b9beec6d4aa0c30613b7b89a3"
ORIGINAL_MEMBERS={f"{prefix}{index:02d}-{arm}.json" for prefix in ("A","U")
                  for index in range(1,9) for arm in ("control","treatment")}|{"analysis.json","state.json"}


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
    # An observation must never be marked green when the launch is unverified.
    return 0 if value.get("status") == "REPLAY_VERIFIED_BOUNDED_RESULT" else 1


def replay_archive(raw):
    with tempfile.TemporaryDirectory() as dirname:
        target=Path(dirname)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names=z.namelist()
            # This observer is scoped to one frozen launch, whose exact 34
            # root-level members are known. No generic extraction is needed.
            if len(names)!=len(set(names)) or set(names)!=ORIGINAL_MEMBERS:
                raise ValueError("duplicate, missing or unexpected original artifact members")
            for item in z.infolist():
                if item.file_size>1_000_000:
                    raise ValueError("oversized evidence member")
                (target/item.filename).write_bytes(z.read(item))
        analyses=list(target.rglob("analysis.json"))
        state=list(target.rglob("state.json"))
        if len(analyses)!=1:
            summary={"status":"INCOMPLETE_EXPERIMENT","state":json.loads(state[0].read_text()) if len(state)==1 else None}
        else:
            result=subprocess.run([sys.executable,str(Path(__file__).with_name("live_pilot.py")),
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
                                      "external_accuracy":replay["external_accuracy"],
                                      "trusted_execution_attestation":replay["trusted_execution_attestation"]}}
    return summary


def preserved_observation():
    raw=base64.b64decode(PRESERVED_ARCHIVE.read_bytes().strip(),validate=True)
    if hashlib.sha256(raw).hexdigest()!=PRESERVED_SHA256:
        raise ValueError("preserved original artifact digest mismatch")
    return record({"launch_sha":FROZEN_LAUNCH_SHA,"run_id":42090379885,
                   "url":f"https://github.com/{REPO}/actions/runs/42090379885",
                   "workflow_status":"completed","workflow_conclusion":"failure",
                   "workflow_failure":"original derived report ordering; corrected by post-execution verifier",
                   "artifact_id":13445236161,"artifact_sha256":PRESERVED_SHA256,
                   "evidence_access":"REPOSITORY_PRESERVED_ORIGINAL_AUTHENTICATED_DOWNLOAD",
                   **replay_archive(raw)})


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote",action="store_true",help="inspect original GitHub run and download instead of pinned preserved bytes")
    opts=parser.parse_args(argv)
    if not opts.remote:
        try:
            return preserved_observation()
        except Exception as exc:
            return record({"status":"PRESERVED_REPLAY_FAILED","launch_sha":FROZEN_LAUNCH_SHA,
                           "error_type":type(exc).__name__,"message":str(exc)[:500]})
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
        if digest!=PRESERVED_SHA256:
            raise ValueError("remote original artifact digest mismatch")
        summary=replay_archive(raw)
        return record({**base,"artifact_sha256":digest,**summary})
    except Exception as exc:
        return record({"status":"OBSERVER_ERROR","launch_sha":FROZEN_LAUNCH_SHA,
                       "error_type":type(exc).__name__,"message":str(exc)[:500]})


if __name__=="__main__":
    raise SystemExit(main())
