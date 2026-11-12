"""Failure-oriented controls for the isolated Research search scheduler."""
import unittest
from tools.factory_guided_search import SearchInputError, run_search

BASE = 'a' * 40
ORACLE = 'b' * 64


def candidate(i):
    return {'candidate_id': f'c{i}', 'base_sha': BASE, 'source_sha': f'{i+1:040x}', 'artifact_sha256': f'{i+1:064x}'}


def receipt(c, *, test='PASS', contract='PASS', price=0, elapsed=1):
    return {'candidate_id': c['candidate_id'], 'source_sha': c['source_sha'],
            'oracle_sha256': ORACLE, 'test_status': test, 'contract_status': contract,
            'cost_micro_usd': price, 'elapsed_ms': elapsed, 'evidence_sha256': 'f'*64}


class GuidedSearchTests(unittest.TestCase):
    def search(self, evaluator, proposer=None, **opts):
        return run_search(proposer or (lambda i, _: candidate(i)), evaluator,
                          base_sha=BASE, oracle_sha256=ORACLE, **opts)

    def test_select_lowest_cost_then_time_after_hard_gates(self):
        r = self.search(lambda c: receipt(c, elapsed=5 if c['candidate_id'] == 'c0' else 2))
        self.assertEqual(r['selected_candidate']['candidate_id'], 'c1')
        self.assertEqual(len(r['attempts']), 3)
        self.assertEqual(r['status'], 'CANDIDATE_PENDING_INDEPENDENT_VERIFICATION')

    def test_unknown_contract_never_passes(self):
        r = self.search(lambda c: receipt(c, contract='UNKNOWN'))
        self.assertIsNone(r['selected_candidate'])
        self.assertEqual([x['status'] for x in r['attempts']], ['INELIGIBLE'] * 3)

    def test_failed_tests_never_pass(self):
        r = self.search(lambda c: receipt(c, test='FAIL'))
        self.assertIsNone(r['selected_candidate'])

    def test_wrong_oracle_digest_is_rejected(self):
        r = self.search(lambda c: {**receipt(c), 'oracle_sha256': 'c' * 64})
        self.assertEqual([x['status'] for x in r['attempts']], ['EVALUATION_ERROR'] * 3)

    def test_invalid_provenance_still_debits_reported_cost(self):
        # SF-GUIDED-COST-001: mismatched oracle evidence cannot erase a
        # positive evaluator-reported cost and continue beyond the budget.
        seen = []
        def wrong_oracle(c):
            seen.append(c["candidate_id"])
            return {**receipt(c, price=1), "oracle_sha256": "c" * 64}
        exhausted = self.search(wrong_oracle, max_cost_micro_usd=0)
        self.assertEqual(seen, ["c0"])
        self.assertEqual(exhausted["termination"], "BUDGET_EXCEEDED")
        self.assertEqual(exhausted["total_reported_cost_micro_usd"], 1)
        self.assertEqual([x["status"] for x in exhausted["attempts"]],
                         ["BUDGET_EXCEEDED"])
        self.assertIsNone(exhausted["selected_candidate"])
        self.assertNotIn(ORACLE, repr(exhausted))

        seen.clear()
        gradual = self.search(wrong_oracle, max_cost_micro_usd=2)
        self.assertEqual(seen, ["c0", "c1", "c2"])
        self.assertEqual(gradual["total_reported_cost_micro_usd"], 3)
        self.assertEqual([x["status"] for x in gradual["attempts"]],
                         ["EVALUATION_ERROR", "EVALUATION_ERROR", "BUDGET_EXCEEDED"])
        self.assertIsNone(gradual["selected_candidate"])

    def test_valid_reported_cost_is_never_double_counted(self):
        value = self.search(lambda c: receipt(c, price=1), max_cost_micro_usd=3)
        self.assertEqual(value["total_reported_cost_micro_usd"], 3)
        self.assertEqual(value["termination"], "ATTEMPTS_EXHAUSTED")
        self.assertEqual([x["status"] for x in value["attempts"]], ["ELIGIBLE"] * 3)

    def test_receipt_for_wrong_commit_rejected(self):
        r = self.search(lambda c: {**receipt(c), 'source_sha': 'e' * 40})
        self.assertIsNone(r['selected_candidate'])

    def test_receipt_rejects_non_string_identity_and_status(self):
        class Impostor:
            def __eq__(self, other):
                return True

            def __hash__(self):
                return hash("PASS")

        cases = {
            "candidate_id": Impostor(),
            "source_sha": Impostor(),
            "test_status": Impostor(),
            "contract_status": Impostor(),
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                result = self.search(lambda c: {**receipt(c), field: value})
                self.assertIsNone(result["selected_candidate"])
                self.assertEqual(result["attempts"][0]["error_type"], "SearchInputError")

        result = self.search(lambda c: receipt(c, test=[]))
        self.assertEqual(result["attempts"][0]["error_type"], "SearchInputError")

    def test_duplicate_identity_is_rejected_even_if_oracle_claims_pass(self):
        r = self.search(lambda c: receipt(c), proposer=lambda i, f: candidate(0))
        self.assertEqual([x['status'] for x in r['attempts']], ['ELIGIBLE', 'INVALID_PROPOSAL', 'INVALID_PROPOSAL'])

    def test_proposal_source_must_be_bound_to_base(self):
        r = self.search(lambda c: receipt(c), proposer=lambda i, f: {**candidate(i), 'base_sha': 'e'*40})
        self.assertEqual([x['status'] for x in r['attempts']], ['INVALID_PROPOSAL'] * 3)

    def test_reported_cost_over_budget_stops_without_selecting_overbudget_candidate(self):
        r = self.search(lambda c: receipt(c, price=1), max_cost_micro_usd=0)
        self.assertEqual(r['termination'], 'BUDGET_EXCEEDED')
        self.assertEqual(len(r['attempts']), 1)
        self.assertIsNone(r['selected_candidate'])
        self.assertEqual(r['total_reported_cost_micro_usd'], 1)

    def test_prior_eligible_survives_later_cost_exhaustion(self):
        r = self.search(lambda c: receipt(c, price=0 if c['candidate_id'] == 'c0' else 1))
        self.assertEqual(r['termination'], 'BUDGET_EXCEEDED')
        self.assertEqual(r['selected_candidate']['candidate_id'], 'c0')

    def test_feedback_does_not_leak_hidden_oracle_or_evidence(self):
        messages = []
        def generate(i, feedback):
            messages.append(feedback)
            return candidate(i)
        self.search(lambda c: receipt(c), proposer=generate)
        self.assertEqual(messages[0], ())
        self.assertEqual(messages[1], ({'slot': 0, 'status': 'ELIGIBLE'},))
        self.assertNotIn(ORACLE, repr(messages))
        self.assertNotIn('evidence_sha256', repr(messages))

    def test_evaluator_failure_preserved_and_search_continues(self):
        def evaluate(c):
            if c['candidate_id'] == 'c0':
                raise RuntimeError('private secret must not leak')
            return receipt(c)
        r = self.search(evaluate)
        self.assertEqual(r['attempts'][0]['status'], 'EVALUATION_ERROR')
        self.assertNotIn('private secret', repr(r))
        self.assertEqual(r['selected_candidate']['candidate_id'], 'c1')

    def test_invalid_limits_fail_closed(self):
        for n in (0, 33, True):
            with self.subTest(n=n), self.assertRaises(SearchInputError):
                self.search(lambda c: receipt(c), max_candidates=n)
        with self.assertRaises(SearchInputError):
            self.search(lambda c: receipt(c), max_cost_micro_usd=True)

    def test_bool_cost_does_not_pass_integer_validation(self):
        r = self.search(lambda c: {**receipt(c), 'cost_micro_usd': True})
        self.assertEqual([x['status'] for x in r['attempts']], ['EVALUATION_ERROR'] * 3)

if __name__ == '__main__':
    unittest.main()
