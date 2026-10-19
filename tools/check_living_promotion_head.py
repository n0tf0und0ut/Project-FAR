#!/usr/bin/env python3
"""Independent fail-closed verifier for governed living-research promotion commits."""
from __future__ import annotations
import hashlib, io, json, os, re, subprocess, sys, tarfile, tempfile
from pathlib import Path, PurePosixPath
from typing import Any

MANIFESTS="research/living/promotions/"
CANDIDATES="research/living/inbox/candidates/"
POLICY="research/living/promotion-policy-v1.0.json"
REVIEWS="research/living/review-dispositions-v1.0.json"
AUTHS="research/living/promotion-authorizations-v1.0.json"
SNAPSHOT_AUTHS="research/living/snapshot-authorizations-v1.0.json"
SOURCE_BRANCH="automation/living-research-inbox"
AUTH_STATUS="ACCEPTED_FOR_MECHANICAL_PROMOTION"
SNAPSHOT_STATUS="ACCEPTED_FOR_MECHANICAL_SNAPSHOT"
PROV_KEYS=("question","execution","observation","discovery","replication","acceptance")
HEX40=re.compile(r"[0-9a-f]{40}")
HEX64=re.compile(r"[0-9a-f]{64}")
CID_RE=re.compile(r"FAR-LIT-[0-9A-F]{16}")
ASCII_PATH=re.compile(r"[A-Za-z0-9._/-]+")

class IntegrityError(RuntimeError): pass

def sha(raw:bytes)->str: return hashlib.sha256(raw).hexdigest()
def canonical_sha(value:Any)->str: return sha((json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode())
def _pairs(pairs):
    out={}
    for key,value in pairs:
        if key in out: raise IntegrityError(f"duplicate JSON key: {key}")
        out[key]=value
    return out
def loads(raw:bytes,label:str):
    try: value=json.loads(raw.decode("utf-8"),object_pairs_hook=_pairs,parse_constant=lambda x: (_ for _ in ()).throw(IntegrityError(f"non-finite JSON constant: {x}")))
    except IntegrityError: raise
    except Exception as exc: raise IntegrityError(f"invalid JSON in {label}: {exc}") from exc
    if not isinstance(value,dict): raise IntegrityError(f"expected object in {label}")
    return value
def run(root:Path,*args:str,check=True):
    result=subprocess.run(["git",*args],cwd=root,text=True,capture_output=True)
    if check and result.returncode: raise IntegrityError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result
def git(root:Path,*args:str)->str: return run(root,*args).stdout.strip()
def blob(root:Path,ref:str,path:str):
    result=subprocess.run(["git","show",f"{ref}:{path}"],cwd=root,capture_output=True)
    return result.stdout if result.returncode==0 else None
def safe(raw:Any)->str:
    if not isinstance(raw,str) or not raw or ASCII_PATH.fullmatch(raw) is None: raise IntegrityError(f"unsafe repository path: {raw!r}")
    p=PurePosixPath(raw)
    if p.is_absolute() or "." in p.parts or ".." in p.parts or any(not x or x.strip()!=x for x in p.parts): raise IntegrityError(f"unsafe repository path: {raw!r}")
    return p.as_posix()
def canonical_target(path:str,policy:dict[str,Any])->None:
    roots=policy.get("canonical_write_roots",[]); exts=policy.get("canonical_write_extensions",[]); parts=PurePosixPath(path).parts
    if not any(parts[:len(PurePosixPath(r).parts)]==PurePosixPath(r).parts for r in roots): raise IntegrityError(f"target outside automatic roots: {path}")
    if PurePosixPath(path).suffix.lower() not in set(exts): raise IntegrityError(f"target extension not allowed: {path}")
    if path in set(policy.get("protected_exact_paths",[])) or path in set(policy.get("trusted_generated_paths",[])): raise IntegrityError(f"protected target: {path}")
    if any(path.startswith(prefix) for prefix in policy.get("canonical_forbidden_prefixes",[])): raise IntegrityError(f"governance/self-modifying target: {path}")

def _verification_ref(root:Path)->tuple[str,str,bool]:
    name=os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME") or ""
    promotion=name.startswith("automation/living-promotion-")
    head_ref=os.environ.get("GITHUB_HEAD_REF") or ""
    if head_ref:
        remote=f"refs/remotes/origin/{head_ref}"
        if run(root,"rev-parse",f"{remote}^{{commit}}",check=False).returncode==0:
            return remote,name,promotion
        parents=git(root,"rev-list","--parents","-n","1","HEAD").split()
        if len(parents)==3:
            return parents[2],name,promotion
        if promotion:
            raise IntegrityError(f"promotion PR head is unavailable locally: {head_ref}")
    return "HEAD",name,promotion

def _verify_generated_outputs(root:Path,base:str,head:str,planned:set[str],generated:set[str])->None:
    """Rebuild trusted generated outputs from the same pre-reconciliation state as promotion.

    Promotion reconciliation runs after authorized planned files are materialized on the frozen
    base and before generated outputs or the promotion manifest are committed. Replaying the
    reconciler from the finished promotion head is not equivalent because reconciliation state
    intentionally records what changed since the previous reconciliation.
    """
    archive=subprocess.run(["git","archive","--format=tar",base],cwd=root,capture_output=True)
    if archive.returncode: raise IntegrityError("cannot archive exact promotion base for generated-output verification")
    with tempfile.TemporaryDirectory(prefix="far-promotion-reconcile-") as td:
        temp=Path(td)
        with tarfile.open(fileobj=io.BytesIO(archive.stdout),mode="r:") as tar: tar.extractall(temp,filter="data")
        for path in sorted(planned):
            raw=blob(root,head,path)
            if raw is None: raise IntegrityError(f"planned promotion output is unavailable at HEAD: {path}")
            target=temp/path
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(raw)
        from tools.reconcile_living_repo import reconcile
        reconcile(temp)
        from tools import reconcile_research_corpus as corpus
        corpus_outputs = {str(corpus.OUTPUT), str(corpus.STATUS)}
        if generated & corpus_outputs:
            if not corpus_outputs <= generated:
                raise IntegrityError("promotion must replay both dependent corpus views")
            data = corpus.load_json(corpus.CORPUS, temp)
            errors = corpus.validate(data, temp)
            if errors:
                raise IntegrityError("promotion corpus inputs invalid: " + "; ".join(errors))
            for path, raw in corpus.expected_outputs(data, temp).items():
                (temp / path).write_bytes(raw)
        for path in sorted(generated):
            expected=temp/path
            actual=blob(root,head,path)
            expected_raw=expected.read_bytes() if expected.is_file() else None
            if actual!=expected_raw: raise IntegrityError(f"trusted generated output is not canonical reconciliation output: {path}")

def verify(root:Path)->list[str]:
    root=root.resolve()
    try:
        verify_ref,_,promotion_ref=_verification_ref(root)
    except IntegrityError as exc:
        return [str(exc)]
    if run(root,"rev-parse","origin/main^{commit}",check=False).returncode:
        return ["promotion ref cannot verify origin/main"] if promotion_ref else []
    head=git(root,"rev-parse",f"{verify_ref}^{{commit}}")
    base=git(root,"merge-base",head,"origin/main")
    manifest_changes=[x for x in git(root,"diff","--name-status","--no-renames",base,head,"--",MANIFESTS).splitlines() if x]
    if not manifest_changes:
        return ["promotion ref is missing its promotion manifest"] if promotion_ref else []
    try:
        current=git(root,"rev-parse","origin/main^{commit}")
        if current!=base: raise IntegrityError(f"living promotion base is stale: merge-base {base}, current main {current}")
        if len(manifest_changes)!=1 or not manifest_changes[0].startswith("A\t"): raise IntegrityError("promotion must add exactly one manifest")
        manifest_path=manifest_changes[0].split("\t",1)[1]; manifest_raw=blob(root,head,safe(manifest_path)); manifest=loads(manifest_raw or b"",manifest_path); source=manifest.get("source_head_sha")
        if manifest_path!=f"{MANIFESTS}{source}.json" or manifest.get("schema_version")!="1.1" or manifest.get("program_id")!="FAR-LIVING-PROMOTION-001" or manifest.get("authority")!="Research" or manifest.get("source_pr")!=490 or manifest.get("source_branch")!=SOURCE_BRANCH or HEX40.fullmatch(str(source)) is None: raise IntegrityError("promotion manifest identity mismatch")
        if manifest.get("base_main_sha")!=base: raise IntegrityError("promotion manifest base mismatch")
        if int(git(root,"rev-list","--count",f"{base}..{head}"))!=1 or git(root,"rev-parse",f"{head}^")!=base: raise IntegrityError("promotion must be exactly one commit on its base")
        policy_raw=blob(root,base,POLICY); reviews_raw=blob(root,base,REVIEWS); auths_raw=blob(root,base,AUTHS); snapshot_auths_raw=blob(root,base,SNAPSHOT_AUTHS)
        if None in (policy_raw,reviews_raw,auths_raw,snapshot_auths_raw): raise IntegrityError("promotion base lacks governing registries")
        policy=loads(policy_raw,POLICY)
        if policy.get("schema_version")!="1.1" or policy.get("program_id")!="FAR-LIVING-PROMOTION-001" or policy.get("source_pr")!=490 or policy.get("source_branch")!=SOURCE_BRANCH: raise IntegrityError("base promotion policy drift")
        if policy.get("snapshot_requires_explicit_authorization") is not True or policy.get("snapshot_authorization_registry")!=SNAPSHOT_AUTHS: raise IntegrityError("base snapshot-authorization policy drift")
        review_data=loads(reviews_raw,REVIEWS); review_rows=review_data.get("reviewed_candidates",[])
        if not isinstance(review_rows,list): raise IntegrityError("base review registry malformed")
        reviews={x.get("candidate_id"):x for x in review_rows if isinstance(x,dict) and isinstance(x.get("candidate_id"),str)}
        if len(reviews)!=len(review_rows): raise IntegrityError("base review registry duplicate/malformed")
        auth_data=loads(auths_raw,AUTHS); auth_rows=auth_data.get("authorizations",[])
        if auth_data.get("schema_version")!="1.1" or auth_data.get("program_id")!="FAR-LIVING-PROMOTION-AUTHORIZATIONS-001" or auth_data.get("authority")!="Research" or not isinstance(auth_rows,list): raise IntegrityError("base authorization registry drift")
        auths={x.get("proposal_id"):x for x in auth_rows if isinstance(x,dict) and isinstance(x.get("proposal_id"),str)}
        if len(auths)!=len(auth_rows): raise IntegrityError("base authorization registry duplicate/malformed")
        snapshot_auth_data=loads(snapshot_auths_raw,SNAPSHOT_AUTHS); snapshot_auth_rows=snapshot_auth_data.get("authorizations",[])
        if snapshot_auth_data.get("schema_version")!="1.1" or snapshot_auth_data.get("program_id")!="FAR-LIVING-SNAPSHOT-AUTHORIZATIONS-001" or snapshot_auth_data.get("authority")!="Research" or not isinstance(snapshot_auth_rows,list): raise IntegrityError("base snapshot authorization registry drift")
        snapshot_auths={x.get("candidate_id"):x for x in snapshot_auth_rows if isinstance(x,dict) and isinstance(x.get("candidate_id"),str)}
        if len(snapshot_auths)!=len(snapshot_auth_rows): raise IntegrityError("base snapshot authorization registry duplicate/malformed")
        sealed_rows=manifest.get("sealed_files")
        if not isinstance(sealed_rows,list) or not sealed_rows: raise IntegrityError("sealed_files missing")
        sealed={}
        for row in sealed_rows:
            if not isinstance(row,dict) or set(row)!={"path","sha256","kind"}: raise IntegrityError("malformed sealed row")
            path=safe(row["path"]); digest=row["sha256"]
            if path in sealed or not isinstance(digest,str) or HEX64.fullmatch(digest) is None or row["kind"] not in {"planned","trusted_generated"}: raise IntegrityError(f"invalid sealed row: {path}")
            raw=blob(root,head,path)
            if raw is None or sha(raw)!=digest: raise IntegrityError(f"sealed HEAD hash mismatch: {path}")
            sealed[path]=row
        changed={x for x in git(root,"diff","--name-only","--no-renames",base,head,"--").splitlines() if x}
        if changed!=set(sealed)|{manifest_path}: raise IntegrityError("commit changed paths outside sealed manifest")
        planned=set(); allowed=set(policy.get("snapshot_review_dispositions",[])); snapshots=manifest.get("snapshot_candidates",[])
        if not isinstance(snapshots,list): raise IntegrityError("snapshot_candidates malformed")
        for item in snapshots:
            if not isinstance(item,dict): raise IntegrityError("snapshot row malformed")
            cid=item.get("candidate_id"); path=safe(item.get("path")); review=reviews.get(cid); planned.add(path)
            if not isinstance(cid,str) or CID_RE.fullmatch(cid) is None or path!=f"{CANDIDATES}{cid}.json" or not review: raise IntegrityError(f"snapshot identity/review mismatch: {cid}")
            if review.get("disposition") not in allowed or review.get("source_key")!=item.get("source_key") or review.get("review_basis")!=item.get("review_basis"): raise IntegrityError(f"snapshot lacks exact protected review: {cid}")
            snapshot_auth=snapshot_auths.get(cid)
            required={"candidate_id","candidate_sha256","source_key","disposition","review_basis","review_basis_sha256","review_record_sha256","authorization_status"}
            if not isinstance(snapshot_auth,dict) or set(snapshot_auth)!=required or snapshot_auth.get("authorization_status")!=SNAPSHOT_STATUS: raise IntegrityError(f"snapshot lacks exact protected snapshot authorization: {cid}")
            if snapshot_auth.get("source_key")!=item.get("source_key") or snapshot_auth.get("disposition")!=item.get("disposition") or snapshot_auth.get("review_basis")!=item.get("review_basis"): raise IntegrityError(f"snapshot authorization identity/disposition mismatch: {cid}")
            if snapshot_auth.get("candidate_sha256")!=item.get("source_sha256"): raise IntegrityError(f"snapshot authorization is not bound to exact candidate bytes: {cid}")
            if snapshot_auth.get("review_record_sha256")!=canonical_sha(review): raise IntegrityError(f"snapshot authorization is not bound to exact protected review row: {cid}")
            basis=review.get("review_basis"); basis_raw=blob(root,base,safe(basis)) if isinstance(basis,str) else None
            if basis_raw is None or snapshot_auth.get("review_basis_sha256")!=sha(basis_raw): raise IntegrityError(f"snapshot authorization review-basis hash mismatch: {cid}")
            raw=blob(root,head,path); candidate=loads(raw or b"",path); before=blob(root,base,path); pre="ABSENT" if before is None else sha(before)
            if candidate.get("candidate_id")!=cid or candidate.get("authority")!="Research" or candidate.get("lifecycle",{}).get("stage")!="DISCOVERED" or candidate.get("source_key")!=item.get("source_key"): raise IntegrityError(f"snapshot candidate content mismatch: {cid}")
            if path not in sealed or sealed[path]["kind"]!="planned" or sealed[path]["sha256"]!=item.get("source_sha256") or pre!=item.get("expected_main_sha256"): raise IntegrityError(f"snapshot seal/preimage mismatch: {path}")
        proposals=manifest.get("canonical_proposals",[])
        if not isinstance(proposals,list): raise IntegrityError("canonical_proposals malformed")
        for proposal in proposals:
            if not isinstance(proposal,dict): raise IntegrityError("proposal row malformed")
            pid=proposal.get("proposal_id"); auth=auths.get(pid)
            auth_fields={"proposal_id","candidate_id","proposal_sha256","candidate_sha256","operations_sha256","lifecycle_stage","authorization_status","provenance_sha256"}
            if not isinstance(auth,dict) or set(auth)!=auth_fields or auth.get("authorization_status")!=AUTH_STATUS or auth.get("lifecycle_stage")!="PROMOTION_PROPOSED" or auth.get("candidate_id")!=proposal.get("candidate_id") or auth.get("proposal_sha256")!=proposal.get("proposal_sha256") or auth.get("candidate_sha256")!=proposal.get("candidate_sha256"): raise IntegrityError(f"proposal lacks exact protected authorization: {pid}")
            operations=proposal.get("operations",[])
            if not isinstance(operations,list) or not operations or canonical_sha(operations)!=auth.get("operations_sha256") or proposal.get("operations_sha256")!=auth.get("operations_sha256"): raise IntegrityError(f"proposal operation authorization mismatch: {pid}")
            provenance=proposal.get("provenance",{})
            if not isinstance(provenance,dict) or set(provenance)!=set(PROV_KEYS): raise IntegrityError(f"proposal provenance incomplete: {pid}")
            for key in PROV_KEYS:
                row=provenance[key]
                if not isinstance(row,dict) or set(row)!={"path","sha256"} or auth.get("provenance_sha256",{}).get(key)!=row.get("sha256"): raise IntegrityError(f"proposal provenance authorization mismatch: {pid}/{key}")
                raw=blob(root,base,safe(row["path"]))
                if raw is None or sha(raw)!=row["sha256"]: raise IntegrityError(f"proposal provenance base hash mismatch: {pid}/{key}")
            seen=set()
            for operation in operations:
                required={"op","path","source_path","expected_main_sha256","result_sha256"}
                if not isinstance(operation,dict) or set(operation)!=required or operation.get("op")!="write_file": raise IntegrityError(f"proposal operation malformed: {pid}")
                path=safe(operation["path"]); canonical_target(path,policy)
                if path in seen or path in planned: raise IntegrityError(f"duplicate/colliding proposal target: {path}")
                seen.add(path); planned.add(path); before=blob(root,base,path); pre="ABSENT" if before is None else sha(before)
                if path not in sealed or sealed[path]["kind"]!="planned" or sealed[path]["sha256"]!=operation.get("result_sha256") or pre!=operation.get("expected_main_sha256"): raise IntegrityError(f"proposal seal/preimage mismatch: {path}")
        generated={safe(x) for x in policy.get("trusted_generated_paths",[])}; unexpected=set(sealed)-planned-generated
        if unexpected: raise IntegrityError("sealed paths lack authority: "+", ".join(sorted(unexpected)))
        for path,row in sealed.items():
            if row["kind"]!=("planned" if path in planned else "trusted_generated"): raise IntegrityError(f"sealed kind mismatch: {path}")
        _verify_generated_outputs(root,base,head,planned,generated)
        return []
    except (IntegrityError,KeyError,TypeError,ValueError) as exc:
        return [str(exc)]

def main()->int:
    errors=verify(Path(__file__).resolve().parents[1])
    if errors:
        print("Living promotion integrity FAILED",file=sys.stderr)
        for error in errors: print(f"- {error}",file=sys.stderr)
        return 1
    print("Living promotion integrity PASS")
    return 0
if __name__=="__main__": raise SystemExit(main())
