"""Epistemic debugger CLI using the existing investigation/package engine."""
from __future__ import annotations
import argparse
import json
import sqlite3
import copy
from datetime import datetime, timezone
from pathlib import Path
from engine import InvalidBundle, canonical
from full_cli import read_json_artifact, write_package, verify_package
from workflow import investigate
from memory import Memory


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")


def resume_request(directory, evidence, *, proposal=None, captured_at=None):
    old=verify_package(Path(directory),include_verified_snapshots=True)
    bundle=old["_verified_bundle"]
    def source(s):
        return {"kind":"text","text":s["text"],"origin_id":s["origin_id"],"published_at":s["published_at"]}
    original=next(s for s in bundle["sources"] if s["id"]=="primary")
    evidence_sources=[source(s) for s in bundle["sources"] if s["id"]!="primary"]
    if not isinstance(evidence,list):
        raise InvalidBundle("resume evidence must be a list of source configurations")
    chosen=copy.deepcopy(proposal if proposal is not None else old["_verified_proposal"])
    if proposal is None:
        remap={s["id"]:f"ev{i+1}" for i,s in enumerate(s for s in bundle["sources"] if s["id"]!="primary")}
        for entry in chosen.get("evidence",[]):
            entry["source_id"]=remap.get(entry["source_id"],entry["source_id"])
        for entry in chosen.get("debugger_options",{}).get("source_lineage",[]):
            entry["source_id"]=remap.get(entry["source_id"],entry["source_id"])
            entry["upstream_source_ids"]=[remap.get(x,x) for x in entry["upstream_source_ids"]]
    chosen["resumes_input_sha256"]=old["_verified_audit"]["input_sha256"]
    config={"investigation_id":bundle["investigation_id"],"source":source(original),
            "evidence_sources":evidence_sources+evidence,"proposal_mode":"supplied","proposal":chosen,"debugger":True}
    if captured_at is not None:
        config["captured_at"]=captured_at
    return config


def main(argv=None):
    parser=argparse.ArgumentParser(description="FAR Epistemic Debugger: investigate, resume, replay and revise")
    sub=parser.add_subparsers(dest="command",required=True)
    create=sub.add_parser("investigate")
    create.add_argument("request",type=Path)
    resume=sub.add_parser("resume")
    resume.add_argument("package",type=Path)
    resume.add_argument("--evidence",type=Path,required=True,help="JSON list of additional source configurations")
    resume.add_argument("--proposal",type=Path,help="replacement interpretation proposal including links to added evidence")
    for p in (create,resume):
        p.add_argument("--output",type=Path,required=True)
        p.add_argument("--memory",type=Path)
        p.add_argument("--captured-at")
        p.add_argument("--allow-network",action="store_true")
    verify=sub.add_parser("verify")
    verify.add_argument("package",type=Path)
    remember=sub.add_parser("remember")
    remember.add_argument("package",type=Path)
    remember.add_argument("--memory",type=Path,required=True)
    replay=sub.add_parser("replay")
    replay.add_argument("--memory",type=Path,required=True)
    replay.add_argument("--through",type=int)
    lookup=sub.add_parser("lookup")
    lookup.add_argument("semantic_id")
    lookup.add_argument("--memory",type=Path,required=True)
    state=sub.add_parser("source-state")
    state.add_argument("target",help="source:<exact snapshot SHA-256>")
    state.add_argument("--memory",type=Path,required=True)
    state.add_argument("--state",choices=["retract","restore"],required=True)
    state.add_argument("--reason",required=True)
    state.add_argument("--valid-time",required=True)
    args=parser.parse_args(argv)
    memory=None
    try:
        if args.command in {"investigate","resume"}:
            config=(read_json_artifact(args.request,450000) if args.command=="investigate" else
                    resume_request(args.package,read_json_artifact(args.evidence,450000),
                                   proposal=read_json_artifact(args.proposal,450000) if args.proposal else None,
                                   captured_at=args.captured_at))
            if not isinstance(config,dict):
                raise InvalidBundle("request must be an object")
            config["debugger"]=True
            if args.captured_at:
                config["captured_at"]=args.captured_at
            result=investigate(config,permit_network=args.allow_network,permit_files=True)
            write_package(args.output,result)
            out={"package":str(args.output),"verification":verify_package(args.output),"debugger":result["debugger"]}
            if args.memory:
                memory=Memory(args.memory)
                out["memory_event"]=memory.remember(args.output,known_time=now())
        elif args.command=="verify":
            out=verify_package(args.package)
        else:
            memory=Memory(args.memory)
            if args.command=="remember":
                out=memory.remember(args.package,known_time=now())
            elif args.command=="replay":
                out=memory.replay(args.through)
            elif args.command=="lookup":
                out=memory.lookup(args.semantic_id)
            else:
                out=memory.source_state(args.target,active=args.state=="restore",reason=args.reason,
                                        known_time=now(),valid_time=args.valid_time)
        print(canonical(out).decode())
        return 0
    except (ValueError, OSError, TypeError, KeyError, RecursionError, sqlite3.Error) as exc:
        print(canonical({"status":"INVALID","error":str(exc)[:500]}).decode())
        return 2
    finally:
        if memory:
            memory.close()


if __name__=="__main__":
    raise SystemExit(main())
