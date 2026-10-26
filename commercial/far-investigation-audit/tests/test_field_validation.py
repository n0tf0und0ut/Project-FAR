"""Hostile tests for a bounded external-evidence scorer. Does not supply real-world truth."""
import math
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from field_validation import (evaluate, upper_error_rate, InvalidFieldEvaluation,
                              predictions_from_far_bundle, read_json)
from full_cli import write_package
from workflow import investigate

GOLD={'case_id':'case01','domain':'news','reference_verdict':'SUPPORTED',
      'mapping_fidelity':'FAITHFUL','evidence_adequacy':'ADEQUATE',
      'temporal_eligibility':'IN_WINDOW'}

class FieldScorerTests(unittest.TestCase):
    def test_correct_decisive(self):
        s=evaluate([{'case_id':'case01','verdict':'SUPPORTED'}],[GOLD])
        self.assertEqual(s['overall']['decisive'],1)
        self.assertEqual(s['overall']['false_certainty'],0)
        self.assertFalse(s['real_world_truth_proven'])
        self.assertFalse(s['reference_independence_verified'])

    def test_wrong_decisive(self):
        s=evaluate([{'case_id':'case01','verdict':'REFUTED'}],[GOLD])
        self.assertEqual(s['overall']['false_certainty'],1)

    def test_relevant_truth_without_adequate_evidence_fails(self):
        s=evaluate([{'case_id':'case01','verdict':'SUPPORTED'}],[{**GOLD,'evidence_adequacy':'INADEQUATE'}])
        self.assertEqual(s['overall']['false_certainty'],1)

    def test_wrong_mapping_with_correct_label_fails(self):
        s=evaluate([{'case_id':'case01','verdict':'SUPPORTED'}],[{**GOLD,'mapping_fidelity':'UNFAITHFUL'}])
        self.assertEqual(s['overall']['false_certainty'],1)

    def test_post_claim_evidence_with_correct_label_fails(self):
        s=evaluate([{'case_id':'case01','verdict':'SUPPORTED'}],[{**GOLD,'temporal_eligibility':'NOT_ADMISSIBLE'}])
        self.assertEqual(s['overall']['false_certainty'],1)

    def test_disputed_reference_cannot_reward_certainty(self):
        s=evaluate([{'case_id':'case01','verdict':'SUPPORTED'}],[{**GOLD,'mapping_fidelity':'DISPUTED'}])
        self.assertEqual(s['overall']['false_certainty'],1)

    def test_abstention_is_not_accuracy(self):
        s=evaluate([{'case_id':'case01','verdict':'ABSTAIN'}],[GOLD])
        self.assertIsNone(s['overall']['false_certainty_rate_given_decisive'])
        self.assertEqual(s['overall']['coverage'],0)

    def test_insufficient_is_not_a_factual_verdict(self):
        gold = {**GOLD, 'reference_verdict':'INSUFFICIENT',
                'evidence_adequacy':'INADEQUATE', 'temporal_eligibility':'UNKNOWN'}
        score=evaluate([{'case_id':'case01','verdict':'INSUFFICIENT'}],[gold])
        self.assertEqual(score['schema'],'far-field-evaluation-score/0.2')
        self.assertEqual(score['overall']['decisive'],0)
        self.assertEqual(score['overall']['insufficient'],1)
        self.assertEqual(score['overall']['abstained'],0)
        self.assertEqual(score['overall']['insufficient_matches_under_reference'],1)
        self.assertEqual(score['overall']['false_certainty'],0)
        self.assertEqual(score['overall']['coverage'],0)
        self.assertIsNone(score['overall']['upper_false_certainty_rate_given_decisive'])

    def test_insufficient_on_supported_case_is_not_falsely_correct(self):
        score=evaluate([{'case_id':'case01','verdict':'INSUFFICIENT'}],[GOLD])
        self.assertEqual(score['overall']['decisive'],0)
        self.assertEqual(score['overall']['insufficient_matches_under_reference'],0)
        self.assertEqual(score['overall']['false_certainty'],0)
        self.assertEqual(score['overall']['coverage'],0)

    def test_contested_gold_insufficiency_is_nondecisive(self):
        gold={**GOLD,'reference_verdict':'CONTESTED','mapping_fidelity':'DISPUTED'}
        score=evaluate([{'case_id':'case01','verdict':'INSUFFICIENT'}],[gold])
        self.assertEqual(score['overall']['insufficient'],1)
        self.assertEqual(score['overall']['false_certainty'],0)
        self.assertEqual(score['overall']['insufficient_matches_under_reference'],0)

    def test_mixed_factual_insufficient_and_abstained_accounting(self):
        predictions=[{'case_id':'case01','verdict':'REFUTED'},
                     {'case_id':'case02','verdict':'INSUFFICIENT'},
                     {'case_id':'case03','verdict':'ABSTAIN'}]
        gold=[GOLD,{**GOLD,'case_id':'case02','reference_verdict':'INSUFFICIENT',
                    'evidence_adequacy':'INADEQUATE'},
              {**GOLD,'case_id':'case03','domain':'medicine'}]
        score=evaluate(predictions,gold)
        self.assertEqual(score['overall']['cases'],3)
        self.assertEqual(score['overall']['decisive'],1)
        self.assertEqual(score['overall']['insufficient'],1)
        self.assertEqual(score['overall']['abstained'],1)
        self.assertEqual(score['overall']['false_certainty'],1)
        self.assertAlmostEqual(score['overall']['coverage'],1/3)
        self.assertEqual(score['overall']['insufficient_matches_under_reference'],1)
        self.assertEqual(score['by_domain']['medicine']['abstained'],1)

    def test_dropped_case_fails(self):
        with self.assertRaises(InvalidFieldEvaluation):
            evaluate([{'case_id':'case01','verdict':'SUPPORTED'}], [GOLD,{**GOLD,'case_id':'case02'}])

    def test_no_gold_in_prediction(self):
        with self.assertRaises(InvalidFieldEvaluation):
            evaluate([{'case_id':'case01','verdict':'SUPPORTED','reference_verdict':'SUPPORTED'}],[GOLD])

    def test_wrong_gold_schema_fails(self):
        with self.assertRaises(InvalidFieldEvaluation):
            evaluate([{'case_id':'case01','verdict':'SUPPORTED'}],[{**GOLD,'temporal_eligibility':True}])

    def test_duplicate_record_fails(self):
        with self.assertRaises(InvalidFieldEvaluation):
            evaluate([{'case_id':'case01','verdict':'SUPPORTED'},{'case_id':'case01','verdict':'ABSTAIN'}],[GOLD])

    def test_duplicate_json_key_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'dupe.json'
            p.write_text('[{"case_id":"x","verdict":"ABSTAIN","verdict":"SUPPORTED"}]')
            with self.assertRaises(InvalidFieldEvaluation):read_json(p)

    def test_zero_failure_exact_confidence(self):
        for n in (1,10,300,1000):
            self.assertAlmostEqual(upper_error_rate(0,n),1-.05**(1/n),places=11)
        self.assertIsNone(upper_error_rate(0,0))

    def test_all_fail_exact_confidence(self):
        self.assertEqual(upper_error_rate(10,10),1.0)

    def test_one_failure_binomial_inversion(self):
        n,k=15,1
        p=upper_error_rate(k,n)
        self.assertGreater(p,k/n)
        prob=(1-p)**n + n*p*(1-p)**(n-1)
        self.assertAlmostEqual(prob,.05,places=9)

    def test_unreviewed_far_is_abstain_even_for_conditional_support(self):
        config={'investigation_id':'field_eval_smoke','source':{'kind':'text','text':'This is a test premise.'},
                'captured_at':'2026-10-17T10:00:00Z'}
        with tempfile.TemporaryDirectory() as d:
            package=investigate(config)
            directory=Path(d)/'package'
            write_package(directory,package)
            preds=predictions_from_far_bundle(directory)
            self.assertTrue(preds)
            self.assertTrue(all(p['verdict']=='ABSTAIN' for p in preds))

    def test_domain_separation_no_aggregate_mask(self):
        preds=[{'case_id':'case01','verdict':'SUPPORTED'}, {'case_id':'case02','verdict':'REFUTED'}]
        gold=[GOLD,{**GOLD,'case_id':'case02','domain':'medicine'}]
        r=evaluate(preds,gold)
        self.assertEqual(r['by_domain']['news']['false_certainty'],0)
        self.assertEqual(r['by_domain']['medicine']['false_certainty'],1)

    def test_nogo_deterministic_world_pair(self):
        observations='Identical accessible facts, hidden coin event unavailable'
        worlds=[{'observations':observations,'hidden_truth':True},
                {'observations':observations,'hidden_truth':False}]
        for guess in (True,False):
            self.assertEqual(sum(w['hidden_truth']==guess for w in worlds),1)
        self.assertEqual(len(set(w['observations'] for w in worlds)),1)

if __name__ == '__main__':unittest.main()
