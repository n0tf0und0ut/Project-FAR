"""Adversarial structural and actual PyTorch smoke tests for the research pilot."""
import copy
import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import model_architecture_search as mas


def example():
    return {"version":mas.VERSION,"study_id":"FAR-MAS-UNIT-ONLY","search_seed":827,
            "data_seed":100,"sequence_length":8,"train_size":48,
            "validation_size":24,"test_size":24,"width":8,"steps":2,"batch_size":12,
            "learning_rate":0.005,"max_candidates":4,"max_blocks":2,
            "selection_train_seed":7,"final_train_seeds":[11,12],
            "tasks":list(mas.TASKS),"device":"cpu"}


class ProtocolTests(unittest.TestCase):
    def test_disjoint_replayable_splits(self):
        p=example()
        a,b=mas.splits_for(p),mas.splits_for(p)
        self.assertEqual(a,b)
        self.assertEqual(sum(map(len,a.values())),len(set(sum(a.values(),[]))))
        self.assertNotEqual(a,mas.splits_for({**p,"data_seed":101}))

    def test_task_truth(self):
        x=[1,0,1,1,0,1,0,0]
        self.assertEqual(mas.label(x,"remember_first"),1)
        self.assertEqual(mas.label(x,"xor_endpoints"),1)
        self.assertEqual(mas.label(x,"majority"),0)
        with self.assertRaises(ValueError):
            mas.label(x,"unknown")

    def test_invalid_protocol_fails_closed(self):
        p=example()
        for key,value in (("data_seed",True),("sequence_length",4),("train_size",1000),
                          ("device","cuda"),("tasks",["majority"]),
                          ("final_train_seeds",[7,12]),("max_candidates",99)):
            with self.subTest(key=key),self.assertRaises(ValueError):
                mas.validate_protocol({**p,key:value})
        with self.assertRaises(ValueError):
            mas.validate_protocol({**p,"unregistered":"surprise"})
        for bad in (("identity","attn"),("eval",),(),("attn",)*3):
            with self.assertRaises(ValueError):
                mas.validate_recipe(bad,2)

    def test_adaptive_candidates_never_duplicate(self):
        prior=[{"recipe":list(r),"parameters":100,"validation":{"macro_accuracy":i/100}}
               for i,r in enumerate(mas.BASES)]
        rng=random.Random(827)
        for _ in range(5):
            candidate,parent=mas.next_recipe(prior,rng,2)
            self.assertNotIn(list(candidate),[r["recipe"] for r in prior])
            self.assertIn(parent,[mas.identity(r["recipe"]) for r in prior]+["enumeration-fallback"])
            prior.append({"recipe":list(candidate),"parameters":100,"validation":{"macro_accuracy":0.51}})


class ActualComputeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import torch
        except ImportError:
            raise unittest.SkipTest("optional PyTorch not installed")
        torch.set_num_threads(1)

    def test_causal_mixing_no_future_visibility(self):
        import torch
        for recipe in (("attn",),("gru",),("conv",)):
            with self.subTest(recipe=recipe):
                torch.manual_seed(44)
                block=mas.make_model(recipe,8,8).blocks[0].eval()
                a=torch.randn(1,8,8)
                b=a.clone()
                b[:, -1, :]+=100
                with torch.no_grad():
                    self.assertTrue(torch.allclose(block(a)[:,:-1],block(b)[:,:-1],atol=1e-5))

    def run_smoke(self, tmp):
        p=example()
        protocol=mas.encoded(p)+b"\n"
        out=Path(tmp)/"report.json"
        result=mas.run(p,out,protocol)
        journal=Path(str(out)+".journal.jsonl").read_bytes()
        mas.verify(result,journal,local_source=True)
        self.assertEqual(result,json.loads(out.read_text()))
        return result,journal

    def test_complete_experiment_honors_budgets_and_all_comparators(self):
        with tempfile.TemporaryDirectory() as tmp:
            report,journal=self.run_smoke(tmp)
            self.assertEqual(len(report["validation_records"]),4)
            self.assertEqual(len(report["final_records"]),8)
            self.assertEqual({r["seed"] for r in report["final_records"]},{11,12})
            self.assertEqual({tuple(r["recipe"]) for r in report["final_records"]},set(mas.BASES))
            with self.assertRaises(FileExistsError):
                mas.run(example(),Path(tmp)/"report.json",mas.encoded(example())+b"\n")
            with self.assertRaises(ValueError):
                mas.verify(report,journal+b"\n")

    def test_tamper_detection_rejects_spoofed_success_and_missing_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            report,_=self.run_smoke(tmp)
            for variant in ("fake-metric","missing-run","fake-winner","fake-protocol"):
                r=copy.deepcopy(report)
                if variant=="fake-metric":
                    r["final_records"][0]["test"]["macro_accuracy"]=1.0
                elif variant=="missing-run":
                    r["final_records"].pop()
                elif variant=="fake-winner":
                    r["selection"]={"recipe":["gru"],"slot":2,"selection_on":"validation_only"}
                else:
                    r["protocol"]["steps"]+=1
                    r["protocol_sha256"]=mas.digest(mas.encoded(r["protocol"])+b"\n")
                r["report_sha256"]=mas.digest(mas.encoded({k:v for k,v in r.items() if k!="report_sha256"}))
                with self.subTest(variant=variant),self.assertRaises(ValueError):
                    mas.verify(r)

    def test_failing_run_is_never_replaced_with_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=example()
            dest=Path(tmp)/"study.json"
            original=mas.fit
            calls=[0]
            def interrupted(*args,**kwargs):
                calls[0]+=1
                if calls[0]==2:
                    raise RuntimeError("deliberate failure")
                return original(*args,**kwargs)
            with mock.patch.object(mas,"fit",side_effect=interrupted):
                with self.assertRaisesRegex(RuntimeError,"deliberate failure"):
                    mas.run(p,dest,mas.encoded(p)+b"\n")
            failure=json.loads(Path(str(dest)+".failure.json").read_text())
            self.assertEqual(failure["status"],"FAILED_OR_INCOMPLETE")
            self.assertEqual(len(failure["completed_validations"]),1)
            with self.assertRaises(FileExistsError):
                mas.run(p,dest,mas.encoded(p)+b"\n")


if __name__=="__main__":
    unittest.main()
