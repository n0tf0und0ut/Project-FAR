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

    def test_dependent_let_conclusion_is_locked(self):
        ledger = checker.load(checker.LEDGER_PATH)
        lock = checker.load(checker.STATEMENT_LOCK_PATH)
        target = "FARCoreV11.finite_operator_count_noninvariant"
        path = lock["signatures"][target]["module"]
        source = (checker.ROOT / path).read_text(encoding="utf-8")
        exact_conclusion = "splitTwoOperatorVocabulary ≠ combinedDispatcherVocabulary"
        self.assertIn(exact_conclusion, lock["signatures"][target]["header"])
        self.assertEqual(source.count(exact_conclusion), 1)
        mutated = source.replace(exact_conclusion, "True", 1)
        errors = checker.statement_lock_errors(ledger, lock, {path: mutated})
        self.assertTrue(any(target in error and "signature drift" in error for error in errors), errors)

    def test_where_defined_value_locks_type_not_fields(self):
        ledger = checker.load(checker.LEDGER_PATH)
        lock = checker.load(checker.STATEMENT_LOCK_PATH)
        target = "FARCoreV11.embeddingRangeEquiv"
        path = lock["signatures"][target]["module"]
        source = (checker.ROOT / path).read_text(encoding="utf-8")
        self.assertNotIn("where toFun", lock["signatures"][target]["header"])
        changed = source.replace(
            "  toFun := imageValue encoding",
            "  -- An implementation-only comment after the type.\n  toFun := imageValue encoding",
            1,
        )
        self.assertNotEqual(changed, source)
        self.assertEqual(checker.statement_lock_errors(ledger, lock, {path: changed}), [])

    def test_qualified_lock_rejects_decoy_namespace_and_quoted_true(self):
        ledger = checker.load(checker.LEDGER_PATH)
        lock = checker.load(checker.STATEMENT_LOCK_PATH)
        target = "FARCoreV11.finite_panel_two_completions"
        path = lock["signatures"][target]["module"]
        source = (checker.ROOT / path).read_text(encoding="utf-8")
        start = source.index("theorem finite_panel_two_completions")
        stop = source.index("/-! ## FAR-CORE-010 -/", start)
        original = source[start:stop]
        mutated = (
            source[:start]
            + "namespace Decoy\\n"
            + original
            + "end Decoy\\n"
            + "theorem «finite_panel_two_completions» : True := by trivial\\n\\n"
            + source[stop:]
        )
        mutated = mutated.replace("\\n", "\n")
        errors = checker.statement_lock_errors(ledger, lock, {path: mutated})
        self.assertTrue(
            any(target in error and (
                "signature drift" in error or "absent, duplicated, or malformed" in error
            ) for error in errors),
            errors,
        )

    def test_line_broken_namespace_and_theorem_decoy_is_rejected(self):
        """Reproduce the Codex review: Lean permits split scope/declaration commands."""
        ledger = checker.load(checker.LEDGER_PATH)
        lock = checker.load(checker.STATEMENT_LOCK_PATH)
        target = "FARCoreV11.finite_panel_two_completions"
        path = lock["signatures"][target]["module"]
        source = (checker.ROOT / path).read_text(encoding="utf-8")
        start = source.index("theorem finite_panel_two_completions")
        stop = source.index("/-! ## FAR-CORE-010 -/", start)
        original = source[start:stop]
        mutated = (
            source[:start]
            + "namespace\\n  Decoy\\n".replace("\\n", "\n")
            + original
            + "end\\n".replace("\\n", "\n")
            + "theorem\\n  «finite_panel_two_completions» : True := by trivial\\n\\n".replace("\\n", "\n")
            + source[stop:]
        )
        errors = checker.statement_lock_errors(ledger, lock, {path: mutated})
        self.assertTrue(
            any(target in error and (
                "absent, duplicated, or malformed" in error or "signature drift" in error
            ) for error in errors),
            errors,
        )

    def test_unsupported_bare_lean_commands_fail_closed(self):
        """Do not overlook namespace/end/declaration keywords split over lines."""
        qualified = "FARCoreV11.exact_factorization_criterion"
        source = (checker.ROOT / "mechanization/lean/FARCoreV11Substrate.lean").read_text(encoding="utf-8")
        marker = "namespace FARCoreV11"
        self.assertIn(marker, source)
        for swapped in ("namespace\n  FARCoreV11", "namespace\n -- comment\n FARCoreV11"):
            with self.subTest(swapped=swapped):
                self.assertIsNone(checker.statement_header(source.replace(marker, swapped, 1), qualified))
        self.assertIsNone(checker.statement_header(
            source.replace("end FARCoreV11", "end\n", 1), qualified,
        ))
        self.assertIsNone(checker.statement_header(
            source.replace(
                "theorem exact_factorization_criterion",
                "theorem\n  exact_factorization_criterion",
                1,
            ), qualified,
        ))

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



    def test_proposition_lock_rejects_module_identity_substitution(self):
        import copy
        ledger = checker.load(checker.LEDGER_PATH)
        lock = copy.deepcopy(checker.load(checker.STATEMENT_LOCK_PATH))
        target = "FARCoreV11.finite_panel_two_completions"
        lock["signatures"][target]["module"] = "mechanization/lean/FARCoreV11Substrate.lean"
        errors = checker.statement_lock_errors(ledger, lock)
        self.assertTrue(
            any(target in error and "module mismatch" in error for error in errors), errors
        )

    def test_proposition_lock_is_enforced_at_alignment_entrypoint(self):
        from unittest import mock
        ledger = checker.load(checker.LEDGER_PATH)
        assurance = checker.load(checker.ASSURANCE_PATH)
        core = checker.load(checker.CORE_PATH)
        generated = checker.inventory(ledger)
        sentinel = "synthetic proposition lock enforcement failure"
        with mock.patch.object(checker, "statement_lock_errors", return_value=[sentinel]):
            errors = checker.alignment_errors(ledger, assurance, core, generated)
        self.assertIn(sentinel, errors)

    def test_generated_views_are_current(self):
        self.assertEqual(checker.main([]), 0)


if __name__ == "__main__":
    unittest.main()
