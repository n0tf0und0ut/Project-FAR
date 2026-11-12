from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from tools import run_living_research as lr
from tools import reconcile_living_repo as rr


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def claims():
    return {"theory_id":"PROJECT-FAR-CORE-THEORY-1.1","claims":[{"id":f"FAR-CORE-{n:03d}","status":"proved","scope":f"scope {n}","claim":f"claim {n}"} for n in range(1,15)]}


def assurance():
    rows=[]
    for n in range(1,15):
        deps=[f"FAR-CORE-{n-1:03d}"] if n>1 else ["set_presentation"]
        rows.append({"id":f"FAR-CORE-{n:03d}","exact_statement":f"claim {n}","scope":f"scope {n}","dependencies":deps,"truth_disposition":"PROVED","formalization_status":"FORMALIZED","novelty_prior_art_status":"NOT_ESTABLISHED","governance_status":"ACCEPTED_CURRENT"})
    return {"claims":rows}


def rq_registry():
    return {"questions":[
        {"id":"FAR-RQ-003","exact_question":"Can FAR-CORE-002 be computed?","governing_scope":"FAR-CORE-002","dependencies":["FAR-CORE-002"],"current_disposition":"OPEN"},
        {"id":"FAR-RQ-009","exact_question":"Does evidence contradict FAR-CORE-001 through FAR-CORE-014?","governing_scope":"FAR-CORE-001 through FAR-CORE-014","dependencies":[],"current_disposition":"OPEN"}
    ]}


def threat_registry():
    return {"threats":[{"id":"THREAT-004"}]}


def minimal_config():
    return {
        "schema_version":"1.0","program_id":"FAR-LIVING-RESEARCH-001","authority":"Research","authority_boundary":lr.AUTHORITY_BOUNDARY,"schedule_intent":"every_30_minutes",
        "sources":{
            "crossref":{"endpoint":"https://api.crossref.org/works","rows_per_query":8,"initial_lookback_days":14,"overlap_days":2,"timeout_seconds":1,"max_retries":0,"user_agent":"test"},
            "openalex":{"endpoint":"https://api.openalex.org/works","rows_per_query":8,"timeout_seconds":1,"max_retries":0,"user_agent":"test"},
            "openlibrary":{"endpoint":"https://openlibrary.org/search.json","enabled":True,"interval_runs":4,"rows_per_query":5,"timeout_seconds":1,"max_retries":0,"user_agent":"test"}},
        "threat_guards":["THREAT-004"],"attention_terms":["counterexample","contradiction"],
        "lenses":{"governed_question":{"bridge_terms":[],"min_bridge_hits":0},"formal_mathematics":{"bridge_terms":["formal"],"min_bridge_hits":0},"formal_metaphysics":{"bridge_terms":["formal","logic","identity"],"min_bridge_hits":1}},
        "historical_backfill":{"min_year":1600,"window_years":10,"queries":[{"id":"HIST-ONE","query":"equivalence quotient","target_ids":["FAR-RQ-009"],"lens":"formal_mathematics","signal_terms":["equivalence","quotient"],"min_signal_hits":1}],"book_queries":[{"id":"BOOK-ONE","query":"metaphysics identity logic","target_ids":["FAR-RQ-009"],"lens":"formal_metaphysics","signal_terms":["metaphysics","identity"],"min_signal_hits":1}]},
        "targets":[{"target_id":"FAR-RQ-003","allowed_dispositions":["OPEN"],"candidate_relation":"COMPUTABILITY","queries":["quotient algorithm"],"signal_terms":["quotient"],"min_signal_hits":1,"max_candidates_per_query":3}]
    }


class TempRepo:
    def __init__(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        write_json(self.root/lr.CONFIG_PATH,minimal_config()); write_json(self.root/lr.RQ_PATH,rq_registry()); write_json(self.root/lr.THREAT_PATH,threat_registry()); write_json(self.root/lr.CLAIM_PATH,claims())
        write_json(self.root/lr.STATE_PATH,{"schema_version":"1.0","program_id":"FAR-LIVING-RESEARCH-001","incremental_cursor_utc":None,"historical":{"query_index":0,"window_end_year":2026,"complete":False,"completed_utc":None},"openlibrary":{"query_index":0,"page":1},"run_count":0,"last_run_id":None,"last_run_status":"NEVER_RUN","total_unique_candidates":0,"updated_utc":None})
    def close(self): self.tmp.cleanup()


def crossref_payload(title="Quotient algorithm equivalence counterexample",doi="10.1/test"):
    return {"message":{"items":[{"DOI":doi,"title":[title],"type":"journal-article","publisher":"Test","published":{"date-parts":[[2001,1,1]]},"URL":"https://doi.org/"+doi}]}}


def openalex_payload(title="Equivalence quotient theorem",doi="https://doi.org/10.1/test"):
    return {"results":[{"id":"https://openalex.org/W1","doi":doi,"display_name":title,"publication_date":"2001-01-01","type":"article","cited_by_count":10,"authorships":[],"keywords":[{"display_name":"equivalence"}],"topics":[],"primary_location":{"landing_page_url":"https://example.org"}}]}


def openlibrary_payload():
    return {"docs":[{"key":"/works/OL1W","title":"Metaphysics of Identity and Formal Logic","author_name":["A. Thinker"],"first_publish_year":1800,"subject":["Metaphysics","Logic","Identity"],"edition_count":2}]}


class LivingResearchTests(unittest.TestCase):
    def test_cross_provider_doi_identity_is_stable(self):
        cr={"DOI":"10.1234/ABC","title":["A"]}; oa={"doi":"https://doi.org/10.1234/abc","display_name":"A"}
        self.assertEqual(lr.source_identity("Crossref",cr),"doi:10.1234/abc"); self.assertEqual(lr.source_identity("Crossref",cr),lr.source_identity("OpenAlex",oa)); self.assertEqual(lr.candidate_id(lr.source_identity("Crossref",cr)),lr.candidate_id(lr.source_identity("OpenAlex",oa)))

    def test_claim_range_expands_to_all_fourteen(self):
        ids=[f"FAR-CORE-{n:03d}" for n in range(1,15)]; self.assertEqual(lr.claim_ids_from_question(rq_registry()["questions"][1],ids),ids)

    def test_unknown_target_fails_closed(self):
        cfg=minimal_config(); cfg["targets"][0]["target_id"]="FAR-RQ-999"
        with self.assertRaises(lr.LivingResearchError): lr.validate_bindings(cfg,rq_registry(),threat_registry(),claims())

    def test_disposition_drift_fails_closed(self):
        cfg=minimal_config(); rq=rq_registry(); rq["questions"][0]["current_disposition"]="RESOLVED"
        with self.assertRaises(lr.LivingResearchError): lr.validate_bindings(cfg,rq,threat_registry(),claims())

    def test_formal_metaphysics_requires_mathematical_bridge(self):
        repo=TempRepo()
        try:
            item={"key":"/works/OLXW","title":"Metaphysics and Being","author_name":[],"subject":["Metaphysics"]}
            outcome,_=lr.process_item(root=repo.root,provider="Open Library",item=item,binding={"target_id":"FAR-RQ-009","target_ids":["FAR-RQ-009"],"query":"x","provider":"Open Library","mode":"historical_backfill","lens":"formal_metaphysics"},signal_terms=["metaphysics"],min_signal_hits=1,lens={"bridge_terms":["formal","logic","identity"],"min_bridge_hits":1},attention_terms=[],all_claim_ids=[f"FAR-CORE-{n:03d}" for n in range(1,15)],questions={q["id"]:q for q in rq_registry()["questions"]},now_iso="2026-01-01T00:00:00Z")
            self.assertEqual(outcome["reason"],"INSUFFICIENT_MATHEMATICAL_BRIDGE"); self.assertFalse(list((repo.root/lr.CANDIDATE_DIR).glob("*.json")))
        finally: repo.close()

    def test_successful_run_merges_crossref_and_openalex_same_doi(self):
        repo=TempRepo()
        try:
            result=lr.run(repo.root,now=datetime(2026,9,8,12,0,tzinfo=timezone.utc),crossref_transport=lambda *a:crossref_payload(),openalex_transport=lambda *a:openalex_payload(),openlibrary_transport=lambda *a:openlibrary_payload(),sleep_fn=lambda _:None)
            self.assertEqual(result["status"],"SUCCESS"); state=lr.read_json(repo.root/lr.STATE_PATH); self.assertEqual(state["incremental_cursor_utc"],"2026-09-08T12:00:00Z"); self.assertTrue(result["historical_advanced"])
            candidates=list((repo.root/lr.CANDIDATE_DIR).glob("*.json")); self.assertEqual(len(candidates),2); doi_record=next(lr.read_json(p) for p in candidates if lr.read_json(p)["source_key"].startswith("doi:")); self.assertEqual({s["provider"] for s in doi_record["sources"]},{"Crossref","OpenAlex"}); self.assertTrue(doi_record["triage"]["attention_terms"])
        finally: repo.close()

    def test_incremental_failure_does_not_advance_incremental_cursor(self):
        repo=TempRepo()
        try:
            def cr(url,headers,timeout):
                qs=parse_qs(urlparse(url).query)
                if "from-index-date" in qs.get("filter",[""])[0]: raise TimeoutError("boom")
                return crossref_payload()
            result=lr.run(repo.root,now=datetime(2026,9,8,12,0,tzinfo=timezone.utc),crossref_transport=cr,openalex_transport=lambda *a:openalex_payload(),openlibrary_transport=lambda *a:openlibrary_payload(),sleep_fn=lambda _:None)
            self.assertEqual(result["status"],"PARTIAL_SOURCE_FAILURE"); self.assertFalse(result["cursor_advanced"]); self.assertIsNone(lr.read_json(repo.root/lr.STATE_PATH)["incremental_cursor_utc"])
        finally: repo.close()

    def test_historical_failure_freezes_historical_cursor(self):
        repo=TempRepo()
        try:
            def oa(url,headers,timeout): raise TimeoutError("openalex unavailable")
            result=lr.run(repo.root,now=datetime(2026,9,8,12,0,tzinfo=timezone.utc),crossref_transport=lambda *a:crossref_payload(),openalex_transport=oa,openlibrary_transport=lambda *a:openlibrary_payload(),sleep_fn=lambda _:None)
            state=lr.read_json(repo.root/lr.STATE_PATH); self.assertEqual(result["status"],"PARTIAL_SOURCE_FAILURE"); self.assertTrue(result["cursor_advanced"]); self.assertFalse(result["historical_advanced"]); self.assertEqual(state["historical"]["query_index"],0); self.assertEqual(state["historical"]["window_end_year"],2026)
        finally: repo.close()

    def test_malformed_provider_row_freezes_only_the_affected_cursor_and_recovers(self):
        cases = (
            ("Crossref", "incremental"),
            ("Crossref", "historical_backfill"),
            ("OpenAlex", "historical_backfill"),
            ("Open Library", "historical_book_backfill"),
        )
        for provider, mode in cases:
            with self.subTest(provider=provider, mode=mode):
                repo = TempRepo()
                try:
                    config = lr.read_json(repo.root / lr.CONFIG_PATH)
                    config["sources"]["openlibrary"]["interval_runs"] = 1
                    write_json(repo.root / lr.CONFIG_PATH, config)

                    def crossref(url, *_):
                        query_filter = parse_qs(urlparse(url).query)["filter"][0]
                        lane = "incremental" if query_filter.startswith("from-index-date:") else "historical_backfill"
                        return {"message": {"items": [None] if (provider, mode) == ("Crossref", lane) else []}}

                    start = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)
                    result = lr.run(
                        repo.root, now=start, crossref_transport=crossref,
                        openalex_transport=lambda *_: {"results": [None] if provider == "OpenAlex" else []},
                        openlibrary_transport=lambda *_: {"docs": [None] if provider == "Open Library" else []},
                        sleep_fn=lambda _: None,
                    )
                    state = lr.read_json(repo.root / lr.STATE_PATH)
                    self.assertEqual(result["status"], "PARTIAL_SOURCE_FAILURE")
                    self.assertEqual([(row["provider"], row["mode"]) for row in result["failures"]], [(provider, mode)])
                    self.assertEqual(state["incremental_cursor_utc"], None if mode == "incremental" else lr.utc_iso(start))
                    self.assertEqual(state["historical"]["window_end_year"], 2026 if mode == "historical_backfill" else 2016)
                    self.assertEqual(state["openlibrary"]["page"], 1 if mode == "historical_book_backfill" else 2)
                    self.assertEqual(len(result["queries"]), 3)
                    self.assertTrue(all(row["request"]["rows_returned"] == 0 for row in result["queries"]))

                    resumed = start.replace(hour=13)
                    result = lr.run(
                        repo.root, now=resumed, crossref_transport=lambda *_: {"message": {"items": []}},
                        openalex_transport=lambda *_: {"results": []},
                        openlibrary_transport=lambda *_: {"docs": []},
                        sleep_fn=lambda _: None,
                    )
                    state = lr.read_json(repo.root / lr.STATE_PATH)
                    self.assertEqual(result["status"], "SUCCESS")
                    self.assertEqual(result["failures"], [])
                    self.assertEqual(state["incremental_cursor_utc"], lr.utc_iso(resumed))
                    self.assertEqual(state["historical"]["window_end_year"], 2016 if mode == "historical_backfill" else 2006)
                    self.assertEqual(state["openlibrary"]["page"], 2 if mode == "historical_book_backfill" else 3)
                finally:
                    repo.close()

    def test_acceptance_cap_prevents_extra_candidate_files(self):
        repo=TempRepo()
        try:
            cfg=lr.read_json(repo.root/lr.CONFIG_PATH); cfg["targets"][0]["max_candidates_per_query"]=1; write_json(repo.root/lr.CONFIG_PATH,cfg)
            def cr(url,headers,timeout): return {"message":{"items":[{"DOI":"10.1/a","title":["quotient one"],"published":{"date-parts":[[2000]]}},{"DOI":"10.1/b","title":["quotient two"],"published":{"date-parts":[[2000]]}}]}}
            lr.run(repo.root,now=datetime(2026,9,8,12,0,tzinfo=timezone.utc),crossref_transport=cr,openalex_transport=lambda *a:{"results":[]},openlibrary_transport=lambda *a:{"docs":[]},sleep_fn=lambda _:None)
            incremental=[lr.read_json(p) for p in (repo.root/lr.CANDIDATE_DIR).glob("*.json") if any(b.get("mode")=="incremental" for b in lr.read_json(p)["discovery"]["query_bindings"])]
            self.assertEqual(len(incremental),1)
        finally: repo.close()


    def test_attention_terms_match_whole_words_only(self):
        self.assertEqual(lr.boundary_hits("a correction to the record",["correction"]),["correction"])
        self.assertEqual(lr.boundary_hits("corrections and failures",["correction","failure"]),[])
        self.assertEqual(lr.boundary_hits("a no-go theorem",["no-go"]),["no-go"])
        self.assertEqual(lr.hits("corrections and failures",["correction","failure"]),["correction","failure"])

    def test_incremental_crossref_query_ranks_by_relevance(self):
        seen={}
        def transport(url,headers,timeout):
            seen["url"]=url; return crossref_payload()
        lr.crossref_query("quotient algorithm",minimal_config()["sources"]["crossref"],index_window=("2026-09-01","2026-09-08"),transport=transport,sleep_fn=lambda _:None)
        params=parse_qs(urlparse(seen["url"]).query)
        self.assertEqual(params["sort"],["relevance"]); self.assertNotIn("order",params)
        self.assertEqual(params["filter"],["from-index-date:2026-09-01,until-index-date:2026-09-08"])

    def test_incremental_index_filter_uses_calendar_dates(self):
        # Crossref rejects a full timestamp in from-index-date/until-index-date with HTTP
        # 400; run 34227532304 failed all 24 incremental queries that way.
        repo=TempRepo(); seen={}
        def cr(url,headers,timeout):
            seen.setdefault("urls",[]).append(url); return crossref_payload()
        try:
            lr.run(repo.root,now=datetime(2026,9,8,12,42,1,tzinfo=timezone.utc),crossref_transport=cr,openalex_transport=lambda *a:openalex_payload(),openlibrary_transport=lambda *a:openlibrary_payload(),sleep_fn=lambda _:None)
            inc=[u for u in seen["urls"] if "from-index-date" in u]
            self.assertTrue(inc)
            for url in inc:
                filt=parse_qs(urlparse(url).query)["filter"][0]
                self.assertEqual(filt,"from-index-date:2026-08-25,until-index-date:2026-09-08")
                self.assertNotIn("T",filt); self.assertNotIn("Z",filt)
        finally: repo.close()

    def test_source_missing_user_agent_fails_closed(self):
        # A source key missing from configuration used to raise KeyError per query and
        # silently kill that lane; it must be rejected before any request is issued.
        for name in ("crossref","openalex","openlibrary"):
            cfg=minimal_config(); cfg["sources"][name].pop("user_agent")
            with self.assertRaises(lr.LivingResearchError):
                lr.validate_bindings(cfg,rq_registry(),threat_registry(),claims())
            cfg=minimal_config(); cfg["sources"][name].pop("endpoint")
            with self.assertRaises(lr.LivingResearchError):
                lr.validate_bindings(cfg,rq_registry(),threat_registry(),claims())

    def test_shipped_config_declares_every_source_credential(self):
        # Guards the real configuration, not just the fixture.
        cfg=lr.read_json(Path(__file__).resolve().parents[1]/lr.CONFIG_PATH)
        for name in ("crossref","openalex","openlibrary"):
            self.assertTrue(cfg["sources"][name].get("user_agent"),f"{name} missing user_agent")
            self.assertTrue(cfg["sources"][name].get("endpoint"),f"{name} missing endpoint")

    def test_attention_terms_are_recomputed_not_accumulated(self):
        repo=TempRepo()
        def run_pass(terms):
            return lr.process_item(root=repo.root,provider="Crossref",item={"DOI":"10.1/attn","title":["A quotient counterexample and a contradiction"],"type":"journal-article"},binding={"target_id":"FAR-RQ-003","target_ids":["FAR-RQ-003"],"query":"quotient algorithm","provider":"Crossref","mode":"incremental"},signal_terms=["quotient"],min_signal_hits=1,lens=None,attention_terms=terms,all_claim_ids=[f"FAR-CORE-{n:03d}" for n in range(1,15)],questions={q["id"]:q for q in rq_registry()["questions"]},now_iso="2026-01-01T00:00:00Z")
        try:
            run_pass(["counterexample","contradiction"])
            path=next((repo.root/lr.CANDIDATE_DIR).glob("*.json"))
            self.assertEqual(lr.read_json(path)["triage"]["attention_terms"],["contradiction","counterexample"])
            run_pass(["contradiction"])  # counterexample removed from configuration
            self.assertEqual(lr.read_json(path)["triage"]["attention_terms"],["contradiction"])
        finally: repo.close()

    def test_rejected_fallback_identity_keeps_title_for_audit(self):
        repo=TempRepo()
        common=dict(root=repo.root,provider="Crossref",binding={"target_id":"FAR-RQ-003","target_ids":["FAR-RQ-003"],"query":"quotient algorithm","provider":"Crossref","mode":"incremental"},signal_terms=["quotient"],min_signal_hits=1,lens=None,attention_terms=[],all_claim_ids=[f"FAR-CORE-{n:03d}" for n in range(1,15)],questions={q["id"]:q for q in rq_registry()["questions"]},now_iso="2026-01-01T00:00:00Z")
        try:
            no_doi,_=lr.process_item(item={"title":["Unrelated chemistry result"],"type":"journal-article","publisher":"X"},**common)
            self.assertTrue(lr.is_fallback_identity(no_doi["source_key"]))
            self.assertEqual(no_doi["decision"],"REJECT"); self.assertEqual(no_doi["title"],"Unrelated chemistry result")
        finally: repo.close()

    def test_rejected_results_keep_identity_without_title(self):
        repo=TempRepo()
        try:
            item={"DOI":"10.1/unrelated","title":["Unrelated chemistry result"],"type":"journal-article"}
            outcome,was_new=lr.process_item(root=repo.root,provider="Crossref",item=item,binding={"target_id":"FAR-RQ-003","target_ids":["FAR-RQ-003"],"query":"quotient algorithm","provider":"Crossref","mode":"incremental"},signal_terms=["quotient"],min_signal_hits=1,lens=None,attention_terms=[],all_claim_ids=[f"FAR-CORE-{n:03d}" for n in range(1,15)],questions={q["id"]:q for q in rq_registry()["questions"]},now_iso="2026-01-01T00:00:00Z")
            self.assertEqual(outcome["decision"],"REJECT"); self.assertFalse(was_new)
            self.assertNotIn("title",outcome)
            self.assertEqual(outcome["source_key"],"doi:10.1/unrelated"); self.assertTrue(outcome["candidate_id"].startswith("FAR-LIT-"))
        finally: repo.close()

class ReconcilerTests(unittest.TestCase):
    def make_repo(self):
        tmp=tempfile.TemporaryDirectory(); root=Path(tmp.name); write_json(root/rr.CLAIM_LEDGER,claims()); write_json(root/rr.ASSURANCE_LEDGER,assurance()); write_json(root/rr.RQ_LEDGER,rq_registry()); write_json(root/rr.SURFACES_PATH,{"authority_boundary":rr.AUTHORITY_BOUNDARY,"surfaces":[{"path":str(rr.CLAIM_LEDGER),"role":"claims"},{"path":str(rr.ASSURANCE_LEDGER),"role":"assurance"},{"path":str(rr.RQ_LEDGER),"role":"rq"}]}); return tmp,root

    def test_reconciler_builds_dependency_fallout_and_review_queue(self):
        tmp,root=self.make_repo()
        try:
            write_json(root/rr.CANDIDATE_DIR/"FAR-LIT-AAAAAAAAAAAAAAAA.json",{"candidate_id":"FAR-LIT-AAAAAAAAAAAAAAAA","triage":{"attention_terms":["counterexample"],"lenses":["formal_mathematics"]},"potential_claim_ids":["FAR-CORE-002"],"discovery":{"query_bindings":[{"mode":"historical_backfill"}]}})
            state=rr.reconcile(root); self.assertEqual(len(state["claims"]),14); self.assertEqual(state["candidate_counts"]["candidates"],1); self.assertEqual(len(state["core_claim_review_queue"]),1); self.assertIn("FAR-CORE-014",state["core_claim_review_queue"][0]["downstream_claim_ids"]); self.assertEqual(state["core_claim_review_queue"][0]["epistemic_status"],"METADATA_SIGNAL_ONLY")
        finally: tmp.cleanup()

    def test_reconciler_rejects_exact_statement_drift(self):
        tmp,root=self.make_repo()
        try:
            bad=assurance(); bad["claims"][0]["exact_statement"]="changed"; write_json(root/rr.ASSURANCE_LEDGER,bad)
            with self.assertRaises(rr.ReconciliationError): rr.reconcile(root)
        finally: tmp.cleanup()


if __name__=="__main__": unittest.main()
