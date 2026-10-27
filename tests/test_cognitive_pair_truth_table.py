"""Review4390630419: an observed disjunct must survive an unknown alternative."""
import copy
from itertools import product
import json
from pathlib import Path
import unittest
from mechanization.far_mechanization.cognitive import CognitiveDocument, audit

ROOT=Path(__file__).resolve().parents[1]


class PairTruthTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cases=json.loads((ROOT/'research/cognitive-audit/frozen-v1/cases.json').read_text())['cases']
        cls.base=next(x['input'] for x in cases if x['id']=='user_stance-stable')

    def test_sensitivity_three_valued_or_all_eighty_one_observations(self):
        for p,q,a,b in product(('YES','NO','UNKNOWN'),('YES','NO','UNKNOWN'),(None,'0.200000','0.800000'),(None,'0.200000','0.800000')):
            data=copy.deepcopy(self.base)
            data['traces'][0].update(position=p,confidence=a);data['traces'][1].update(position=q,confidence=b)
            observed_positive=(p!='UNKNOWN' and q!='UNKNOWN' and p!=q) or (a is not None and b is not None and a!=b)
            observations_complete='UNKNOWN' not in (p,q) and None not in (a,b)
            expected='SUPPORTED' if observed_positive else 'CONTRADICTED' if observations_complete else 'UNKNOWN'
            with self.subTest(p=p,q=q,a=a,b=b):
                self.assertEqual(audit(CognitiveDocument.from_dict(data))['diagnoses'][0]['status'],expected)

    def test_cross_turn_position_predicate_ignores_confidence_all_eighty_one_observations(self):
        for p,q,a,b in product(('YES','NO','UNKNOWN'),('YES','NO','UNKNOWN'),(None,'0.200000','0.800000'),(None,'0.200000','0.800000')):
            data=copy.deepcopy(self.base)
            data['traces'][0].update(position=p,confidence=a);data['traces'][1].update(position=q,confidence=b)
            data['traces'][1]['conditions']=copy.deepcopy(data['traces'][0]['conditions'])
            data['probes'][0]['rule']='cross-turn-conflict';data['probes'][0]['facts'].pop('factor')
            expected='UNKNOWN' if 'UNKNOWN' in (p,q) else 'SUPPORTED' if p!=q else 'CONTRADICTED'
            with self.subTest(p=p,q=q,a=a,b=b):
                self.assertEqual(audit(CognitiveDocument.from_dict(data))['diagnoses'][0]['status'],expected)


if __name__=='__main__':unittest.main()
