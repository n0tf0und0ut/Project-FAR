from __future__ import annotations
import hashlib, json, os, subprocess, tempfile, unittest
from pathlib import Path
from unittest import mock
from tools import promote_living_research as p
from tools import check_living_promotion_head as integrity


def D(value): return (json.dumps(value, sort_keys=True) + "\n").encode()
def H(value): return hashlib.sha256(value).hexdigest()
CID = "FAR-LIT-0123456789ABCDEF"
PID = "FAR-LIVING-PROP-TEST1"

class PromotionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        (self.root / "research/living").mkdir(parents=True); (self.root / "docs").mkdir()
        for name in ("promotion-policy-v1.0.json", "promotion-authorizations-v1.0.json", "snapshot-authorizations-v1.0.json"):
            (self.root / "research/living" / name).write_bytes((Path("research/living") / name).read_bytes())
        (self.root / "research/living/lifecycle-v1.0.json").write_bytes(D({"stages":[{"id":"DISCOVERED","automation_may_enter":True},{"id":"PROMOTION_PROPOSED","automation_may_enter":False}]}))
        self.reviews([])
        subprocess.run(["git","init","-q"], cwd=self.root, check=True)
        # These repositories are disposable test fixtures. Automatic Git maintenance is
        # outside the test contract and may detach a pack-writing process that races
        # TemporaryDirectory cleanup on CI.
        subprocess.run(["git","config","maintenance.auto","false"], cwd=self.root, check=True)
        subprocess.run(["git","config","gc.auto","0"], cwd=self.root, check=True)
        subprocess.run(["git","config","user.email","test@example.com"], cwd=self.root, check=True)
        subprocess.run(["git","config","user.name","test"], cwd=self.root, check=True)
        subprocess.run(["git","add","."], cwd=self.root, check=True); subprocess.run(["git","commit","-qm","base"], cwd=self.root, check=True)
        self.base = subprocess.check_output(["git","rev-parse","HEAD"], cwd=self.root, text=True).strip(); self.source = "a"*40
        self.mainref(self.base)
    def tearDown(self): self.tmp.cleanup()
    def mainref(self,sha): subprocess.run(["git","update-ref","refs/heads/origin/main",sha],cwd=self.root,check=True)
    def reviews(self, rows): (self.root / "research/living/review-dispositions-v1.0.json").write_bytes(D({"reviewed_candidates":rows}))
    def candidate(self, source_key="doi:x"): return D({"authority":"Research","candidate_id":CID,"source_key":source_key,"lifecycle":{"stage":"DISCOVERED"}})
    def plan(self, files): return p.build(self.root, p.MemorySource(files, self.source), self.source, self.base)
    def verify_fixture(self):
        # verify() takes the CI ref from the environment. A synthetic fixture must be judged the
        # same on every runner, including a workflow running on a real promotion branch.
        with mock.patch.dict(os.environ):
            os.environ.pop("GITHUB_HEAD_REF",None); os.environ.pop("GITHUB_REF_NAME",None)
            return integrity.verify(self.root)
    def provenance(self):
        out={}
        for key in p.PROV_KEYS:
            path=f"docs/{key}.md"; data=(key+"\n").encode(); (self.root/path).write_bytes(data); out[key]={"path":path,"sha256":H(data)}
        subprocess.run(["git","add","docs"], cwd=self.root, check=True)
        if subprocess.check_output(["git","status","--porcelain"],cwd=self.root,text=True).strip(): subprocess.run(["git","commit","-qm","provenance"], cwd=self.root, check=True)
        self.base=subprocess.check_output(["git","rev-parse","HEAD"], cwd=self.root, text=True).strip(); self.mainref(self.base); return out
    def fixture(self, *, target="theory/x.md", bad_payload=False, duplicate_target=False, bad_prov=False):
        candidate=self.candidate("doi:a"); prov=self.provenance()
        if bad_prov: prov["acceptance"]["sha256"]="0"*64
        payload=b"new\n"; op={"op":"write_file","path":target,"source_path":f"{p.PAYLOADS}{PID}/x.md","expected_main_sha256":"ABSENT","result_sha256":"0"*64 if bad_payload else H(payload)}
        operations=[op, dict(op)] if duplicate_target else [op]
        proposal={"schema_version":"1.0","proposal_id":PID,"candidate_id":CID,"candidate_sha256":H(candidate),"lifecycle_stage":"PROMOTION_PROPOSED","provenance":prov,"operations":operations}; raw=D(proposal)
        auth={"proposal_id":PID,"candidate_id":CID,"proposal_sha256":H(raw),"candidate_sha256":H(candidate),"operations_sha256":p.canonical_json_sha(operations),"lifecycle_stage":"PROMOTION_PROPOSED","authorization_status":p.AUTH_STATUS,"provenance_sha256":{k:v["sha256"] for k,v in prov.items()}}
        (self.root/p.AUTHS).write_bytes(D({"schema_version":"1.1","program_id":"FAR-LIVING-PROMOTION-AUTHORIZATIONS-001","authority":"Research","authorizations":[auth]}))
        subprocess.run(["git","add",str(p.AUTHS)], cwd=self.root, check=True); subprocess.run(["git","commit","-qm","authorize"], cwd=self.root, check=True)
        self.base=subprocess.check_output(["git","rev-parse","HEAD"], cwd=self.root, text=True).strip(); self.mainref(self.base)
        return {f"{p.CANDIDATES}{CID}.json":candidate,f"{p.PROPOSALS}{PID}.json":raw,f"{p.PAYLOADS}{PID}/x.md":payload}
    def test_ephemeral_repo_disables_automatic_maintenance(self):
        self.assertEqual("false", subprocess.check_output(["git","config","--bool","maintenance.auto"], cwd=self.root, text=True).strip())
        self.assertEqual("0", subprocess.check_output(["git","config","--int","gc.auto"], cwd=self.root, text=True).strip())
    def test_reviewed_candidate_requires_exact_path(self):
        basis="docs/review.md"; (self.root/basis).write_text("review\n")
        self.reviews([{"candidate_id":CID,"source_key":"doi:x","disposition":"N1_PRIOR_ART_LEAD","review_basis":basis}]); subprocess.run(["git","add",str(p.REVIEWS),basis],cwd=self.root,check=True); subprocess.run(["git","commit","-qm","review"],cwd=self.root,check=True); self.base=subprocess.check_output(["git","rev-parse","HEAD"],cwd=self.root,text=True).strip(); self.mainref(self.base)
        self.assertTrue(self.plan({f"{p.CANDIDATES}{CID}.json":self.candidate()})["actionable"])
        with self.assertRaises(p.PromotionError): self.plan({f"{p.CANDIDATES}nested.json":self.candidate()})
    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(p.PromotionError): p.loadb(b'{"a":1,"a":2}',"x")
    def test_proposal_hash_provenance_target_and_duplicate_guards(self):
        self.assertTrue(self.plan(self.fixture())["actionable"])
        self.assertTrue(self.plan(self.fixture(bad_payload=True))["fatal"])
        self.assertTrue(self.plan(self.fixture(bad_prov=True))["fatal"])
        self.assertTrue(self.plan(self.fixture(target="tools/x.json"))["fatal"])
        self.assertTrue(self.plan(self.fixture(target=str(p.POLICY)))["fatal"])
        self.assertTrue(self.plan(self.fixture(duplicate_target=True))["fatal"])
    def test_symlink_target_rejected(self):
        files=self.fixture(); (self.root/"theory").mkdir(exist_ok=True); (self.root/"theory/x.md").symlink_to("../docs/question.md")
        self.assertTrue(self.plan(files)["fatal"])
    def test_generated_views_cannot_be_supplied_as_canonical_payloads(self):
        for path in p.load(self.root / p.POLICY)["trusted_generated_paths"]:
            with self.subTest(path=path):
                self.assertTrue(self.plan(self.fixture(target=path))["fatal"])
    def test_precommit_seals_exact_staged_paths_and_rejects_extras(self):
        files=self.fixture(); plan=self.plan(files); src=p.MemorySource(files,self.source); p.materialize(self.root,src,plan)
        generated=p.load(self.root/p.POLICY)["trusted_generated_paths"]
        for path in generated:
            q=self.root/path; q.parent.mkdir(parents=True,exist_ok=True); q.write_text("generated\n")
        subprocess.run(["git","add","-A"],cwd=self.root,check=True)
        manifest=p.precommit_seal(self.root,plan,refresh_main=False)
        self.assertTrue(manifest["sealed_files"])
        self.assertIn(f"{p.MANIFESTS}{self.source}.json", subprocess.check_output(["git","diff","--cached","--name-only"],cwd=self.root,text=True).splitlines())
        subprocess.run(["git","reset","--hard","HEAD"],cwd=self.root,check=True,stdout=subprocess.DEVNULL)
        p.materialize(self.root,src,plan); (self.root/"docs/unexpected.md").write_text("x"); subprocess.run(["git","add","-A"],cwd=self.root,check=True)
        with self.assertRaises(p.PromotionError): p.precommit_seal(self.root,plan,refresh_main=False)
    def test_materialize_installs_fail_closed_precommit_hook(self):
        files=self.fixture(); plan=self.plan(files); plan_path=Path(self.tmp.name).parent/(Path(self.tmp.name).name+"-plan.json"); p.dump(plan_path,plan)
        p.materialize(self.root,p.MemorySource(files,self.source),plan); p.install_precommit_hook(self.root,plan_path)
        hook=(self.root/".git/hooks/pre-commit").read_text(); self.assertIn("promote_living_research.py precommit --plan",hook); plan_path.unlink(missing_ok=True)
    def test_stale_nonpromotion_branch_is_not_rejected(self):
        base=self.base
        (self.root/"docs/feature.md").write_text("feature\n"); subprocess.run(["git","add","docs/feature.md"],cwd=self.root,check=True); subprocess.run(["git","commit","-qm","feature"],cwd=self.root,check=True); feature=subprocess.check_output(["git","rev-parse","HEAD"],cwd=self.root,text=True).strip()
        subprocess.run(["git","checkout","-q","-b","advance",base],cwd=self.root,check=True); (self.root/"docs").mkdir(exist_ok=True); (self.root/"docs/main.md").write_text("main\n"); subprocess.run(["git","add","docs/main.md"],cwd=self.root,check=True); subprocess.run(["git","commit","-qm","advance"],cwd=self.root,check=True); advance=subprocess.check_output(["git","rev-parse","HEAD"],cwd=self.root,text=True).strip(); self.mainref(advance)
        subprocess.run(["git","checkout","-q","--detach",feature],cwd=self.root,check=True)
        self.assertEqual([],self.verify_fixture())
    def test_stale_promotion_branch_is_rejected(self):
        files=self.fixture(); plan=self.plan(files); base=plan["base_main_sha"]
        p.materialize(self.root,p.MemorySource(files,self.source),plan); subprocess.run(["git","add","-A"],cwd=self.root,check=True); p.precommit_seal(self.root,plan,refresh_main=False); subprocess.run(["git","commit","-qm","promotion","--no-verify"],cwd=self.root,check=True); promotion=subprocess.check_output(["git","rev-parse","HEAD"],cwd=self.root,text=True).strip()
        subprocess.run(["git","checkout","-q","-b","advance",base],cwd=self.root,check=True); (self.root/"docs/main-advance.md").write_text("main\n"); subprocess.run(["git","add","docs/main-advance.md"],cwd=self.root,check=True); subprocess.run(["git","commit","-qm","advance"],cwd=self.root,check=True); advance=subprocess.check_output(["git","rev-parse","HEAD"],cwd=self.root,text=True).strip(); self.mainref(advance)
        subprocess.run(["git","checkout","-q","--detach",promotion],cwd=self.root,check=True)
        errors=self.verify_fixture(); self.assertTrue(any("base is stale" in e for e in errors),errors)
    def test_valid_promotion_commit_passes_independent_head_verifier(self):
        files=self.fixture(); plan=self.plan(files)
        p.materialize(self.root,p.MemorySource(files,self.source),plan); subprocess.run(["git","add","-A"],cwd=self.root,check=True); p.precommit_seal(self.root,plan,refresh_main=False); subprocess.run(["git","commit","-qm","promotion","--no-verify"],cwd=self.root,check=True); branch="automation/living-promotion-"+self.source+"-"+plan["base_main_sha"]
        old_head=os.environ.get("GITHUB_HEAD_REF"); old_ref=os.environ.get("GITHUB_REF_NAME"); os.environ.pop("GITHUB_HEAD_REF",None); os.environ["GITHUB_REF_NAME"]=branch
        try:
            with mock.patch.object(integrity,"_verify_generated_outputs"):
                self.assertEqual([],integrity.verify(self.root))
        finally:
            if old_head is None: os.environ.pop("GITHUB_HEAD_REF",None)
            else: os.environ["GITHUB_HEAD_REF"]=old_head
            if old_ref is None: os.environ.pop("GITHUB_REF_NAME",None)
            else: os.environ["GITHUB_REF_NAME"]=old_ref
    def test_generated_reconciliation_replays_base_plus_planned_state(self):
        (self.root/"planned.txt").write_text("old\n"); (self.root/"generated.txt").write_text("previous\n")
        subprocess.run(["git","add","planned.txt","generated.txt"],cwd=self.root,check=True); subprocess.run(["git","commit","-qm","generated-base"],cwd=self.root,check=True)
        base=subprocess.check_output(["git","rev-parse","HEAD"],cwd=self.root,text=True).strip()
        (self.root/"planned.txt").write_text("new\n"); (self.root/"generated.txt").write_text("changed\n")
        subprocess.run(["git","add","planned.txt","generated.txt"],cwd=self.root,check=True); subprocess.run(["git","commit","-qm","generated-head"],cwd=self.root,check=True)
        head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=self.root,text=True).strip()
        def fake_reconcile(root):
            prior=(root/"generated.txt").read_text(); planned=(root/"planned.txt").read_text()
            (root/"generated.txt").write_text("changed\n" if prior=="previous\n" and planned=="new\n" else "replayed\n")
        with mock.patch("tools.reconcile_living_repo.reconcile",side_effect=fake_reconcile):
            integrity._verify_generated_outputs(self.root,base,head,{"planned.txt"},{"generated.txt"})
        (self.root/"generated.txt").write_text("tampered\n"); subprocess.run(["git","add","generated.txt"],cwd=self.root,check=True); subprocess.run(["git","commit","--amend","-qm","generated-head"],cwd=self.root,check=True)
        tampered=subprocess.check_output(["git","rev-parse","HEAD"],cwd=self.root,text=True).strip()
        with mock.patch("tools.reconcile_living_repo.reconcile",side_effect=fake_reconcile):
            with self.assertRaises(integrity.IntegrityError): integrity._verify_generated_outputs(self.root,base,tampered,{"planned.txt"},{"generated.txt"})
    def test_checked_out_repository_head_is_integrity_valid(self):
        repo=Path(__file__).resolve().parents[1]
        self.assertEqual([],integrity.verify(repo))

if __name__ == "__main__": unittest.main()
