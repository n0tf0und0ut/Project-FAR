"""Routing contract regression tests; these do not test LLM output or theology."""
import json
import unittest
from mechanization.far_mechanization.worldview_profiles import PROFILE_ID, DOMAINS, route_question


class WorldviewProfileTests(unittest.TestCase):
    def test_moral_uses_orthodox_norms_without_default_explicit_basis(self):
        route = route_question("moral")
        self.assertEqual(route.framework_id, PROFILE_ID)
        self.assertEqual(route.presentation, "ordinary")
        self.assertIn("without unsolicited Scripture citations", route.internal_guidance)
        self.assertIn("not empirically", route.audit_record()["normative_truth_assurance"].lower().replace("_", " "))
        self.assertTrue(route.audit_record()["provenance"])

    def test_explicit_theological_question_exposes_sources(self):
        route = route_question("religious")
        self.assertEqual(route.presentation, "religious")
        self.assertIn("Holy Tradition", route.internal_guidance)
        self.assertIn("Cite verifiable", route.internal_guidance)

    def test_question_domains_do_not_force_normative_profile(self):
        for domain in ("factual", "technical", "philosophical", "unknown"):
            with self.subTest(domain=domain):
                route = route_question(domain)
                self.assertIsNone(route.framework_id)
                self.assertEqual(route.presentation, "neutral")
                self.assertEqual(route.provenance, ())
                self.assertNotIn("Eastern Orthodox", route.internal_guidance)

    def test_mixed_only_targets_normative_component(self):
        route = route_question("mixed")
        self.assertEqual(route.framework_id, PROFILE_ID)
        self.assertIn("Keep empirical and normative subanswers separately justified", route.internal_guidance)

    def test_on_request_audit_disclosure(self):
        route = route_question("moral", explain_basis=True)
        self.assertEqual(route.presentation, "explicit_basis")
        self.assertIn("The active normative perspective is Eastern Orthodox", route.internal_guidance)
        self.assertEqual(route.audit_record()["framework_id"], PROFILE_ID)
        json.dumps(route.audit_record())

    def test_explicit_other_framework_is_respected(self):
        route = route_question("moral", another_framework_requested=True)
        self.assertIsNone(route.framework_id)
        self.assertEqual(route.presentation, "neutral")
        self.assertIn("Respect the user's explicitly specified framework", route.internal_guidance)

    def test_invalid_classification_or_flags_fail_closed(self):
        for domain in (None, "", "ethics", "Moral", {}, 3):
            with self.subTest(domain=domain), self.assertRaises(ValueError):
                route_question(domain)
        with self.assertRaises(ValueError):
            route_question("moral", explain_basis="yes")
        with self.assertRaises(ValueError):
            route_question("moral", another_framework_requested=1)

    def test_all_registered_domains_have_inspectable_provenance(self):
        for domain in DOMAINS:
            with self.subTest(domain=domain):
                record = route_question(domain).audit_record()
                self.assertEqual(record["question_domain"], domain)
                self.assertEqual(record["classification_assurance"], "UNVERIFIED_CALLER_SUPPLIED_DOMAIN")
                self.assertFalse(record["generated_answer_verified"])


if __name__ == "__main__":
    unittest.main()
