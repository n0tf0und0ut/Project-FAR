"""UQ-T33 source-bound evidence: adversarial checking and real-source integration."""
from __future__ import annotations

import ast
from itertools import product
from pathlib import Path
import tempfile
import unittest

from research.uq_t33_effective_quotients import source_bound_status as m

ROOT = Path(__file__).resolve().parents[1]


def fake_source() -> bytes:
    # Synthetic test source only. Strictly weaker than verification of real file.
    statements = ast.unparse(ast.Module(body=m._expected_resolver(), type_ignores=[]))
    return ("def adjudicate(package, findings, semantic_audits):\n" +
            "    " + statements.replace("\n", "\n    ") + "\n").encode("utf-8")


class SourceBoundCorrespondenceTests(unittest.TestCase):
    def test_source_identity_is_immutable_not_claimant_supplied(self):
        with self.assertRaises(m.SourceCorrespondenceError) as cm:
            m.inspect_source(fake_source())
        self.assertEqual(cm.exception.code, "SOURCE_BLOB_MISMATCH")

    def test_shape_accepts_expected_production_fragment(self):
        r = m._check_fragment(fake_source())
        self.assertEqual(r["matched_ast_statements"], 5)

    def test_status_precedence_not_just_cardinality(self):
        expected = {
            (False, False, False): "JUSTIFIED",
            (False, False, True): "UNVERIFIABLE",
            (False, True, False): "UNDERDETERMINED",
            (False, True, True): "UNDERDETERMINED",
            (True, False, False): "UNSUPPORTED",
            (True, False, True): "UNSUPPORTED",
            (True, True, False): "UNSUPPORTED",
            (True, True, True): "UNSUPPORTED",
        }
        self.assertEqual({b: m.status_of_flags(b) for b in product((False, True), repeat=3)}, expected)

    def test_nonparticipating_unknown_rules_do_not_change_classes(self):
        for rules in (frozenset(), frozenset(("arbitrary-unseen-rule",)),
                      frozenset(("semantic-contract-invalid",)),
                      frozenset(("evidence-contradicted",))):
            self.assertEqual(m.alpha(rules), m.alpha(rules | {"completely-unrecognized-rule"}))

    def test_all_supported_rule_subsets_commute_under_additions(self):
        vocab = tuple(sorted(m.UNSUPPORTED | m.UNVERIFIABLE | {m.ALTERNATIVE, "other-rule"}))
        for mask in range(1 << len(vocab)):
            rules = frozenset(rule for bit, rule in enumerate(vocab) if mask & (1 << bit))
            flags = m.alpha(rules)
            for rule in vocab:
                self.assertEqual(m.alpha(m.add_rule(rules, rule)), m.abstract_add(flags, rule))

    def test_recomputed_source_digest_cannot_authorize_modified_code(self):
        variant = fake_source().replace(b"IntegrityStatus.UNSUPPORTED", b"IntegrityStatus.JUSTIFIED")
        # A claimant might recompute a new content hash. The shape check still rejects it.
        self.assertEqual(m.git_blob_sha(variant), m.git_blob_sha(variant))
        with self.assertRaises(m.SourceCorrespondenceError) as cm:
            m._check_fragment(variant)
        self.assertEqual(cm.exception.code, "SOURCE_SEMANTICS_DRIFT")

    def test_additional_early_status_override_rejected(self):
        src = fake_source().replace(b"    return Adjudication", b"    status = 'override'\n    return Adjudication")
        with self.assertRaises(m.SourceCorrespondenceError) as cm:
            m._check_fragment(src)
        self.assertEqual(cm.exception.code, "SOURCE_SEMANTICS_DRIFT")

    def test_priority_change_rejected(self):
        src = fake_source().replace(b"if rule_ids & unsupported:", b"if rule_ids & unverifiable:")
        with self.assertRaises(m.SourceCorrespondenceError) as cm:
            m._check_fragment(src)
        self.assertEqual(cm.exception.code, "SOURCE_SEMANTICS_DRIFT")

    def test_missing_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as p:
            with self.assertRaises(m.SourceCorrespondenceError) as cm:
                m.certify_source(Path(p))
        self.assertEqual(cm.exception.code, "SOURCE_UNAVAILABLE")

    def test_actual_production_blob_and_certificate(self):
        path = ROOT / m.SOURCE_REL
        self.assertTrue(path.is_file(), "real production source is required; no skipped correspondence tests")
        report = m.certify_source(ROOT)
        self.assertEqual(report["source_git_blob"], m.SOURCE_GIT_BLOB)
        self.assertEqual(report["abstraction_states"], 8)
        self.assertEqual(report["finite_wrapper_transition_obligations"], 32)
        self.assertEqual(report["whole_program_correspondence"], "NOT_VERIFIED")
        self.assertEqual(report["independent_external_replication"], "NOT_OBTAINED")

    def test_live_adjudicate_all_eight_priority_cases(self):
        import sys
        root = ROOT / "commercial/far-decision-integrity/src"
        self.assertTrue(root.is_dir(), "real production package is required; no skipped runtime tests")
        sys.path.insert(0, str(root))
        from far_decision_integrity.adjudicate import adjudicate
        from far_decision_integrity.model import (
            DecisionPackage, DecisionNode, SCHEMA_VERSION
        )
        for u, a, v in product((False, True), repeat=3):
            # Real adjudicator generates 3 different types of finding.
            package = DecisionPackage(
                schema_version=SCHEMA_VERSION,
                decision_id="uq-t33-evidence", decision_type="validation",
                policy_version="test", decision_root="root", proposed_action={},
                nodes=(DecisionNode("root", "claim", "sample"),), dependencies=(),
                authorization_requirements=("root",) if u else (),
                unknowns=("unknown",) if v else (), trace_completeness=1.0,
                metadata={"material_alternatives": ["a", "b"]} if a else {},
            )
            actual = adjudicate(package)
            self.assertEqual(actual.status.name, m.status_of_flags((u, a, v)))
            self.assertEqual(m.alpha(x.rule_id for x in actual.findings), (u, a, v))


if __name__ == "__main__":
    unittest.main()
