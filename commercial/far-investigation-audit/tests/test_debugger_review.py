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
    def test_4458895730_resume_extends_inherited_lineage_without_claiming_independence(self):
        cfg=request(True)
        cfg["debugger_options"]={"source_lineage":[
            {"schema":"far-source-lineage/1.0","source_id":"primary","relationship":"origin",
             "root_lineage_ids":["declared-original"],"upstream_source_ids":[]}]}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);original=investigate(cfg);write_package(root/"original",original)
            resumed=investigate(resume_request(root/"original",[
                {"kind":"text","text":"An additional record of blue birds."},
                {"kind":"text","text":"A second additional observation."}],captured_at=T))
            lineage={record["source_id"]:record for record in resumed["debugger"]["source_lineage"]}
            self.assertEqual(lineage["primary"],original["debugger"]["source_lineage"][0])
            self.assertEqual(set(lineage),{"primary","ev1","ev2"})
            self.assertTrue(all(lineage[key]["relationship"]=="unknown" for key in ("ev1","ev2")))
            self.assertEqual(lineage["ev1"]["root_lineage_ids"],lineage["ev2"]["root_lineage_ids"])
            write_package(root/"resumed",resumed)
            self.assertTrue(verify_package(root/"resumed")["replay_match"])
            # A second resume must retain existing unknowns and cover only new IDs.
            again=investigate(resume_request(root/"resumed",[{"kind":"text","text":"Another added source."}],captured_at=T))
            self.assertEqual({record["source_id"] for record in again["debugger"]["source_lineage"]},
                             {"primary","ev1","ev2","ev3"})

    def test_4391545567_singular_polarity_is_not_count_equivalence(self):
        formula={"atom":"P"}
        atoms={"P":"Rain is wet."}
        result=fidelity("Rain is not wet.",formula,atoms)
        self.assertEqual(result["status"],"CONTRADICTED")
        self.assertEqual(len(collisions([
            {"id":"negative","text":"Rain is not wet.","formula":formula},
            {"id":"positive","text":"Rain is wet.","formula":formula}])),1)
        nested={"implies":[{"atom":"P"},{"atom":"Q"}]}
        self.assertEqual(fidelity("If rain is not wet, then snow is cold.",nested,
                                 {"P":"Rain is wet.","Q":"Snow is cold."})["status"],"CONTRADICTED")

    def test_449514_quantified_pronouns_cannot_be_fixed_singular(self):
        # "Something is not blue" is not equivalent to
        # "not (something is blue)" on a mixed-color population.
        from semantic import compile_text
        for subject in (
            "Something", "Someone", "Somebody", "Anything", "Anyone",
            "Anybody", "Everything", "Everyone", "Everybody", "Nothing",
            "Nobody", "Each", "Either", "Neither", "Both",
        ):
            with self.subTest(subject=subject):
                affirmative=f"{subject} is blue."
                negative=f"{subject} is not blue."
                self.assertIsNone(compile_text(affirmative))
                self.assertEqual(
                    fidelity(negative, {"not":{"atom":"P"}}, {"P":affirmative})["status"],
                    "ABSTAIN",
                )

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

    def test_449514_resume_reuses_large_verified_snapshots_without_input_bypass(self):
        original_config=request(True,ident="large-resume")
        del original_config["captured_at"]
        original_config["source"]={"kind":"url","url":"https://example.org/primary"}
        original_config["evidence_sources"]=[
            {"kind":"url","url":"https://example.org/evidence1"},
            {"kind":"url","url":"https://example.org/evidence2"},
        ]
        payload="Some birds are blue. All birds are blue." + " x"*80000
        self.assertLess(len(payload.encode()),190000)
        def fetch_large(url,*,permit_network):
            return {"url":url,"text":payload,"raw_snapshot_utf8":payload,
                    "raw_sha256":digest(payload.encode()),"extraction":"utf8_identity_v1"}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            original=investigate(original_config,permit_network=True,source_fetcher=fetch_large)
            write_package(root/"original",original)
            self.assertTrue(verify_package(root/"original")["replay_match"])
            continued=resume_request(root/"original",[])
            self.assertLess(len(canonical(continued)),450000)
            self.assertEqual(continued["source"]["kind"],"verified_snapshot")
            with self.assertRaisesRegex(InvalidBundle,"verified source reference"):
                investigate(dict(continued))
            result=investigate(continued)
            self.assertEqual(len(result["bundle"]["sources"]),3)
            self.assertEqual(result["proposal"]["resumes_input_sha256"],
                             original["audit"]["input_sha256"])
            self.assertTrue(result["manifest"]["network_used"])
            self.assertEqual(
                [a["url"] for a in result["acquisition"]],
                [a["url"] for a in original["acquisition"]],
            )
            self.assertEqual(
                [s["captured_at"] for s in result["bundle"]["sources"]],
                [s["captured_at"] for s in original["bundle"]["sources"]],
            )
            self.assertEqual(
                [s["sha256"] for s in result["bundle"]["sources"]],
                [s["sha256"] for s in original["bundle"]["sources"]],
            )
            write_package(root/"resumed",result)
            self.assertTrue(verify_package(root/"resumed")["replay_match"])

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

    def test_449514_lineage_does_not_cross_deduplicated_source_occurrences(self):
        # Two investigations reuse primary snapshot X. Only one declares
        # that X depends on Y; retracting Y must not taint independent X.
        derived=request(True,ident="derived")
        derived["evidence_sources"]=[{"kind":"text","text":"Upstream record of blue birds."}]
        derived["debugger_options"]={"source_lineage":[
            {"schema":"far-source-lineage/1.0","source_id":"primary",
             "relationship":"derived","upstream_source_ids":["ev1"],"root_lineage_ids":["upstream-root"]},
            {"schema":"far-source-lineage/1.0","source_id":"ev1",
             "relationship":"origin","upstream_source_ids":[],"root_lineage_ids":["upstream-root"]}]}
        independent=request(True,ident="independent")
        independent["debugger_options"]={"source_lineage":[{
            "schema":"far-source-lineage/1.0","source_id":"primary",
            "relationship":"origin","upstream_source_ids":[],"root_lineage_ids":["separate-root"]}]}
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            p=investigate(derived);q=investigate(independent)
            self.assertEqual(p["bundle"]["sources"][0]["sha256"],q["bundle"]["sources"][0]["sha256"])
            write_package(root/"derived",p);write_package(root/"independent",q)
            self.assertTrue(verify_package(root/"derived")["replay_match"])
            self.assertTrue(verify_package(root/"independent")["replay_match"])
            memory=Memory(root/"memory.sqlite")
            try:
                memory.remember(root/"derived",known_time=T)
                memory.remember(root/"independent",known_time=T)
                state=memory.replay()
                shared="source:"+p["bundle"]["sources"][0]["sha256"]
                self.assertEqual(len(state["nodes"][shared]["occurrences"]),2)
                self.assertEqual(sum(n["type"]=="source_occurrence" and n["content_id"]==shared
                                     for n in state["nodes"].values()),2)
                upstream="source:"+p["bundle"]["sources"][1]["sha256"]
                memory.source_state(upstream,active=False,reason="upstream withdrawn",
                                    known_time=T,valid_time=T)
                invalid=set(memory.replay()["invalidated"])
                self.assertIn(p["audit"]["input_sha256"]+":reading:r1",invalid)
                self.assertNotIn(q["audit"]["input_sha256"]+":reading:r1",invalid)
                memory.source_state(upstream,active=True,reason="restored",
                                    known_time=T,valid_time=T)
                self.assertFalse(memory.replay()["invalidated"])
            finally:
                memory.close()

    def test_4391124913_nested_count_equivalence_abstains_and_never_collides(self):
        a="If no birds are blue, then rain is wet."
        b="If all birds are not blue, then rain is wet."
        formula={"implies":[{"atom":"P"},{"atom":"Q"}]}
        self.assertEqual(fidelity(a,formula,{"P":"All birds are not blue.","Q":"Rain is wet."})["status"],"ABSTAIN")
        self.assertFalse(collisions([{"id":"a","text":a,"formula":formula},{"id":"b","text":b,"formula":formula}]))


if __name__=="__main__":unittest.main()
