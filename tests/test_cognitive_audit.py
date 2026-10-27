"""Hostile contract and mechanism checks; synthetic data, not external validity."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from decimal import localcontext

from mechanization.far_mechanization.cognitive import CognitiveDocument, CognitiveValidationError, RULES, audit

ROOT = Path(__file__).resolve().parents[1]


class CognitiveAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads((ROOT/'research/cognitive-audit/frozen-v1/cases.json').read_text())['cases']
        cls.by_id = {x['id']: x['input'] for x in cls.cases}

    def test_frozen_rule_statuses_and_bounded_outputs(self):
        self.assertEqual(set(RULES), {x['input']['probes'][0]['rule'] for x in self.cases})
        for row in self.cases:
            with self.subTest(case=row['id']):
                result = audit(CognitiveDocument.from_dict(row['input']))
                diagnosis = result['diagnoses'][0]
                self.assertEqual(diagnosis['status'], row['reference_status'])
                self.assertEqual(diagnosis['mental_cause'], 'UNKNOWN')
                self.assertEqual(diagnosis['coding_fidelity'], 'UNKNOWN')
                self.assertIsNone(diagnosis['diagnostic_confidence']['probability'])
                self.assertFalse(result['scientific_promotion_authority'])
                self.assertTrue(all(key in diagnosis for key in ['source_span_or_trace','observation','candidate_failure_mode','diagnostic_rule_version','alternative_explanations','counterevidence','assurance_level','scope','retest_or_falsifier','limitations']))

    def test_tamper_quotes_hashes_unknown_fields_and_forbidden_diagnoses(self):
        for mutation in ('quote', 'hash', 'field', 'rule', 'range', 'missing-counter-anchor'):
            value = copy.deepcopy(self.by_id['intent-contradiction'])
            if mutation == 'quote': value['probes'][0]['source_span_or_trace'][0]['quote'] = 'changed'
            if mutation == 'hash': value['sources'][0]['sha256'] = '0'*64
            if mutation == 'field': value['speaker_is_narcissistic'] = True
            if mutation == 'rule': value['probes'][0]['rule'] = 'AI_IS_CONSCIOUS'
            if mutation == 'range': value['probes'][0]['source_span_or_trace'][0]['end_byte'] = 1000000
            if mutation == 'missing-counter-anchor': value['probes'][0]['counterevidence'] = [{'trace_ref':'absent'}]
            with self.subTest(mutation=mutation), self.assertRaises(CognitiveValidationError):
                CognitiveDocument.from_dict(value)

    def test_strict_json_and_utf8_boundaries(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
            with self.assertRaises(CognitiveValidationError): CognitiveDocument.loads(raw)
        value = copy.deepcopy(self.by_id['intent-contradiction'])
        value['sources'][0]['text'] = 'é'
        import hashlib
        value['sources'][0]['sha256'] = hashlib.sha256('é'.encode()).hexdigest()
        value['probes'][0]['source_span_or_trace'][0].update(start_byte=0,end_byte=1,quote='é')
        with self.assertRaises(CognitiveValidationError): CognitiveDocument.from_dict(value)

    def test_reference_closure_and_snapshot_commitments(self):
        for name in ('user_stance-shift','lineage-copy','bayes-match','selection-omitted'):
            value = copy.deepcopy(self.by_id[name])
            if name == 'user_stance-shift': value['probes'][0]['facts']['right'] = 'missing'
            if name == 'lineage-copy': value['source_lineage'][1]['upstream_source_ids'] = ['copy']
            if name == 'bayes-match': value['epistemic_document']['snapshots'][0]['hypothesis_probabilities']['h.rain'] = '0.400000'
            if name == 'selection-omitted': value['probes'][0]['facts']['selected_refs'] = ['missing']
            with self.subTest(name=name), self.assertRaises(CognitiveValidationError): CognitiveDocument.from_dict(value)

    def test_immutable_document_and_ambient_decimal_precision(self):
        value = copy.deepcopy(self.by_id['bayes-mismatch'])
        doc = CognitiveDocument.from_dict(value); expected = audit(doc)
        value['id'] = 'mutated'; doc.to_dict()['id'] = 'changed'
        with localcontext() as context:
            context.prec = 3
            self.assertEqual(audit(doc), expected)

    def test_cli_and_existing_learning_reuse(self):
        result = subprocess.run([sys.executable,'-m','mechanization.far_mechanization.cli','cognitive','audit','examples/cognitive/inconsistency-is-not-intent.json'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['diagnoses'][0]['status'],'SUPPORTED')
        scores = audit(CognitiveDocument.from_dict(self.by_id['bayes-match']))['existing_epistemic_scores']
        self.assertTrue(scores)
        self.assertEqual(scores[0]['resolved_count'],2)


if __name__ == '__main__': unittest.main()
