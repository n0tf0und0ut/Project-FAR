"""Internal adversarial checks; not scientific replication or scored benchmark runs."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from tools import model_architecture_external as mas


DATA_SHA={"digits":"f6d9e39f37dc45d327f6db33428ee58970ccceabb2535a5c179de35886b70443",
          "breast_cancer":"25e2eb7b7a8745b1bde5ba18bc4969983d2e2f403291ecd5bde4a29ef30c3859"}
SPLIT_SHA={"digits":"52aa6260697bb7fd91a1b48cb3b07ab3f6a8a21fa969894fd53aa4fc82d05b9b",
           "breast_cancer":"18d62d14ccb655953ad1c7ecb861511f16c77344109dca9d1a769fbe52277d99"}


def protocol():
    return {"version":mas.VERSION,"study_id":"TEST-ONLY","datasets":list(mas.DATASETS),
            "split_seed":20261103,"scales":[48,72],"steps_budgets":[8,16],
            "seeds":[111,112],"batch_size":64,"learning_rate":0.004,
            "max_param_relative_error":0.11,"max_mac_relative_error":0.11,"training_threads":1,
            "comparison":list(mas.FAMILIES),"device":"cpu",
            "selection_policy":"mean_validation_accuracy_then_cost_then_name",
            "acceptance":{"primary_scale":72,"primary_steps":16,"min_test_gain":0.02,"max_selection_regret":0.02},
            "precommit_source_sha256":mas.file_sha(mas.__file__),
            "expected_data_sha256":DATA_SHA,"expected_split_sha256":SPLIT_SHA}


def training_fixture(classes=10,train_size=100,validation_size=30):
    """Nonbenchmark smoke-test data; every evaluation class must be present."""
    import torch
    rng=torch.Generator().manual_seed(42)
    return {"tokens":8,"token_features":8,"classes":classes,"tensors":{
        "train":(torch.rand(train_size,8,8,generator=rng),torch.arange(train_size)%classes),
        "validation":(torch.rand(validation_size,8,8,generator=rng),torch.arange(validation_size)%classes)}}


class ProtocolTests(unittest.TestCase):
    def test_protocol_mutations_fail_closed(self):
        p=protocol();mas.check(p)
        mutations=[("device","cuda"),("datasets",["digits"]),("scales",[48,48]),
                   ("seeds",[111,111]),("max_mac_relative_error",0.6),
                   ("precommit_source_sha256","BAD"),("expected_data_sha256",{})]
        for k,v in mutations:
            with self.subTest(k=k),self.assertRaises(ValueError):
                mas.check({**p,k:v})
        with self.assertRaises(ValueError):
            mas.check({**p,"unexpected":True})

    def test_metric_tampering_fails(self):
        self.assertEqual(mas.grade([1,0,1,1],[1,0,0,1],2)["correct"],3)
        for pred in ([1,2,0,0], [1], [False,1,0,1]):
            with self.subTest(pred=pred),self.assertRaises(ValueError):
                mas.grade(pred,[1,0,0,1],2)
        with self.assertRaisesRegex(ValueError,"missing class in evaluation"):
            mas.grade([0,0],[0,0],2)

    @unittest.skipUnless(importlib.util.find_spec("sklearn"),"optional scikit-learn missing")
    def test_real_data_provenance_and_splits(self):
        for name in mas.DATASETS:
            with self.subTest(name=name):
                d, arrays=mas.read_dataset(name,20261103)
                self.assertEqual(d["raw_sha256"],DATA_SHA[name])
                self.assertEqual(d["split_sha256"],SPLIT_SHA[name])
                sets=[set(d["split_indices"][k]) for k in ("train","validation","test")]
                self.assertFalse(sets[0]&sets[1]);self.assertFalse(sets[0]&sets[2]);self.assertFalse(sets[1]&sets[2])
                self.assertEqual(len(set.union(*sets)),d["shape"][0])
                self.assertEqual(d["scaler_fit_on"],"train_only")

    def test_journal_is_append_only_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"log.jsonl"
            mas.event(p,{"event":"started"})
            mas.event(p,{"event":"failed","error":"reproducer"})
            lines=[json.loads(y) for y in p.read_text().splitlines()]
            self.assertEqual([z["event"] for z in lines],["started","failed"])
            with self.assertRaises(FileExistsError):
                mas.write_once(p,b"replacement")


@unittest.skipUnless(importlib.util.find_spec("torch"),"optional PyTorch missing")
class TorchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        torch.set_num_threads(1)

    def setUp(self):
        import torch
        self.enterContext(torch.random.fork_rng(devices=[]))

    def test_training_fixture_covers_classes_without_ambient_rng_dependency(self):
        import torch
        for classes,train_size,validation_size in ((10,100,30),(2,32,20)):
            reference=training_fixture(classes,train_size,validation_size)
            for seed in (2,42,999):
                with self.subTest(classes=classes,ambient_seed=seed):
                    torch.manual_seed(seed)
                    torch.rand(17)  # Simulate preceding tests consuming the global generator.
                    before=torch.get_rng_state().clone()
                    d=training_fixture(classes,train_size,validation_size)
                    for split,(x,y) in d["tensors"].items():
                        self.assertEqual(set(y.tolist()),set(range(classes)))
                        self.assertTrue(torch.equal(x,reference["tensors"][split][0]))
                        self.assertTrue(torch.equal(y,reference["tensors"][split][1]))
                    self.assertTrue(torch.equal(before,torch.get_rng_state()))

    def test_all_architectures_train_and_share_output_contract(self):
        d=training_fixture()
        p=protocol()
        sp=mas.specs(8,8,10,48,p)
        for family,spec in sp.items():
            with self.subTest(family=family):
                self.assertTrue(spec["within_registered_cost_bounds"])
                self.assertLessEqual(abs(spec["parameter_relative_difference"]),.11)
                self.assertLessEqual(abs(spec["estimated_mac_relative_difference"]),.11)
                net,record=mas.train_one(spec,d,p,2,999)
                self.assertEqual(len(record["validation_predictions"]),30)
                self.assertEqual(sum(x.numel() for x in net.parameters()),spec["parameters"])

    def test_model_scale_and_cost_match_on_registered_shapes(self):
        p=protocol()
        for n,features,classes in ((8,8,10),(30,1,2)):
            for scale in p["scales"]:
                matches=mas.specs(n,features,classes,scale,p)
                self.assertTrue(all(z["within_registered_cost_bounds"] for z in matches.values()))
                self.assertEqual(len(matches),4)
                for z in matches.values():
                    self.assertGreater(z["estimated_forward_macs"],0)

    def test_per_seed_repeatability_on_nonbenchmark_random_data(self):
        d=training_fixture(classes=2,train_size=32,validation_size=20)
        p=protocol()
        s=mas.specs(8,8,2,48,p)["one_attn"]
        a,ar=mas.train_one(s,d,p,2,333)
        b,br=mas.train_one(s,d,p,2,333)
        self.assertEqual(ar["validation_predictions"],br["validation_predictions"])
        self.assertEqual(mas.fingerprint(a),mas.fingerprint(b))

if __name__=="__main__":
    unittest.main()
