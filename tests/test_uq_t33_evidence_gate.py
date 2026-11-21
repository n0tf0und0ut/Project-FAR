"""Failure-seeking checks for finite-explicit UQ-T33 correspondence evidence."""
import hashlib
import json
import unittest

from research.uq_t33_effective_quotients.evidence_gate import (
    EvidenceError, certificate, witness,
)


def example():
    # Two unused concrete flags accompany a three-stage controller.
    concrete = {
        "states": [f"{mode}:{flag}" for mode in range(3) for flag in range(2)],
        "actions": ["tick", "reset"],
        "outputs": ["done" if mode == 2 else "busy" for mode in range(3) for _ in range(2)],
        "transitions": [[min(mode + 1, 2) * 2 + flag, flag]
                        for mode in range(3) for flag in range(2)],
    }
    abstract = {
        "states": ["start", "middle", "done"],
        "actions": ["tick", "reset"],
        "outputs": ["busy", "busy", "done"],
        "transitions": [[1, 0], [2, 0], [2, 0]],
    }
    # Reset on concrete state must reset the mode, preserve irrelevant flag.
    d = hashlib.sha256(json.dumps(concrete, sort_keys=True, separators=(",", ":"),
                                  ensure_ascii=False).encode()).hexdigest()
    return {"concrete": concrete, "abstract": abstract,
            "abstraction": [mode for mode in range(3) for _ in range(2)],
            "claimed_state_bound": 3, "expected_concrete_table_sha256": d}


def refresh_digest(record):
    record["expected_concrete_table_sha256"] = hashlib.sha256(
        json.dumps(record["concrete"], sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode()).hexdigest()
    return record


class UQT33EvidenceTests(unittest.TestCase):
    def rejects(self, record, code):
        with self.assertRaises(EvidenceError) as cm:
            certificate(record)
        self.assertEqual(cm.exception.code, code)

    def test_positive_complete_refinement_and_witness(self):
        m = example()
        r = certificate(m)
        self.assertEqual(r["result"], "FINITE_TABLE_REFINEMENT_VERIFIED")
        self.assertEqual(r["external_system_correspondence"], "NOT_VERIFIED")
        self.assertEqual(r["verified_transition_obligations"], 12)
        self.assertEqual(r["word_length_bound"], 1)
        self.assertEqual(witness(m, 0, 2), (0,))
        self.assertIsNone(witness(m, 0, 1))

    def test_missing_action_not_certified(self):
        m = example()
        m["abstract"]["actions"] = ["tick"]
        m["abstract"]["transitions"] = [[1], [2], [2]]
        self.rejects(m, "ACTION_COVERAGE")

    def test_missing_concrete_state_transition_rejected(self):
        m = example()
        m["concrete"]["transitions"][0] = [2]
        self.rejects(m, "TOTALITY")

    def test_hidden_flag_affects_output(self):
        m = example()
        m["concrete"]["outputs"][1] = "done"
        refresh_digest(m)
        self.rejects(m, "OUTPUT_FIDELITY")

    def test_hidden_flag_affects_future_transition(self):
        m = example()
        m["concrete"]["transitions"][0][0] = 4
        refresh_digest(m)
        self.rejects(m, "TRANSITION_FIDELITY")

    def test_out_of_domain_transition_rejected(self):
        m = example()
        m["concrete"]["transitions"][0][0] = 6
        self.rejects(m, "CLOSURE")

    def test_too_small_state_cap_rejected(self):
        m = example()
        m["claimed_state_bound"] = 2
        self.rejects(m, "BOUND")

    def test_forged_or_stale_table_digest_rejected(self):
        m = example()
        m["concrete"]["outputs"][0] = "changed"
        self.rejects(m, "SOURCE_DIGEST")

    def test_no_external_certification_from_self_authored_table(self):
        m = example()
        m["claim_external_independent_certification"] = True
        self.assertEqual(certificate(m)["external_system_correspondence"], "NOT_VERIFIED")

    def test_non_boolean_transition_index_rejected(self):
        m = example()
        m["concrete"]["transitions"][0][0] = True
        self.rejects(m, "CLOSURE")

    def test_full_observation_commutes_for_every_short_word(self):
        from itertools import product
        m = example()
        certificate(m)
        for state in range(len(m["concrete"]["states"])):
            for depth in range(5):
                for word in product(range(2), repeat=depth):
                    concrete_state = state
                    abstract_state = m["abstraction"][state]
                    for action in word:
                        concrete_state = m["concrete"]["transitions"][concrete_state][action]
                        abstract_state = m["abstract"]["transitions"][abstract_state][action]
                    self.assertEqual(m["abstraction"][concrete_state], abstract_state)
                    self.assertEqual(m["concrete"]["outputs"][concrete_state],
                                     m["abstract"]["outputs"][abstract_state])

    def test_counterexample_word_on_concrete_states(self):
        m = example()
        word = witness(m, 0, 2)
        self.assertEqual(word, (0,))
        def run(start):
            pos = start
            for act in word:
                pos = m["concrete"]["transitions"][pos][act]
            return m["concrete"]["outputs"][pos]
        self.assertNotEqual(run(0), run(2))


if __name__ == "__main__":
    unittest.main()
