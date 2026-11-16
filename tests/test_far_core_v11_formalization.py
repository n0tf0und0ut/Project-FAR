from __future__ import annotations

import unittest

from tools import check_far_core_v11_formalization as checker


class FARCoreV11FormalizationTests(unittest.TestCase):
    def test_machine_ledger_and_lean_sources_align(self):
        generated, _report, errors = checker.expected()
        self.assertEqual(errors, [])
        self.assertEqual(generated["w2_summary"]["formalized"], 14)
        self.assertEqual(generated["w2_summary"]["partial_obstruction"], 0)
        self.assertEqual(generated["w2_summary"]["contradiction_reopen_required"], 0)

    def test_far_core_008_encodes_count_noninvariance(self):
        ledger = checker.load(checker.LEDGER_PATH)
        assurance = checker.load(checker.ASSURANCE_PATH)
        claim = next(item for item in ledger["claims"] if item["id"] == "FAR-CORE-008")
        assurance_claim = next(item for item in assurance["claims"] if item["id"] == "FAR-CORE-008")
        declaration = "FARCoreV11.finite_operator_count_noninvariant"
        self.assertIn(declaration, claim["lean_declarations"])
        self.assertIn(declaration, assurance_claim["lean_declarations"])
        self.assertIn(declaration, checker.EXPECTED_DECLARATION_AXIOMS)

    def test_far_core_014_is_end_to_end_formalized_without_provenance_rewrite(self):
        ledger = checker.load(checker.LEDGER_PATH)
        assurance = checker.load(checker.ASSURANCE_PATH)
        claim = next(item for item in ledger["claims"] if item["id"] == "FAR-CORE-014")
        assurance_claim = next(item for item in assurance["claims"] if item["id"] == "FAR-CORE-014")
        self.assertEqual(claim["formalization_status"], "FORMALIZED")
        self.assertEqual(claim["obstruction"]["classification"], "none")
        self.assertIn("FARCoreV11.SSS.MLL.sOr_witness_certified", claim["lean_declarations"])
        self.assertIn("FARCoreV11.SSS.MLL.sAnd_witness_certified", claim["lean_declarations"])
        self.assertIn("FARCoreV11.SSS.MLL.bounded_projected_decoder_failure", claim["lean_declarations"])
        self.assertEqual(assurance_claim["truth_disposition"], "PROVED")
        self.assertEqual(assurance_claim["formalization_status"], "FORMALIZED")

    def test_no_w2_axiom_or_placeholder(self):
        generated, _report, _errors = checker.expected()
        self.assertEqual(generated["w2_summary"]["forbidden_placeholders"], 0)

    @staticmethod
    def _valid_axiom_output():
        lines = []
        for declaration, axioms in sorted(checker.EXPECTED_DECLARATION_AXIOMS.items()):
            if axioms:
                lines.append(f"'{declaration}' depends on axioms: [{', '.join(sorted(axioms))}]")
            else:
                lines.append(f"'{declaration}' does not depend on any axioms")
        return "\n".join(lines) + "\n"

    def test_axiom_audit_source_is_generated_and_rejects_output_forgery(self):
        source = checker.render_axiom_audit()
        self.assertEqual(checker.axiom_audit_source_errors(source), [])
        target = "#print axioms FARCoreV11.collision_refutes_sufficiency"
        forged = source.replace(target, f"-- {target}\n#eval IO.println \"fabricated\"")
        self.assertTrue(checker.axiom_audit_source_errors(forged))

    def test_runtime_axiom_output_matches_every_declaration(self):
        ledger = checker.load(checker.LEDGER_PATH)
        self.assertEqual(checker.axiom_output_errors(self._valid_axiom_output(), ledger), [])

    def test_hidden_transitive_axiom_and_constant_are_rejected(self):
        ledger = checker.load(checker.LEDGER_PATH)
        target = "FARCoreV11.collision_refutes_sufficiency"
        original = f"'{target}' does not depend on any axioms"
        hidden = f"'{target}' depends on axioms: [Hidden.secret]"
        errors = checker.axiom_output_errors(self._valid_axiom_output().replace(original, hidden), ledger)
        self.assertTrue(any("actual axiom set" in error and "Hidden.secret" in error for error in errors))
        self.assertIsNotNone(checker.FORBIDDEN.search("constant hidden : False\n"))


    def test_proposition_lock_covers_all_governed_declarations(self):
        ledger = checker.load(checker.LEDGER_PATH)
        lock = checker.load(checker.STATEMENT_LOCK_PATH)
        self.assertEqual(checker.statement_lock_errors(ledger, lock), [])
        self.assertEqual(len(lock["signatures"]), 40)

    def test_proposition_lock_rejects_trivial_theorem_replacement(self):
        ledger = checker.load(checker.LEDGER_PATH)
        lock = checker.load(checker.STATEMENT_LOCK_PATH)
        target = "FARCoreV11.finite_panel_two_completions"
        path = lock["signatures"][target]["module"]
        source = (checker.ROOT / path).read_text(encoding="utf-8")
        import re
        mutated, count = re.subn(
            r"(?ms)^[ \t]*theorem finite_panel_two_completions\b.*?(?=:= by)",
            "theorem finite_panel_two_completions : True ",
            source, count=1,
        )
        self.assertEqual(count, 1)
        errors = checker.statement_lock_errors(ledger, lock, {path: mutated})
        self.assertTrue(
            any(target in error and "proposition signature drift" in error for error in errors),
            errors,
        )

    def test_proposition_lock_rejects_duplicate_declaration(self):
        ledger = checker.load(checker.LEDGER_PATH)
        lock = checker.load(checker.STATEMENT_LOCK_PATH)
        target = "FARCoreV11.finite_panel_two_completions"
        path = lock["signatures"][target]["module"]
        source = (checker.ROOT / path).read_text(encoding="utf-8")
        duplicated = source + "\ntheorem finite_panel_two_completions : True := by trivial\n"
        errors = checker.statement_lock_errors(ledger, lock, {path: duplicated})
        self.assertTrue(any(target in error and "duplicated" in error for error in errors), errors)

    def test_proposition_lock_ignores_proof_body_comments(self):
        ledger = checker.load(checker.LEDGER_PATH)
        lock = checker.load(checker.STATEMENT_LOCK_PATH)
        path = "mechanization/lean/FARCoreV11Claims001To012.lean"
        source = (checker.ROOT / path).read_text(encoding="utf-8")
        self.assertIn("  refine ⟨fun _ => True,", source)
        changed = source.replace(
            "  refine ⟨fun _ => True,",
            "  -- Statement-level lock does not freeze proof implementation.\n  refine ⟨fun _ => True,",
            1,
        )
        self.assertEqual(checker.statement_lock_errors(ledger, lock, {path: changed}), [])


    def test_generated_views_are_current(self):
        self.assertEqual(checker.main([]), 0)


if __name__ == "__main__":
    unittest.main()
