"""Regressions for exact-head review 5670073956; each failed before its fix."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from semantic import fidelity,collisions
from engine import InvalidBundle,canonical,digest
from memory import Memory,SCHEMA
from workflow import investigate
from full_cli import write_package,verify_package
from debugger_cli import resume_request
from test_debugger import request,T


def fetched(url,*,permit_network):
    text="Some birds are blue."
    return {"url":url,"text":text,"raw_snapshot_utf8":text,
            "raw_sha256":digest(text.encode()),"extraction":"utf8_identity_v1"}


class ReviewRegressions(unittest.TestCase):
    def test_4390863035_unsupported_cardinal_cannot_be_singular(self):
        for phrase in ("Exactly thirty birds","Thirty birds","Thirty-two birds","Several birds","Both birds"):
            with self.subTest(phrase=phrase):
                result=fidelity(phrase+" are not blue.",{"not":{"atom":"P"}},{"P":phrase+" are blue."})
                self.assertEqual(result["status"],"ABSTAIN")

    def test_4390863050_universal_negation_keeps_temporal_scope_unknown(self):
        result=fidelity("Some birds are not blue before 2020.",{"not":{"atom":"P"}},
                        {"P":"All birds are blue before 2020."})
        self.assertEqual(result["status"],"ABSTAIN")

    def test_4390863057_aggregate_limit_rejects_before_commit(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);package=investigate(request(True));write_package(root/"package",package)
            m=Memory(root/"memory.sqlite")
            try:
                m.remember(root/"package",known_time=T)
                target="source:"+package["bundle"]["sources"][0]["sha256"]
                incoming={"schema":SCHEMA,"type":"source_state","known_time":T,"valid_time":T,
                          "target":target,"active":False,"reason":"bounded"}
                current=m.db.execute("SELECT SUM(length(payload)) FROM events").fetchone()[0]
                limit=current+len(canonical(incoming))-1
                with patch("memory.MAX_HISTORY_BYTES",limit,create=True):
                    with self.assertRaisesRegex(InvalidBundle,"history byte limit"):
                        m.source_state(target,active=False,reason="bounded",known_time=T,valid_time=T)
                    self.assertEqual(m.replay()["through_event"],1)
                    self.assertFalse(m.db.in_transaction)
            finally:m.close()

    def test_4390863070_failed_evidence_mapping_blocks_assurance_pass(self):
        cfg=request(False)
        cfg["evidence_sources"]=[{"kind":"text","text":"All birds are blue."}]
        cfg["proposal"]["evidence"]=[{"id":"e1","claim_id":"c1","source_id":"ev1",
            "quote":"All birds are blue.","formula":{"atom":"P"},"relation":"supports"}]
        result=investigate(cfg)["debugger"]
        self.assertEqual(result["evidence_semantics"]["e1"]["status"],"CONTRADICTED")
        self.assertEqual(result["audit_assurance"]["checks"]["interpretation_fidelity"]["status"],"fail")
        self.assertEqual(result["audit_assurance"]["overall_status"],"not_assured")

    def test_4390863082_resume_live_url_assigns_capture_during_acquisition(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"original";write_package(path,investigate(request(True)))
            cfg=resume_request(path,[{"kind":"url","url":"https://example.org/new"}])
            self.assertNotIn("captured_at",cfg)
            called=[]
            def fetch(url,**kwargs):called.append(url);return fetched(url,**kwargs)
            result=investigate(cfg,permit_network=True,source_fetcher=fetch)
            self.assertEqual(called,["https://example.org/new"])
            write_package(Path(t)/"followup",result)
            self.assertTrue(verify_package(Path(t)/"followup")["replay_match"])
            explicit=resume_request(path,[{"kind":"url","url":"https://example.org/new"}],captured_at=T)
            with self.assertRaisesRegex(InvalidBundle,"historical capture"):
                investigate(explicit,permit_network=True,source_fetcher=fetch)

    def test_4390863105_discovery_source_refs_survive_resume(self):
        cfg={"source":{"kind":"text","text":"Some birds are blue."},"debugger":True,
             "discovery":"tavily","queries":["birds blue"],"expand_discovery":True}
        package=investigate(cfg,permit_network=True,source_fetcher=fetched,
            search_requester=lambda _: {"results":[{"url":"https://example.org/origin","content":"unverified lead"}]})
        self.assertEqual(package["proposal"]["evidence"][0]["source_id"],"discovery1")
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"original";write_package(path,package)
            self.assertTrue(verify_package(path)["replay_match"])
            resumed=investigate(resume_request(path,[]))
            self.assertEqual(resumed["proposal"]["evidence"][0]["source_id"],"ev1")
            write_package(Path(t)/"resumed",resumed)
            self.assertTrue(verify_package(Path(t)/"resumed")["replay_match"])

    def test_4391124909_declared_lineage_propagates_retraction_and_restore(self):
        cfg=request(False)
        cfg["source"]["text"]="Some birds are blue. Therefore some birds are blue."
        cfg["proposal"]["claims"][0]["start"]=0
        cfg["proposal"]["claims"][1].update(quote="Therefore some birds are blue.",formula={"atom":"P"})
        cfg["evidence_sources"]=[{"kind":"text","text":"Upstream record of blue birds."}]
        cfg["debugger_options"]={"source_lineage":[
            {"schema":"far-source-lineage/1.0","source_id":"primary","relationship":"derived","upstream_source_ids":["ev1"],"root_lineage_ids":["origin"]},
            {"schema":"far-source-lineage/1.0","source_id":"ev1","relationship":"origin","upstream_source_ids":[],"root_lineage_ids":["origin"]}]}
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=investigate(cfg);write_package(root/"package",p)
            self.assertEqual(p["debugger"]["readings"][0]["acceptance"],"CONDITIONAL_ON_GRAMMAR_AND_PREMISES")
            m=Memory(root/"memory.sqlite")
            try:
                m.remember(root/"package",known_time=T)
                target="source:"+p["bundle"]["sources"][1]["sha256"]
                m.source_state(target,active=False,reason="upstream withdrawn",known_time=T,valid_time=T)
                self.assertIn(p["audit"]["input_sha256"]+":reading:r1",m.replay()["invalidated"])
                m.source_state(target,active=True,reason="restored",known_time=T,valid_time=T)
                self.assertFalse(m.replay()["invalidated"])
            finally:m.close()

    def test_4391124913_nested_count_equivalence_abstains_and_never_collides(self):
        a="If no birds are blue, then rain is wet."
        b="If all birds are not blue, then rain is wet."
        formula={"implies":[{"atom":"P"},{"atom":"Q"}]}
        self.assertEqual(fidelity(a,formula,{"P":"All birds are not blue.","Q":"Rain is wet."})["status"],"ABSTAIN")
        self.assertFalse(collisions([{"id":"a","text":a,"formula":formula},{"id":"b","text":b,"formula":formula}]))


if __name__=="__main__":unittest.main()
