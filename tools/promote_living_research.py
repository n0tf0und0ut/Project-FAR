#!/usr/bin/env python3
"""Fail-closed promoter for permanent Research-only PR #490."""
from __future__ import annotations
import argparse, hashlib, json, re, shlex, stat, subprocess, sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

POLICY=Path("research/living/promotion-policy-v1.0.json")
REVIEWS=Path("research/living/review-dispositions-v1.0.json")
AUTHS=Path("research/living/promotion-authorizations-v1.0.json")
LIFECYCLE=Path("research/living/lifecycle-v1.0.json")
ANCHOR="research/living/inbox/.rolling-pr-anchor.json"
CANDIDATES="research/living/inbox/candidates/"
PROPOSALS="research/living/inbox/promotion-proposals/"
PAYLOADS="research/living/inbox/promotion-payloads/"
MANIFESTS="research/living/promotions/"
CANDIDATE_RE=re.compile(r"FAR-LIT-[0-9A-F]{16}")
PROPOSAL_RE=re.compile(r"FAR-LIVING-PROP-[A-Z0-9][A-Z0-9._-]{0,63}")
HEX64_RE=re.compile(r"[0-9a-f]{64}")
HEX40_RE=re.compile(r"[0-9a-f]{40}")
AUTH_STATUS="ACCEPTED_FOR_MECHANICAL_PROMOTION"
PROV_KEYS=("question","execution","observation","discovery","replication","acceptance")

class PromotionError(RuntimeError): pass

def h(raw:bytes)->str: return hashlib.sha256(raw).hexdigest()
def canonical_json_sha(value:Any)->str:
    return h((json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode())
def _no_dupes(pairs):
    out={}
    for key,value in pairs:
        if key in out: raise PromotionError(f"duplicate JSON key: {key}")
        out[key]=value
    return out
def loadb(raw:bytes,label:str)->dict[str,Any]:
    try: value=json.loads(raw.decode("utf-8"),object_pairs_hook=_no_dupes)
    except PromotionError: raise
    except Exception as exc: raise PromotionError(f"invalid JSON in {label}: {exc}") from exc
    if not isinstance(value,dict): raise PromotionError(f"expected JSON object in {label}")
    return value
def load(path:Path)->dict[str,Any]: return loadb(path.read_bytes(),path.as_posix())
def dump(path:Path,value:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
def git(root:Path,*args:str)->str:
    result=subprocess.run(["git",*args],cwd=root,text=True,capture_output=True)
    if result.returncode: raise PromotionError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()

@dataclass(frozen=True)
class GitSource:
    root:Path; ref:str
    def resolve(self): return git(self.root,"rev-parse",f"{self.ref}^{{commit}}")
    def list(self,prefix): return [x for x in git(self.root,"ls-tree","-r","--name-only",self.ref,"--",prefix).splitlines() if x]
    def read(self,path):
        result=subprocess.run(["git","show",f"{self.ref}:{path}"],cwd=self.root,capture_output=True)
        return result.stdout if result.returncode==0 else None
@dataclass(frozen=True)
class MemorySource:
    files:dict[str,bytes]; sha:str
    def resolve(self): return self.sha
    def list(self,prefix): return sorted(x for x in self.files if x.startswith(prefix))
    def read(self,path): return self.files.get(path)

def safe(raw:str)->str:
    if not isinstance(raw,str) or not raw: raise PromotionError("empty repository path")
    if "\\" in raw or any(ord(ch)<32 or ord(ch)==127 for ch in raw): raise PromotionError(f"unsafe repository path: {raw!r}")
    path=PurePosixPath(raw)
    if path.is_absolute() or "." in path.parts or ".." in path.parts or any(not p or p.strip()!=p for p in path.parts): raise PromotionError(f"unsafe repository path: {raw!r}")
    value=path.as_posix()
    if value==ANCHOR: raise PromotionError("rolling PR anchor is never promotable")
    return value
def path_obj(root:Path,path:str)->Path:
    current=root
    for part in PurePosixPath(safe(path)).parts:
        current=current/part
        if current.is_symlink(): raise PromotionError(f"symlink path is not promotable: {path}")
    return current
def mainbytes(root:Path,path:str):
    target=path_obj(root,path)
    if not target.exists(): return None
    if not target.is_file(): raise PromotionError(f"canonical path is not a regular file: {path}")
    return target.read_bytes()
def blob_at(root:Path,ref:str,path:str):
    result=subprocess.run(["git","show",f"{ref}:{path}"],cwd=root,capture_output=True)
    return result.stdout if result.returncode==0 else None
def under(path:str,roots:list[str])->bool:
    parts=PurePosixPath(path).parts
    return any(parts[:len(PurePosixPath(root).parts)]==PurePosixPath(root).parts for root in roots)

def validate_policy(policy:dict[str,Any])->None:
    if policy.get("schema_version")!="1.1" or policy.get("program_id")!="FAR-LIVING-PROMOTION-001" or policy.get("authority")!="Research": raise PromotionError("promotion policy identity/version drift")
    if policy.get("source_pr")!=490 or policy.get("source_branch")!="automation/living-research-inbox": raise PromotionError("source identity policy drift")
    for key in ("canonical_write_roots","canonical_write_extensions","trusted_generated_paths","protected_exact_paths"):
        value=policy.get(key)
        if not isinstance(value,list) or not value or any(not isinstance(x,str) or not x for x in value) or len(value)!=len(set(value)): raise PromotionError(f"invalid promotion policy list: {key}")
def validate_target(target:str,policy:dict[str,Any])->None:
    if not under(target,policy["canonical_write_roots"]): raise PromotionError(f"target outside automatic roots: {target}")
    if PurePosixPath(target).suffix.lower() not in set(policy["canonical_write_extensions"]): raise PromotionError(f"target extension is not mechanically promotable: {target}")
    if target in set(policy["protected_exact_paths"]): raise PromotionError(f"protected control-plane path is not mechanically promotable: {target}")
    if target in set(policy["trusted_generated_paths"]): raise PromotionError(f"generated reconciliation output is not a proposal payload: {target}")

def registries(root:Path):
    lifecycle=load(root/LIFECYCLE)
    stages={x["id"]:bool(x.get("automation_may_enter")) for x in lifecycle.get("stages",[]) if isinstance(x,dict) and isinstance(x.get("id"),str)}
    if stages.get("DISCOVERED") is not True or stages.get("PROMOTION_PROPOSED") is not False: raise PromotionError("lifecycle automation boundary drift")
    review_reg=load(root/REVIEWS); rows=review_reg.get("reviewed_candidates")
    if not isinstance(rows,list): raise PromotionError("reviewed_candidates must be an array")
    reviews={}
    for row in rows:
        if not isinstance(row,dict): raise PromotionError("malformed review row")
        cid=row.get("candidate_id")
        if not isinstance(cid,str) or CANDIDATE_RE.fullmatch(cid) is None or cid in reviews: raise PromotionError(f"invalid or duplicate reviewed candidate id: {cid!r}")
        for field in ("source_key","disposition","review_basis"):
            if not isinstance(row.get(field),str) or not row[field].strip(): raise PromotionError(f"{cid}: review registry missing {field}")
        reviews[cid]=row
    auth_reg=load(root/AUTHS); rows=auth_reg.get("authorizations")
    if auth_reg.get("schema_version")!="1.1" or auth_reg.get("program_id")!="FAR-LIVING-PROMOTION-AUTHORIZATIONS-001" or auth_reg.get("authority")!="Research" or not isinstance(rows,list): raise PromotionError("authorization registry identity/version drift")
    auths={}
    for row in rows:
        if not isinstance(row,dict): raise PromotionError("malformed authorization row")
        pid=row.get("proposal_id"); cid=row.get("candidate_id")
        if not isinstance(pid,str) or PROPOSAL_RE.fullmatch(pid) is None or pid in auths: raise PromotionError(f"invalid or duplicate proposal authorization id: {pid!r}")
        if not isinstance(cid,str) or CANDIDATE_RE.fullmatch(cid) is None: raise PromotionError(f"{pid}: invalid candidate id")
        for field in ("proposal_sha256","candidate_sha256","operations_sha256"):
            if not isinstance(row.get(field),str) or HEX64_RE.fullmatch(row[field]) is None: raise PromotionError(f"{pid}: invalid authorization {field}")
        if row.get("lifecycle_stage")!="PROMOTION_PROPOSED" or row.get("authorization_status")!=AUTH_STATUS: raise PromotionError(f"{pid}: authorization stage/status drift")
        prov=row.get("provenance_sha256")
        if not isinstance(prov,dict) or set(prov)!=set(PROV_KEYS) or any(not isinstance(prov[k],str) or HEX64_RE.fullmatch(prov[k]) is None for k in PROV_KEYS): raise PromotionError(f"{pid}: authorization provenance hashes incomplete")
        auths[pid]=row
    return reviews,auths

def validate_proposal(root:Path,src,path:str,raw:bytes,auth:dict[str,Any],policy:dict[str,Any]):
    proposal=loadb(raw,path); pid=proposal.get("proposal_id"); cid=proposal.get("candidate_id")
    if not isinstance(pid,str) or PROPOSAL_RE.fullmatch(pid) is None or path!=f"{PROPOSALS}{pid}.json": raise PromotionError(f"invalid proposal identity/path: {path}")
    if not isinstance(cid,str) or CANDIDATE_RE.fullmatch(cid) is None: raise PromotionError(f"{pid}: invalid candidate id")
    if auth.get("proposal_sha256")!=h(raw) or auth.get("candidate_id")!=cid or proposal.get("lifecycle_stage")!="PROMOTION_PROPOSED": raise PromotionError(f"{pid}: protected authorization/stage mismatch")
    candidate=src.read(f"{CANDIDATES}{cid}.json")
    if candidate is None or proposal.get("candidate_sha256")!=h(candidate) or auth.get("candidate_sha256")!=h(candidate): raise PromotionError(f"{pid}: candidate binding mismatch")
    provenance=proposal.get("provenance")
    if not isinstance(provenance,dict) or set(provenance)!=set(PROV_KEYS): raise PromotionError(f"{pid}: incomplete provenance")
    normalized_prov={}
    for key in PROV_KEYS:
        item=provenance[key]
        if not isinstance(item,dict) or set(item)!={"path","sha256"}: raise PromotionError(f"{pid}: malformed {key} provenance")
        prov_path=safe(item.get("path")); expected=item.get("sha256"); raw_prov=mainbytes(root,prov_path)
        if raw_prov is None or not isinstance(expected,str) or HEX64_RE.fullmatch(expected) is None or h(raw_prov)!=expected or auth["provenance_sha256"].get(key)!=expected: raise PromotionError(f"{pid}: {key} provenance hash mismatch")
        normalized_prov[key]={"path":prov_path,"sha256":expected}
    operations=proposal.get("operations")
    if not isinstance(operations,list) or not operations or canonical_json_sha(operations)!=auth.get("operations_sha256"): raise PromotionError(f"{pid}: operation-set binding mismatch")
    seen=set(); normalized=[]
    for operation in operations:
        if not isinstance(operation,dict) or operation.get("op")!="write_file": raise PromotionError(f"{pid}: only write_file is allowed")
        target=safe(operation.get("path")); source_path=safe(operation.get("source_path")); validate_target(target,policy)
        if target in seen: raise PromotionError(f"{pid}: duplicate target: {target}")
        seen.add(target)
        if not source_path.startswith(f"{PAYLOADS}{pid}/"): raise PromotionError(f"{pid}: payload outside proposal")
        payload=src.read(source_path)
        if payload is None or operation.get("result_sha256")!=h(payload): raise PromotionError(f"{pid}: payload hash mismatch: {target}")
        before=mainbytes(root,target); pre="ABSENT" if before is None else h(before)
        if operation.get("expected_main_sha256")!=pre: raise PromotionError(f"{pid}: stale main preimage: {target}")
        if before!=payload: normalized.append({"op":"write_file","path":target,"source_path":source_path,"expected_main_sha256":pre,"result_sha256":h(payload)})
    return {"proposal_id":pid,"candidate_id":cid,"proposal_sha256":h(raw),"candidate_sha256":h(candidate),"operations_sha256":auth["operations_sha256"],"operations":normalized,"provenance":normalized_prov}

def base_plan(source_sha,base_sha,policy,manifest_path):
    return {"schema_version":"1.1","source_pr":490,"source_branch":policy["source_branch"],"source_head_sha":source_sha,"base_main_sha":base_sha,"already_promoted":False,"actionable":False,"fatal":False,"fatal_blocks":[],"snapshot_candidates":[],"canonical_proposals":[],"review_required":[],"unauthorized_proposals":[],"manifest_path":manifest_path}
def build(root:Path,src,source_sha:str,base_sha:str):
    policy=load(root/POLICY); validate_policy(policy)
    if src.resolve()!=source_sha: raise PromotionError("source ref moved")
    if HEX40_RE.fullmatch(source_sha) is None or HEX40_RE.fullmatch(base_sha) is None or git(root,"rev-parse","HEAD^{commit}")!=base_sha: raise PromotionError("invalid or stale base/source commit")
    manifest_path=f"{MANIFESTS}{source_sha}.json"; plan=base_plan(source_sha,base_sha,policy,manifest_path)
    existing=root/manifest_path
    if existing.is_file():
        manifest=load(existing)
        if manifest.get("program_id")!="FAR-LIVING-PROMOTION-001" or manifest.get("source_head_sha")!=source_sha or manifest.get("source_pr")!=490 or manifest.get("source_branch")!=policy["source_branch"]: raise PromotionError("existing promotion manifest identity mismatch")
        plan["already_promoted"]=True; return plan
    reviews,auths=registries(root); allowed=set(policy.get("snapshot_review_dispositions",[])); snapshots=[]
    for path in src.list(CANDIDATES):
        raw=src.read(path)
        if raw is None: continue
        candidate=loadb(raw,path); cid=candidate.get("candidate_id")
        if not isinstance(cid,str) or CANDIDATE_RE.fullmatch(cid) is None or path!=f"{CANDIDATES}{cid}.json": raise PromotionError(f"candidate identity/path mismatch: {path}")
        review=reviews.get(cid)
        if not review or review.get("disposition") not in allowed: continue
        if candidate.get("authority")!="Research" or candidate.get("lifecycle",{}).get("stage")!="DISCOVERED" or candidate.get("source_key")!=review.get("source_key"): raise PromotionError(f"{cid}: reviewed candidate identity/stage drift")
        current=mainbytes(root,path)
        if current!=raw: snapshots.append({"candidate_id":cid,"path":path,"source_key":candidate.get("source_key"),"disposition":review["disposition"],"review_basis":review["review_basis"],"source_sha256":h(raw),"expected_main_sha256":"ABSENT" if current is None else h(current)})
    pending=[]; state=src.read("research/living/repository-state-v1.0.json")
    if state:
        for item in loadb(state,"source repository state").get("core_claim_review_queue",[]):
            if isinstance(item,dict) and isinstance(item.get("candidate_id"),str) and item["candidate_id"] not in reviews: pending.append({key:item.get(key,[]) for key in ("candidate_id","claim_ids","downstream_claim_ids","attention_terms")})
    proposals=[]; unauthorized=[]; blocks=[]; seen_pids=set()
    for path in src.list(PROPOSALS):
        raw=src.read(path)
        if raw is None: continue
        try:
            item=loadb(raw,path); pid=item.get("proposal_id")
            if not isinstance(pid,str) or PROPOSAL_RE.fullmatch(pid) is None or pid in seen_pids or path!=f"{PROPOSALS}{pid}.json": raise PromotionError(f"proposal identity/path mismatch: {path}")
            seen_pids.add(pid)
            if pid not in auths: unauthorized.append(pid); continue
            normalized=validate_proposal(root,src,path,raw,auths[pid],policy)
            if normalized["operations"]: proposals.append(normalized)
        except PromotionError as exc: blocks.append(str(exc))
    targets=[op["path"] for item in proposals for op in item["operations"]]
    if len(targets)!=len(set(targets)): blocks.append("canonical proposals collide on a target path")
    plan.update(snapshot_candidates=sorted(snapshots,key=lambda x:x["candidate_id"]),canonical_proposals=sorted(proposals,key=lambda x:x["proposal_id"]),review_required=sorted(pending,key=lambda x:x["candidate_id"]),unauthorized_proposals=sorted(set(unauthorized)),fatal=bool(blocks),fatal_blocks=sorted(blocks))
    plan["actionable"]=bool(snapshots or proposals) and not blocks
    return plan

def planned_paths(plan): return {safe(x["path"]) for x in plan["snapshot_candidates"]}|{safe(op["path"]) for item in plan["canonical_proposals"] for op in item["operations"]}
def materialize(root:Path,src,plan):
    if plan.get("fatal") or not plan.get("actionable"): raise PromotionError("plan is not materializable")
    if src.resolve()!=plan["source_head_sha"] or git(root,"rev-parse","HEAD^{commit}")!=plan["base_main_sha"]: raise PromotionError("source/base moved")
    if len(planned_paths(plan))!=sum(len(x["operations"]) for x in plan["canonical_proposals"])+len(plan["snapshot_candidates"]): raise PromotionError("duplicate materialization target")
    for item in plan["snapshot_candidates"]:
        path=safe(item["path"]); raw=src.read(path); current=mainbytes(root,path); pre="ABSENT" if current is None else h(current)
        if raw is None or h(raw)!=item["source_sha256"] or pre!=item["expected_main_sha256"]: raise PromotionError(f"candidate changed: {path}")
        target=path_obj(root,path); target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
    for proposal in plan["canonical_proposals"]:
        for operation in proposal["operations"]:
            path=safe(operation["path"]); raw=src.read(safe(operation["source_path"])); current=mainbytes(root,path); pre="ABSENT" if current is None else h(current)
            if raw is None or h(raw)!=operation["result_sha256"] or pre!=operation["expected_main_sha256"]: raise PromotionError(f"proposal changed: {path}")
            target=path_obj(root,path); target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
    if (root/ANCHOR).exists(): raise PromotionError("anchor leaked into promotion")

def staged_paths(root): return {x for x in git(root,"diff","--cached","--name-only","--no-renames","--").splitlines() if x}
def index_bytes(root,path):
    result=subprocess.run(["git","show",f":{path}"],cwd=root,capture_output=True)
    return result.stdout if result.returncode==0 else None
def install_precommit_hook(root:Path,plan_path:Path):
    hook=root/".git/hooks/pre-commit"; hook.parent.mkdir(parents=True,exist_ok=True)
    hook.write_text("#!/usr/bin/env bash\nset -euo pipefail\n"+f"python tools/promote_living_research.py precommit --plan {shlex.quote(str(plan_path.resolve()))}\n",encoding="utf-8")
    hook.chmod(hook.stat().st_mode|stat.S_IXUSR)
def precommit_seal(root:Path,plan:dict[str,Any],refresh_main=True):
    if git(root,"rev-parse","HEAD^{commit}")!=plan["base_main_sha"]: raise PromotionError("pre-commit base moved")
    if refresh_main:
        git(root,"fetch","--no-tags","origin","+refs/heads/main:refs/remotes/origin/main")
        current=git(root,"rev-parse","origin/main^{commit}")
        if current!=plan["base_main_sha"]: raise PromotionError(f"main advanced after analysis: {current}")
    policy=load(root/POLICY); validate_policy(policy); required=planned_paths(plan); generated={safe(x) for x in policy["trusted_generated_paths"]}; staged=staged_paths(root)
    if not required<=staged: raise PromotionError("planned promotion path missing from staged diff")
    unexpected=sorted(staged-required-generated)
    if unexpected: raise PromotionError("unexpected staged paths: "+", ".join(unexpected))
    deleted=[x for x in git(root,"diff","--cached","--name-only","--diff-filter=D","--").splitlines() if x]
    if deleted: raise PromotionError("promotion may not delete files: "+", ".join(sorted(deleted)))
    sealed=[]
    for path in sorted(staged):
        raw=index_bytes(root,path)
        if raw is None: raise PromotionError(f"unable to read staged path: {path}")
        sealed.append({"path":path,"sha256":h(raw),"kind":"trusted_generated" if path in generated and path not in required else "planned"})
    by_path={x["path"]:x for x in sealed}
    for item in plan["snapshot_candidates"]:
        path=safe(item["path"]); before=blob_at(root,plan["base_main_sha"],path); pre="ABSENT" if before is None else h(before)
        if path not in by_path or by_path[path]["sha256"]!=item["source_sha256"] or pre!=item["expected_main_sha256"]: raise PromotionError(f"staged snapshot/preimage mismatch: {path}")
    for proposal in plan["canonical_proposals"]:
        for operation in proposal["operations"]:
            path=safe(operation["path"]); before=blob_at(root,plan["base_main_sha"],path); pre="ABSENT" if before is None else h(before)
            if path not in by_path or by_path[path]["sha256"]!=operation["result_sha256"] or pre!=operation["expected_main_sha256"]: raise PromotionError(f"staged proposal/preimage mismatch: {path}")
    manifest={"schema_version":"1.1","program_id":"FAR-LIVING-PROMOTION-001","authority":"Research","source_pr":490,"source_branch":plan["source_branch"],"source_head_sha":plan["source_head_sha"],"base_main_sha":plan["base_main_sha"],"snapshot_candidates":plan["snapshot_candidates"],"canonical_proposals":plan["canonical_proposals"],"review_required_count_at_analysis":len(plan["review_required"]),"sealed_files":sealed}
    manifest_path=safe(plan["manifest_path"]); dump(root/manifest_path,manifest); git(root,"add","--",manifest_path)
    if staged_paths(root)!=staged|{manifest_path}: raise PromotionError("manifest changed staged path set unexpectedly")
    unstaged={x for x in git(root,"diff","--name-only","--").splitlines() if x}; untracked={x for x in git(root,"ls-files","--others","--exclude-standard").splitlines() if x}
    if unstaged or untracked: raise PromotionError(f"unsealed worktree residue: unstaged={sorted(unstaged)} untracked={sorted(untracked)}")
    return manifest

def verify_promotion_head(root:Path)->list[str]:
    try: git(root,"rev-parse","origin/main^{commit}")
    except PromotionError: return []
    base=git(root,"merge-base","HEAD","origin/main")
    manifests=[x for x in git(root,"diff","--name-status","--no-renames",base,"HEAD","--",MANIFESTS).splitlines() if x]
    if not manifests: return []
    try: git(root,"fetch","--no-tags","origin","+refs/heads/main:refs/remotes/origin/main")
    except PromotionError as exc: return [f"could not refresh protected main: {exc}"]
    base=git(root,"merge-base","HEAD","origin/main"); current_main=git(root,"rev-parse","origin/main^{commit}")
    if current_main!=base: return [f"living promotion base is stale: merge-base {base}, current main {current_main}"]
    manifests=[x for x in git(root,"diff","--name-status","--no-renames",base,"HEAD","--",MANIFESTS).splitlines() if x]
    try:
        if len(manifests)!=1 or not manifests[0].startswith("A\t"): raise PromotionError("promotion must add exactly one new promotion manifest")
        manifest_path=manifests[0].split("\t",1)[1]; manifest=load(root/safe(manifest_path)); source=manifest.get("source_head_sha")
        if manifest_path!=f"{MANIFESTS}{source}.json" or manifest.get("schema_version")!="1.1" or manifest.get("program_id")!="FAR-LIVING-PROMOTION-001" or manifest.get("source_pr")!=490 or manifest.get("source_branch")!="automation/living-research-inbox": raise PromotionError("promotion manifest identity mismatch")
        if manifest.get("base_main_sha")!=base: raise PromotionError("promotion manifest base mismatch")
        if int(git(root,"rev-list","--count",f"{base}..HEAD"))!=1 or git(root,"rev-parse","HEAD^")!=base: raise PromotionError("promotion branch must contain exactly one commit on its base")
        rows=manifest.get("sealed_files")
        if not isinstance(rows,list) or not rows: raise PromotionError("promotion sealed_files missing")
        sealed={}
        for row in rows:
            if not isinstance(row,dict) or set(row)!={"path","sha256","kind"}: raise PromotionError("malformed sealed row")
            path=safe(row["path"])
            if path in sealed or not isinstance(row["sha256"],str) or HEX64_RE.fullmatch(row["sha256"]) is None: raise PromotionError(f"malformed/duplicate sealed path: {path}")
            raw=blob_at(root,"HEAD",path)
            if raw is None or h(raw)!=row["sha256"]: raise PromotionError(f"sealed HEAD hash mismatch: {path}")
            sealed[path]=row
        changed={x for x in git(root,"diff","--name-only","--no-renames",base,"HEAD","--").splitlines() if x}
        if changed!=set(sealed)|{manifest_path}: raise PromotionError("promotion commit changed paths outside sealed manifest")
        for item in manifest.get("snapshot_candidates",[]):
            path=safe(item["path"]); before=blob_at(root,base,path); pre="ABSENT" if before is None else h(before)
            if path not in sealed or sealed[path]["sha256"]!=item["source_sha256"] or pre!=item["expected_main_sha256"]: raise PromotionError(f"snapshot seal/preimage mismatch: {path}")
        for proposal in manifest.get("canonical_proposals",[]):
            for operation in proposal.get("operations",[]):
                path=safe(operation["path"]); before=blob_at(root,base,path); pre="ABSENT" if before is None else h(before)
                if path not in sealed or sealed[path]["sha256"]!=operation["result_sha256"] or pre!=operation["expected_main_sha256"]: raise PromotionError(f"proposal seal/preimage mismatch: {path}")
        return []
    except (PromotionError,KeyError,TypeError,ValueError) as exc: return [str(exc)]

def body(plan):
    return f"""## Result\n\nGoverned promotion from permanent living-research PR #490 head `{plan['source_head_sha']}` against `main` `{plan['base_main_sha']}`. Source-branch content was treated as untrusted Research-only data.\n\n- reviewed Research snapshots: {len(plan['snapshot_candidates'])}\n- exact protected-authorized canonical proposals: {len(plan['canonical_proposals'])}\n- unreviewed claim candidates left pending: {len(plan['review_required'])}\n\n## Governance boundary\n\nResearch snapshots do not change scientific status. Canonical edits require exact protected-main authorization binding proposal, candidate, operation-set, lifecycle provenance, preimage, and payload hashes. A pre-commit seal rejects every unplanned staged byte and stale base. Protected `merge-authority` independently verifies the final promotion manifest and exact one-commit diff.\n"""
def cli():
    parser=argparse.ArgumentParser(); commands=parser.add_subparsers(dest="cmd",required=True)
    q=commands.add_parser("analyze"); [q.add_argument(x,required=True) for x in ("--source-ref","--source-sha","--base-sha","--output")]
    q=commands.add_parser("materialize"); q.add_argument("--source-ref",required=True); q.add_argument("--plan",required=True)
    q=commands.add_parser("precommit"); q.add_argument("--plan",required=True)
    commands.add_parser("verify-head")
    q=commands.add_parser("pr-body"); q.add_argument("--plan",required=True); q.add_argument("--output",required=True)
    args=parser.parse_args(); root=Path.cwd().resolve()
    try:
        if args.cmd=="analyze":
            plan=build(root,GitSource(root,args.source_ref),args.source_sha,args.base_sha); dump(Path(args.output),plan); print(json.dumps(plan,indent=2,sort_keys=True)); return 2 if plan.get("fatal") else 0
        if args.cmd=="materialize":
            plan=load(Path(args.plan)); materialize(root,GitSource(root,args.source_ref),plan); install_precommit_hook(root,Path(args.plan)); return 0
        if args.cmd=="precommit": precommit_seal(root,load(Path(args.plan))); return 0
        if args.cmd=="verify-head":
            errors=verify_promotion_head(root)
            if errors: raise PromotionError("; ".join(errors))
            return 0
        plan=load(Path(args.plan)); Path(args.output).write_text(body(plan),encoding="utf-8"); return 0
    except PromotionError as exc:
        print(f"living-research promotion failed closed: {exc}",file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(cli())
