"""Replays of native length and model-budget failure cases."""
import copy
import unittest
from unittest.mock import Mock

from tools.far_investigation_audit import audit
from tools.far_investigation_engine import Investigation
from tools.far_investigation_retrieval import RetrievalPolicy, retrieve
from tests.test_far_investigation_audit import NativeFunctionFixtureModel, reseal
from tests.test_far_investigation_engine import BODY_A, BODY_B, QUESTION, URL_A, full_script
from tests.test_far_investigation_retrieval import Response, dns


class InvestigationReviewerRegressionTests(unittest.TestCase):
    def test_complete_native_body_must_match_declared_length(self):
        def fetch(url, policy, checkpoint):
            client = Mock()
            body = ('<script>'+BODY_A+'</script>') if url == URL_A else BODY_B
            client.open.return_value = Response(body.encode(), url=url)
            return retrieve(url, policy, checkpoint=checkpoint, opener=client)

        state=Investigation(QUESTION,
            RetrievalPolicy(('example.org','independent.example.org'),resolver=dns),
            fetcher=fetch).run_agent(NativeFunctionFixtureModel(full_script()))
        self.assertTrue(audit(state)['valid'])
        copy_state=copy.deepcopy(state)
        mutated=[0]
        def walk(node):
            if isinstance(node,dict):
                if node.get('status')=='RETRIEVED' and isinstance(node.get('transport'),dict):
                    node['transport']['content_length_values']=['9999']
                    node['transport']['response_headers']['Content-Length']='9999'
                    mutated[0]+=1
                for value in node.values():
                    walk(value)
            elif isinstance(node,list):
                for value in node:
                    walk(value)
        walk(copy_state)
        self.assertGreater(mutated[0],0)
        reseal(copy_state)
        errors=audit(copy_state)['errors']
        self.assertTrue(any('content_length' in e for e in errors),errors)


if __name__=='__main__':
    unittest.main()
