"""Finite FAR-CORE-001/004/011 witnesses for the Orthodox worldview profile.

These are synthetic stipulated behavior tables, *not* empirical comparisons of
religious traditions, proofs of moral truth, or new universal theorems.
Run against the current governed far-ir/2.0 verifier, not an ad hoc checker.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from mechanization.far_mechanization.contract_v2_strict_v11 import (
    contract_sha256,
    validate_contract,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "conformance" / "far-ir-2.0"

CASE_IDS = ("case.orthodox", "case.alternative")
OBSERVATION = {"observed_action": "same-stipulated-action"}
PROFILES = ("eastern-orthodox/0.1", "nonconfessional-analytical")
# These distinct *illustrative required outputs* are not a moral verdict.
OUTPUTS = ("RESTRICTED_BY_DECLARED_FRAME", "UNDETERMINED_BY_DECLARED_FRAME")


def base(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def configure(document: dict, *, keep_profile: bool, normative: bool) -> dict:
    """Construct two cases sharing observations but carrying different profiles."""
    doc = copy.deepcopy(document)
    contract = doc["contract"]
    contract["source_domain"]["cases"] = [
        {"id": case, "value": {"observation": OBSERVATION, "framework": profile}}
        for case, profile in zip(CASE_IDS, PROFILES)
    ]
    values = OUTPUTS if normative else ("SAME_OBSERVED_EVENT", "SAME_OBSERVED_EVENT")
    contract["required_behavior"]["table"] = [
        {"case_id": case, "value": value}
        for case, value in zip(CASE_IDS, values)
    ]
    representations = (
        [{"observation": OBSERVATION, "framework": profile} for profile in PROFILES]
        if keep_profile else
        [{"observation": OBSERVATION} for _ in CASE_IDS]
    )
    contract["representation"]["table"] = [
        {"case_id": case, "value": value}
        for case, value in zip(CASE_IDS, representations)
    ]
    contract["interpretation_profile"] = {
        "id": "worldview.contract.profile-family",
        "description": "Finite explicit comparison of two declared normative interpretation profiles",
        "status": "EXPLICIT",
    }
    contract["target_model_class"]["description"] = "Exactly these two synthetic cases"
    doc["freeze"]["contract_sha256"] = contract_sha256(contract)
    return doc


def factored(*, keep_profile: bool, normative: bool) -> dict:
    doc = configure(base("valid-factorization.json"),
                    keep_profile=keep_profile, normative=normative)
    contract = doc["contract"]
    output = {
        row["case_id"]: row["value"] for row in contract["required_behavior"]["table"]
    }
    pairs = []
    seen = set()
    for row in contract["representation"]["table"]:
        value = row["value"]
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        pairs.append({"representation_value": value, "behavior_value": output[row["case_id"]]})
    doc["report"]["evidence"]["decoder_table"] = pairs
    return doc


class WorldviewFactorizationTests(unittest.TestCase):
    def test_normative_profile_omission_is_checked_collision(self):
        witness = configure(base("valid-collision.json"),
                            keep_profile=False, normative=True)
        result = validate_contract(witness)
        self.assertTrue(result.success, [(d.code, d.message) for d in result.diagnostics])
        self.assertEqual(witness["report"]["outcome"], "REFUTED")
        self.assertEqual(len({json.dumps(row["value"], sort_keys=True)
                              for row in witness["contract"]["representation"]["table"]}), 1)
        self.assertEqual(len({row["value"] for row in
                              witness["contract"]["required_behavior"]["table"]}), 2)

    def test_explicit_profile_repairs_factorization(self):
        witness = factored(keep_profile=True, normative=True)
        result = validate_contract(witness)
        self.assertTrue(result.success, [(d.code, d.message) for d in result.diagnostics])
        self.assertEqual(witness["report"]["outcome"], "PROVED")
        self.assertEqual(len(witness["report"]["evidence"]["decoder_table"]), 2)

    def test_empirical_only_behavior_needs_no_profile(self):
        witness = factored(keep_profile=False, normative=False)
        result = validate_contract(witness)
        self.assertTrue(result.success, [(d.code, d.message) for d in result.diagnostics])
        self.assertEqual(witness["report"]["outcome"], "PROVED")
        self.assertEqual(len(witness["report"]["evidence"]["decoder_table"]), 1)

    def test_mutating_moral_behavior_without_resealing_fails(self):
        witness = factored(keep_profile=True, normative=True)
        witness["contract"]["required_behavior"]["table"][0]["value"] = "TAMPERED"
        result = validate_contract(witness)
        self.assertFalse(result.success)
        self.assertIn("FREEZE_HASH_MISMATCH", [d.code for d in result.diagnostics])

    def test_declared_difference_is_not_theological_evidence(self):
        """Protect against rebranding the stipulated fixture as a doctrinal test."""
        witness = configure(base("valid-collision.json"),
                            keep_profile=False, normative=True)
        self.assertFalse(witness["provenance"]["sources"])
        self.assertTrue(all("framework" in x["value"] for x in
                            witness["contract"]["source_domain"]["cases"]))
        self.assertNotIn("empirical", witness["contract"]["required_behavior"]["description"].lower())


if __name__ == "__main__":
    unittest.main()
