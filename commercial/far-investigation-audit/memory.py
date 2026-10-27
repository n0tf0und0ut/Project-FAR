"""Transactional, content-addressed event history for verified investigations.

Derived projections are rebuilt from checked events. Hash chains detect accidental
or partial modification, not replacement by an attacker controlling the whole DB.
Imported conclusions remain conditional/untrusted; memory never votes on truth.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
from engine import InvalidBundle, canonical, digest, required, timestamp, audit

SCHEMA="far-investigation-memory/1.0"
MAX_EVENTS=5000


class Memory:
    def __init__(self,path):
        self.path=Path(path)
        required(not self.path.is_symlink(),"symlink memory database forbidden")
        self.db=sqlite3.connect(str(self.path),timeout=10,isolation_level=None)
        self.db.execute("PRAGMA trusted_schema=OFF")
        self.db.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, previous TEXT NOT NULL, payload BLOB NOT NULL, sha256 TEXT NOT NULL UNIQUE)")

    def close(self):
        self.db.close()

    def events(self,through=None):
        from full_cli import parse_json_artifact
        required(through is None or type(through) is int and through>=0,"invalid historical sequence")
        rows=self.db.execute("SELECT seq,previous,payload,sha256 FROM events ORDER BY seq LIMIT ?",(MAX_EVENTS+1,)).fetchall()
        required(len(rows)<=MAX_EVENTS,"memory event cap exceeded")
        out=[]
        previous="0"*64
        total=0
        for expected,(seq,parent,raw,identity) in enumerate(rows,1):
            required(isinstance(raw,bytes) and len(raw)<=6_000_000,"memory payload limit exceeded")
            total+=len(raw)
            required(total<=250_000_000,"memory history byte limit exceeded")
            required(seq==expected and parent==previous and digest(canonical({"seq":seq,"previous":parent,"payload_sha256":digest(raw)}))==identity,"memory chain integrity failure")
            payload=parse_json_artifact(raw,"memory event")
            required(raw==canonical(payload),"noncanonical memory event")
            self._validate(payload)
            out.append({"seq":seq,"sha256":identity,"payload":payload})
            previous=identity
        if through is not None:
            required(through<=len(out),"historical sequence beyond recorded history")
            return out[:through]
        return out

    def _validate(self,p):
        required(isinstance(p,dict) and p.get("schema")==SCHEMA,"unknown memory event schema")
        timestamp(p.get("known_time"),"memory.known_time")
        if p.get("type")=="investigation":
            required(set(p)=={"schema","type","known_time","bundle","audit","proposal","debugger"},"unexpected investigation event fields")
            from debugger import debug
            from independent_check import check_report
            result=audit(p["bundle"])
            required(result==p["audit"],"memory audit replay failure")
            check_report(p["bundle"],result)
            required(p["bundle"].get("proposal_sha256")==digest(canonical(p["proposal"])),"memory proposal mismatch")
            required(debug(p["bundle"],result,p["proposal"])==p["debugger"],"memory debugger replay failure")
        elif p.get("type")=="source_state":
            required(set(p)=={"schema","type","known_time","valid_time","target","active","reason"},"unexpected source-state fields")
            timestamp(p["valid_time"],"memory.valid_time")
            required(type(p["active"]) is bool and isinstance(p["target"],str) and
                     isinstance(p["reason"],str) and 0<len(p["reason"])<=2000,"invalid source state")
        else:
            raise InvalidBundle("unknown memory event type")

    def _append(self,payload):
        self._validate(payload)
        raw=canonical(payload)
        required(len(raw)<=6_000_000,"memory event too large")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            events=self.events()
            required(len(events)<MAX_EVENTS,"memory event cap exceeded")
            required(not events or timestamp(payload["known_time"],"known_time")>=timestamp(events[-1]["payload"]["known_time"],"previous.known_time"),"memory known time moved backwards")
            if payload["type"]=="investigation":
                for event in events:
                    old=event["payload"]
                    if old["type"]=="investigation" and old["audit"]["input_sha256"]==payload["audit"]["input_sha256"]:
                        self.db.execute("ROLLBACK")
                        return {"duplicate":True,"seq":event["seq"],"sha256":event["sha256"]}
            else:
                state=self._project(events)
                required(payload["target"] in state["nodes"] and state["nodes"][payload["target"]]["type"]=="source","source-state target not found")
            seq=len(events)+1
            parent=events[-1]["sha256"] if events else "0"*64
            identity=digest(canonical({"seq":seq,"previous":parent,"payload_sha256":digest(raw)}))
            self.db.execute("INSERT INTO events VALUES (?,?,?,?)",(seq,parent,raw,identity))
            self.db.execute("COMMIT")
            return {"duplicate":False,"seq":seq,"sha256":identity}
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def remember(self,directory,*,known_time):
        from full_cli import verify_package
        verified=verify_package(Path(directory),include_verified_snapshots=True)
        required("_verified_debugger" in verified,"memory requires a debugger-enabled verified package")
        return self._append({"schema":SCHEMA,"type":"investigation","known_time":known_time,
                             "bundle":verified["_verified_bundle"],"audit":verified["_verified_audit"],
                             "proposal":verified["_verified_proposal"],"debugger":verified["_verified_debugger"]})

    def source_state(self,target,*,active,reason,known_time,valid_time):
        return self._append({"schema":SCHEMA,"type":"source_state","known_time":known_time,
                             "valid_time":valid_time,"target":target,"active":active,"reason":reason})

    @staticmethod
    def _project(events,valid_at=None):
        nodes={}
        edges=set()
        disabled=set()
        semantic_index={}
        versions={}
        if valid_at is None and events:
            valid_at=events[-1]["payload"]["known_time"]
        if valid_at is not None:
            timestamp(valid_at,"valid_at")
        for event in events:
            p=event["payload"]
            if p["type"]=="source_state":
                if timestamp(p["valid_time"],"valid_time")>timestamp(valid_at,"valid_at"):
                    continue
                if p["active"]:
                    disabled.discard(p["target"])
                else:
                    disabled.add(p["target"])
                continue
            run=p["audit"]["input_sha256"]
            versions.setdefault(p["bundle"]["investigation_id"],[]).append(run)
            source_map={s["id"]:"source:"+s["sha256"] for s in p["bundle"]["sources"]}
            mapped={}
            for n in p["debugger"]["graph"]["nodes"]:
                key=source_map[n["record"]["id"]] if n["type"]=="source" else run+":"+n["id"]
                mapped[n["id"]]=key
                if n["type"]=="source":
                    if key not in nodes:
                        nodes[key]={"type":"source","record":{"text":n["record"]["text"],"sha256":n["record"]["sha256"]},"occurrences":[]}
                    nodes[key]["occurrences"].append({"run":run,"record":n["record"]})
                else:
                    nodes[key]={"type":n["type"],"record":n["record"],"run":run}
                if n["type"]=="interpretation" and n["record"].get("semantic_id"):
                    semantic_index.setdefault(n["record"]["semantic_id"],[]).append(key)
            for e in p["debugger"]["graph"]["edges"]:
                edges.add((mapped[e["from"]],mapped[e["to"]],e["relation"]))
        adjacency={}
        for a,b,_ in edges:
            adjacency.setdefault(a,set()).add(b)
        invalid=set(disabled)
        pending=list(disabled)
        while pending:
            for target in adjacency.get(pending.pop(),set()):
                if target not in invalid:
                    invalid.add(target)
                    pending.append(target)
        for key in nodes:
            nodes[key]["state"]="INVALIDATED_DEPENDENCY" if key in invalid else "RECORDED_CONDITIONAL"
        return {"schema":SCHEMA,"through_event":len(events),"head":events[-1]["sha256"] if events else "0"*64,
                "nodes":dict(sorted(nodes.items())),"edges":[{"from":a,"to":b,"relation":r} for a,b,r in sorted(edges)],
                "semantic_index":dict(sorted(semantic_index.items())),"investigation_versions":dict(sorted(versions.items())),
                "invalidated":sorted(invalid),"trust":"No source authenticity or truth promotion from memory."}

    def replay(self,through=None,*,valid_at=None):
        return self._project(self.events(through),valid_at)

    def lookup(self,semantic_id,*,through=None):
        state=self.replay(through)
        return [{"id":k,**state["nodes"][k]} for k in state["semantic_index"].get(semantic_id,[])]
