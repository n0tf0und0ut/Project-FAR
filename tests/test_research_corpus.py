from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from tools import reconcile_research_corpus as corpus


class ResearchCorpusTests(unittest.TestCase):
    def setUp(self):
        self.data = corpus.load_json(corpus.CORPUS)

    def derive(self, data=None):
        return corpus.derive(data or self.data)

    def observation(self, oid, proposition, relation="SUPPORTS", targets=None, target_kind="NONE", effect="NONE", mechanisms=None, scope="source_bounded", statement=None, dependencies=None):
        return {
            "id": oid, "proposition_id": proposition, "epistemic_class": "EVIDENCE",
            "statement": statement or f"bounded statement {oid}", "scope": "bounded test scope",
            "scope_key": scope, "relation": relation, "relation_targets": targets or [],
            "target_kind": target_kind, "replacement_effect": effect,
            "uncertainty": "test uncertainty remains", "mechanism_ids": mechanisms or ["MEC-CONTRACT"],
            "dependencies": dependencies or [], "history": [],
        }

    def source(self, sid, observations):
        return {
            "id": sid, "source_identity": sid, "path": "README.md",
            "sha256": hashlib.sha256((corpus.ROOT / "README.md").read_bytes()).hexdigest(),
            "version": "test-v1", "external_identifier": f"test:{sid}", "evidence_class": "test",
            "kind": "repository_artifact", "current_availability": "available",
            "historical_availability": "PRESENT", "evidence_usable": True, "material": True,
            "scope": "bounded test scope", "history": [], "supersedes": [], "corrects": [],
            "observations": observations, "review_status": "GOVERNED_REPOSITORY_SOURCE",
            "primary_evidence_verified": True,
        }

    def with_relation_fixture(self, *observations):
        data = copy.deepcopy(self.data)
        # Isolate MEC-CONTRACT so the fixture determines its state.
        for source in data["sources"]:
            for observation in source["observations"]:
                observation["mechanism_ids"] = [m for m in observation["mechanism_ids"] if m != "MEC-CONTRACT"]
        data["sources"].append(self.source("SRC-TEST-RELATION", list(observations)))
        return data

    def mechanism(self, result, mechanism_id="MEC-CONTRACT"):
        return next(row for row in result["mechanisms"] if row["id"] == mechanism_id)

    def test_jsonschema_dependency_is_declared_for_workflow_and_package(self):
        requirements = (corpus.ROOT / "requirements.txt").read_text()
        package = (corpus.ROOT / "pyproject.toml").read_text()
        self.assertIn("jsonschema>=4.22,<5", requirements)
        self.assertIn('"jsonschema>=4.22,<5"', package)

    def test_real_outputs_are_reproducible_and_counts_are_manifest_derived(self):
        self.assertEqual(corpus.validate(self.data), [])
        result = self.derive()
        expected_manifest_count = corpus.load_json(Path("research/corpus/snapshots/pr-490-manifest-v1.0.json"))["candidate_count"]
        current_ids = {path.stem for path in (corpus.ROOT / "research/living/inbox/candidates").glob("FAR-LIT-*.json")}
        manifest_ids = {Path(item["path"]).stem for item in corpus.load_json(Path("research/corpus/snapshots/pr-490-manifest-v1.0.json"))["candidate_blobs"]}
        external_ids = {path.stem for path in (corpus.ROOT / "research/corpus/external").glob("*.json")}
        self.assertEqual(result["untrusted_lead_count"], len(manifest_ids | current_ids | external_ids))
        self.assertEqual(expected_manifest_count, len(manifest_ids))
        outputs = corpus.expected_outputs(self.data)
        self.assertEqual((corpus.ROOT / corpus.OUTPUT).read_bytes(), outputs[corpus.OUTPUT])
        self.assertEqual((corpus.ROOT / corpus.STATUS).read_bytes(), outputs[corpus.STATUS])
        # This binds the derived schema identity to the exact governed schema bytes.
        self.assertEqual(result["generator_sha256"], corpus.digest(Path(corpus.__file__).read_bytes()))
        self.assertEqual(result["schema_sha256"], corpus.digest((corpus.ROOT / corpus.SCHEMA).read_bytes()))

    def test_mutable_living_state_is_dynamic_invalidation_input_not_evidence(self):
        declaration = self.data["dynamic_dependencies"][0]
        self.assertEqual(declaration["path"], "research/living/repository-state-v1.0.json")
        self.assertNotIn("sha256", declaration)
        self.assertFalse(any(source["path"] == declaration["path"] for source in self.data["sources"]))
        original = self.derive()
        changed = copy.deepcopy(original["dynamic_dependencies"])
        changed[0]["sha256"] = "0" * 64
        with mock.patch.object(corpus, "dynamic_dependencies", return_value=changed):
            recomputed = self.derive()
        self.assertNotEqual(original["dynamic_dependencies_sha256"], recomputed["dynamic_dependencies_sha256"])
        self.assertNotEqual(original["synthesis_input_sha256"], recomputed["synthesis_input_sha256"])
        self.assertFalse(original["dynamic_dependencies"][0]["evidence_usable"])

    def test_dynamic_dependency_identity_and_format_fail_closed(self):
        duplicate = copy.deepcopy(self.data)
        duplicate["dynamic_dependencies"].append(copy.deepcopy(duplicate["dynamic_dependencies"][0]))
        self.assertTrue(any("duplicate identity" in error for error in corpus.validate(duplicate)))
        bad_format = copy.deepcopy(self.data)
        bad_format["dynamic_dependencies"][0]["format_value"] = "impossible-version"
        self.assertTrue(any("dynamic dependency format mismatch" in error for error in corpus.validate(bad_format)))

    def test_completeness_dimensions_are_bounded_and_distinct(self):
        completeness = self.derive()["completeness"]
        self.assertEqual(set(completeness), {"inventory", "evidence", "search", "synthesis", "global_open_world"})
        self.assertIn("RELATIVE", completeness["inventory"]["status"])
        self.assertEqual(completeness["search"]["status"], "BOUNDED_NOT_GLOBAL")
        self.assertEqual(completeness["global_open_world"]["status"], "UNESTABLISHED")
        self.assertNotEqual(completeness["inventory"]["status"], completeness["evidence"]["status"])

    def test_supports_is_the_only_unconditional_positive_relation(self):
        support = self.observation("OBS-TEST-SUPPORT", "FND-TEST")
        for relation in ("QUALIFIES", "UNRESOLVED", "CONTRADICTS"):
            marker = self.observation(f"OBS-TEST-{relation}", "FND-MARKER", relation, ["FND-TEST"], "PROPOSITION")
            result = self.derive(self.with_relation_fixture(support, marker))
            state = self.mechanism(result)["state"]
            self.assertEqual(state, {"QUALIFIES": "QUALIFIED", "UNRESOLVED": "UNRESOLVED", "CONTRADICTS": "CONTRADICTED"}[relation])
            finding = next(row for row in result["normalized_findings"] if row["id"] == "FND-TEST")
            if relation == "QUALIFIES": self.assertEqual(finding["qualification_details"][0]["statement"], marker["statement"])
        correction = self.observation("OBS-TEST-CORRECT", "FND-REPLACEMENT", "CORRECTS", ["OBS-TEST-SUPPORT"], "OBSERVATION", "INVALIDATE_ONLY", mechanisms=[])
        self.assertEqual(self.mechanism(self.derive(self.with_relation_fixture(support, correction)))["state"], "NO_ACTIVE_SUPPORT")

    def test_correction_replaces_support_and_keeps_old_finding_historical(self):
        original = self.observation("OBS-TEST-A", "FND-TEST", statement="old statement")
        correction = self.observation("OBS-TEST-B", "FND-TEST", "CORRECTS", ["OBS-TEST-A"], "OBSERVATION", "REPLACE_EQUIVALENT", statement="corrected statement")
        result = self.derive(self.with_relation_fixture(original, correction))
        finding = next(row for row in result["normalized_findings"] if row["id"] == "FND-TEST")
        self.assertEqual(finding["state"], "SUPPORTED")
        self.assertEqual(finding["active_support_observation_ids"], ["OBS-TEST-B"])
        self.assertIn("OBS-TEST-A", finding["historical_inactive_observation_ids"])

    def test_hypothesis_support_cannot_satisfy_inference_conclusion(self):
        observation = self.observation("OBS-TEST-H", "FND-TEST")
        observation["epistemic_class"] = "HYPOTHESIS"
        result = self.derive(self.with_relation_fixture(observation))
        stability = next(row for row in result["conclusions"] if row["id"] == "CON-STABILITY")
        self.assertEqual(stability["epistemic_class"], "UNRESOLVED")
        self.assertEqual(stability["blocked_mechanisms"]["MEC-CONTRACT"], "EPISTEMIC_CEILING")

    def test_mechanism_epistemic_classes_are_observation_specific(self):
        evidence = self.observation("OBS-TEST-E", "FND-TEST", mechanisms=["MEC-CONTRACT"])
        hypothesis = self.observation("OBS-TEST-H", "FND-TEST", mechanisms=["MEC-RECONCILIATION"])
        hypothesis["epistemic_class"] = "HYPOTHESIS"
        data = self.with_relation_fixture(evidence, hypothesis)
        # Keep the proposition semantically identical so finding-level support is not ambiguous.
        hypothesis["statement"] = evidence["statement"]
        result = self.derive(data)
        contract = self.mechanism(result, "MEC-CONTRACT")
        reconciliation = self.mechanism(result, "MEC-RECONCILIATION")
        self.assertIn({"scope_key": "source_bounded", "epistemic_class": "EVIDENCE"}, contract["support_scope_epistemic_classes"])
        self.assertNotIn({"scope_key": "source_bounded", "epistemic_class": "EVIDENCE"}, reconciliation["support_scope_epistemic_classes"])

    def test_conclusion_dependency_cannot_raise_epistemic_class(self):
        data = copy.deepcopy(self.data)
        parent = next(rule for rule in data["conclusion_rules"] if rule["id"] == "CON-COMPOUNDING")
        child = next(rule for rule in data["conclusion_rules"] if rule["id"] == "CON-STABILITY")
        parent["result_class"] = "HYPOTHESIS"
        child["depends_on_conclusions"] = [parent["id"]]
        result = self.derive(data)
        stability = next(row for row in result["conclusions"] if row["id"] == "CON-STABILITY")
        self.assertEqual(stability["epistemic_class"], "UNRESOLVED")
        self.assertEqual(stability["dependency_blocks"][parent["id"]], "EPISTEMIC_CEILING")

    def test_transitive_dependency_inactivity_reaches_fixed_point(self):
        a = self.observation("OBS-TEST-A", "FND-A")
        b = self.observation("OBS-TEST-B", "FND-B", dependencies=["OBS-TEST-A"])
        c = self.observation("OBS-TEST-C", "FND-C", dependencies=["OBS-TEST-B"])
        data = self.with_relation_fixture(a, b, c)
        data["sources"][-1]["observations"] = [b, c]  # A exists only historically/unavailable.
        unavailable = self.source("SRC-TEST-OLD", [a])
        unavailable["current_availability"] = "withdrawn"
        unavailable["historical_availability"] = "WITHDRAWN_RETAINED"
        unavailable["evidence_usable"] = False
        data["sources"].append(unavailable)
        result = self.derive(data)
        self.assertEqual(set(result["observation_state"]["dependency_inactive"]), {"OBS-TEST-B", "OBS-TEST-C"})

    def test_conclusion_dependency_hash_is_bound_to_evidence_content(self):
        original = self.derive()
        changed = copy.deepcopy(self.data)
        changed["sources"][0]["observations"][0]["statement"] += " changed evidence wording"
        recomputed = self.derive(changed)
        before = next(row for row in original["conclusions"] if row["id"] == "CON-STABILITY")
        after = next(row for row in recomputed["conclusions"] if row["id"] == "CON-STABILITY")
        self.assertNotEqual(before["dependency_sha256"], after["dependency_sha256"])

    def test_supersession_with_narrower_scope_does_not_satisfy_stronger_scope(self):
        original = self.observation("OBS-TEST-A", "FND-TEST")
        narrower = self.observation("OBS-TEST-B", "FND-TEST", "SUPERSEDES", ["OBS-TEST-A"], "OBSERVATION", "REPLACE_NARROWER", scope="narrow_test")
        data = self.with_relation_fixture(original, narrower)
        data["mechanism_catalog"][0]["accepted_scope_keys"].append("narrow_test")
        result = self.derive(data)
        self.assertEqual(self.mechanism(result)["state"], "SUPPORTED")
        stability = next(row for row in result["conclusions"] if row["id"] == "CON-STABILITY")
        self.assertEqual(stability["epistemic_class"], "UNRESOLVED")
        self.assertEqual(stability["blocked_mechanisms"]["MEC-CONTRACT"], "SCOPE_NOT_SUPPORTED")

    def test_withdrawn_correction_does_not_resurrect_retired_support(self):
        original = self.observation("OBS-TEST-A", "FND-TEST")
        correction = self.observation("OBS-TEST-B", "FND-TEST", "CORRECTS", ["OBS-TEST-A"], "OBSERVATION", "REPLACE_EQUIVALENT")
        data = self.with_relation_fixture(original, correction)
        # Put the correction in its own later governed source, then withdraw it.
        data["sources"][-1]["observations"] = [original]
        later = self.source("SRC-TEST-CORRECTION", [correction])
        later["current_availability"] = "withdrawn"; later["historical_availability"] = "WITHDRAWN_RETAINED"; later["evidence_usable"] = False
        data["sources"].append(later)
        result = self.derive(data)
        finding = next(row for row in result["normalized_findings"] if row["id"] == "FND-TEST")
        self.assertEqual(finding["state"], "NO_ACTIVE_SUPPORT")
        self.assertIn("OBS-TEST-A", finding["historical_inactive_observation_ids"])

    def test_correction_of_correction_transitively_retires_history(self):
        a = self.observation("OBS-TEST-A", "FND-TEST", statement="a")
        b = self.observation("OBS-TEST-B", "FND-TEST", "CORRECTS", ["OBS-TEST-A"], "OBSERVATION", "REPLACE_EQUIVALENT", statement="b")
        c = self.observation("OBS-TEST-C", "FND-TEST", "CORRECTS", ["OBS-TEST-B"], "OBSERVATION", "REPLACE_EQUIVALENT", statement="c")
        finding = next(row for row in self.derive(self.with_relation_fixture(a, b, c))["normalized_findings"] if row["id"] == "FND-TEST")
        self.assertEqual(finding["active_support_observation_ids"], ["OBS-TEST-C"])
        self.assertEqual(finding["historical_inactive_observation_ids"], ["OBS-TEST-A", "OBS-TEST-B"])

    def test_conflicting_active_sources_block_mechanism_and_conclusion(self):
        support = self.observation("OBS-TEST-A", "FND-TEST")
        contradiction = self.observation("OBS-TEST-B", "FND-CONTRA", "CONTRADICTS", ["FND-TEST"], "PROPOSITION")
        result = self.derive(self.with_relation_fixture(support, contradiction))
        self.assertEqual(self.mechanism(result)["state"], "CONTRADICTED")
        self.assertEqual(next(row for row in result["conclusions"] if row["id"] == "CON-STABILITY")["epistemic_class"], "UNRESOLVED")

    def test_ambiguous_active_support_is_fail_closed(self):
        a = self.observation("OBS-TEST-A", "FND-TEST", statement="claim a")
        b = self.observation("OBS-TEST-B", "FND-TEST", statement="claim b")
        result = self.derive(self.with_relation_fixture(a, b))
        self.assertEqual(next(row for row in result["normalized_findings"] if row["id"] == "FND-TEST")["state"], "AMBIGUOUS_ACTIVE_SUPPORT")
        self.assertEqual(self.mechanism(result)["state"], "AMBIGUOUS")

    def test_withdrawal_and_missing_evidence_are_not_negative_evidence(self):
        data = self.with_relation_fixture(self.observation("OBS-TEST-A", "FND-TEST"))
        data["sources"][-1]["current_availability"] = "withdrawn"
        data["sources"][-1]["historical_availability"] = "WITHDRAWN_RETAINED"
        data["sources"][-1]["evidence_usable"] = False
        result = self.derive(data)
        self.assertEqual(self.mechanism(result)["state"], "NO_ACTIVE_SUPPORT")
        self.assertNotEqual(self.mechanism(result)["state"], "CONTRADICTED")

    def test_source_supersession_is_operational_while_old_source_remains_present(self):
        data = self.with_relation_fixture(self.observation("OBS-TEST-A", "FND-TEST"))
        old_source = data["sources"][-1]
        newer = self.source("SRC-TEST-NEWER", [])
        newer["supersedes"] = [old_source["id"]]
        data["sources"].append(newer)
        result = self.derive(data)
        self.assertFalse(next(row for row in result["sources"] if row["id"] == old_source["id"])["active"])
        self.assertEqual(self.mechanism(result)["state"], "NO_ACTIVE_SUPPORT")

    def test_circular_history_and_dependencies_are_rejected(self):
        a = self.observation("OBS-TEST-A", "FND-A", "CORRECTS", ["OBS-TEST-B"], "OBSERVATION", "REPLACE_EQUIVALENT")
        b = self.observation("OBS-TEST-B", "FND-B", "SUPERSEDES", ["OBS-TEST-A"], "OBSERVATION", "REPLACE_EQUIVALENT")
        errors = corpus.validate(self.with_relation_fixture(a, b))
        self.assertTrue(any("circular observation correction/supersession" in error for error in errors))

        source_cycle = copy.deepcopy(self.data); source_cycle["sources"][0]["corrects"] = [source_cycle["sources"][1]["id"]]; source_cycle["sources"][1]["supersedes"] = [source_cycle["sources"][0]["id"]]
        self.assertTrue(any("circular source correction/supersession" in error for error in corpus.validate(source_cycle)))

    def test_conclusion_order_is_irrelevant_and_unresolved_propagates(self):
        expected = {row["id"]: row for row in self.derive()["conclusions"]}
        reordered = copy.deepcopy(self.data)
        reordered["conclusion_rules"].reverse()
        actual = {row["id"]: row for row in self.derive(reordered)["conclusions"]}
        self.assertEqual({key: value["epistemic_class"] for key, value in expected.items()}, {key: value["epistemic_class"] for key, value in actual.items()})
        data = self.with_relation_fixture(self.observation("OBS-TEST-U", "FND-U", "UNRESOLVED", ["FND-U"], "PROPOSITION"))
        result = self.derive(data)
        self.assertEqual(next(row for row in result["conclusions"] if row["id"] == "CON-INVESTIGATION-ASSURANCE")["epistemic_class"], "UNRESOLVED")

    def test_omitted_material_input_and_unproved_gap_fail(self):
        data = copy.deepcopy(self.data)
        data["sources"] = [source for source in data["sources"] if source.get("path") != "docs/audits/far-core-epistemic-calibration-v1.0.md"]
        self.assertTrue(any("unclassified material input" in error for error in corpus.validate(data)))
        gap = copy.deepcopy(self.data)
        gap["mechanism_catalog"][0]["architecture_class"] = "genuine_architecture_gap"
        self.assertTrue(any("unproved genuine architecture gap" in error for error in corpus.validate(gap)))

    def test_schema_parser_and_reference_hardening(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            corpus.strict_json_bytes(b'{"id":1,"id":2}', "hostile")
        invalid = copy.deepcopy(self.data)
        del invalid["sources"][0]["source_identity"]
        self.assertTrue(any(error.startswith("schema:") for error in corpus.validate(invalid)))
        invalid = copy.deepcopy(self.data)
        invalid["sources"][0]["observations"][0]["relation"] = "MAYBE"
        self.assertTrue(any(error.startswith("schema:") for error in corpus.validate(invalid)))
        invalid = copy.deepcopy(self.data)
        invalid["sources"][0]["sha256"] = "bad"
        self.assertTrue(any(error.startswith("schema:") for error in corpus.validate(invalid)))
        invalid = copy.deepcopy(self.data)
        invalid["sources"][0]["path"] = "../outside.md"
        self.assertTrue(any("unsafe path" in error for error in corpus.validate(invalid)))

    def test_unattended_workflow_executes_and_persists_reconciliation(self):
        workflow = (corpus.ROOT / ".github/workflows/living-research.yml").read_text()
        runner = (corpus.ROOT / "tools/run_living_research.py").read_text()
        self.assertIn("python tools/reconcile_research_corpus.py --living-loop --write", workflow)
        self.assertIn("research/corpus/external", workflow)
        self.assertIn("write_living(root)", runner)
        self.assertNotIn("research/living/corpus-reconciliation-v1.0.json \\", workflow)
        self.assertNotIn("research/living/repository-state-v1.0.json \\", workflow)
        self.assertIn("schemas/far-reviewed-input-v1.schema.json", workflow)
        self.assertIn("docs/audits/**", workflow)
        preflight = workflow.split("- name: Preflight tests and authority checks", 1)[1].split("- name: Discover current and historical research", 1)[0]
        self.assertLess(preflight.index("python tools/reconcile_research_corpus.py --living-loop --write"), preflight.index("python -m unittest"))

    def test_external_ingestion_is_routed_but_cannot_self_promote(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            incoming = root / "input"
            incoming.write_bytes(b"#!/bin/sh\nexit 99\n")
            corpus.freeze_external(incoming, "scheduled_task", root)
            receipt = json.loads(next((root / "research/corpus/external").glob("*.json")).read_text())
            living = json.loads((root / corpus.LIVING_RECONCILIATION).read_text())
            self.assertFalse(receipt["primary_evidence_verified"])
            self.assertFalse(receipt["executable"])
            self.assertFalse(living["promotion_authority"])
            self.assertEqual(living["review_bridge"], str(corpus.REVIEWED_INPUTS))
            self.assertFalse(living["candidates"][0]["evidence_usable"])

    def test_orphaned_external_blob_or_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "research/corpus/external"
            external.mkdir(parents=True)
            (external / ("a" * 64 + ".bin")).write_bytes(b"orphan")
            with self.assertRaisesRegex(ValueError, "receipt/blob pairing mismatch"):
                corpus.living_leads(root)

    def test_reviewed_input_bridge_requires_three_exact_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative, raw in (("candidate.json", b"{}\n"), ("primary.md", b"primary\n"), ("review.md", b"review\n")):
                (root / relative).write_bytes(raw)
            observation = self.observation("OBS-REVIEWED-A", "FND-REVIEWED", mechanisms=[])
            entry = {
                "id": "INPUT-001", "candidate": {"path": "candidate.json", "sha256": corpus.digest((root / "candidate.json").read_bytes())},
                "primary_evidence": {"path": "primary.md", "sha256": corpus.digest((root / "primary.md").read_bytes()), "external_identifier": "doi:test", "version": "v1", "independently_verified": True},
                "review": {"path": "review.md", "sha256": corpus.digest((root / "review.md").read_bytes()), "status": "VERIFIED_FOR_CORPUS"},
                "evidence_class": "external_primary", "scope": "bounded", "observations": [observation],
            }
            registry = {"format_version": "far-reviewed-inputs/1.0", "authority": "Research", "entries": [entry], "promotion_authority": False}
            target = root / corpus.REVIEWED_INPUTS
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(registry))
            data = copy.deepcopy(self.data)
            dynamic = root / data["dynamic_dependencies"][0]["path"]
            dynamic.parent.mkdir(parents=True, exist_ok=True)
            dynamic.write_text(json.dumps({"schema_version": data["dynamic_dependencies"][0]["format_value"]}))
            sources, errors = corpus.reviewed_sources(data, root)
            self.assertEqual(errors, [])
            self.assertEqual(sources[0]["review_status"], "VERIFIED_FOR_CORPUS")
            derived = corpus.derive(data, root)
            self.assertTrue(any(row["id"] == "FND-REVIEWED" for row in derived["normalized_findings"]))
            registry["entries"][0]["primary_evidence"]["sha256"] = "0" * 64
            target.write_text(json.dumps(registry))
            _, errors = corpus.reviewed_sources(data, root)
            self.assertTrue(any("primary evidence hash mismatch" in error for error in errors))

    def test_reviewed_bridge_accepts_exact_frozen_binary_primary_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "candidate.json").write_text("{}\n")
            (root / "primary.bin").write_bytes(b"%PDF exact frozen bytes\x00")
            (root / "review.md").write_text("verified\n")
            observation = self.observation("OBS-REVIEWED-BIN", "FND-REVIEWED-BIN", mechanisms=[])
            entry = {
                "id": "INPUT-BIN", "candidate": {"path": "candidate.json", "sha256": corpus.digest((root / "candidate.json").read_bytes())},
                "primary_evidence": {"path": "primary.bin", "sha256": corpus.digest((root / "primary.bin").read_bytes()), "external_identifier": "frozen:test", "version": "v1", "independently_verified": True},
                "review": {"path": "review.md", "sha256": corpus.digest((root / "review.md").read_bytes()), "status": "VERIFIED_FOR_CORPUS"},
                "evidence_class": "external_primary", "scope": "bounded", "observations": [observation],
            }
            target = root / corpus.REVIEWED_INPUTS
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps({"format_version": "far-reviewed-inputs/1.0", "authority": "Research", "entries": [entry], "promotion_authority": False}))
            sources, errors = corpus.reviewed_sources(self.data, root)
            self.assertEqual(errors, [])
            self.assertEqual(sources[0]["path"], "primary.bin")

    def test_unavailable_source_unresolved_observation_remains_uncertainty_signal(self):
        result = self.derive()
        finding = next(row for row in result["normalized_findings"] if row["id"] == "FND-HISTORY-MISSING")
        self.assertEqual(finding["state"], "UNRESOLVED")
        self.assertIn("OBS-SCHEDULED-TASK-HISTORY-HISTORY-MISSING", finding["unresolved_observation_ids"])
        self.assertIn("OBS-SCHEDULED-TASK-HISTORY-HISTORY-MISSING", result["observation_state"]["uncertainty_signals"])

    def test_pr571_snapshot_manifest_covers_every_extractor_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = corpus.ROOT / "research/corpus/snapshots"
            target = root / "research/corpus/snapshots"
            shutil.copytree(source, target)
            manifest_path = target / "pr-571-manifest-v1.0.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["files"] = [row for row in manifest["files"] if row["path"] != "research/saturation-falsification-001/findings-v1.0.json"]
            manifest["file_inventory_sha256"] = corpus.digest(corpus.canonical(manifest["files"]))
            manifest_path.write_text(json.dumps(manifest))
            errors = corpus.validate_snapshots(root)
            self.assertTrue(any("extractor input omitted" in error or "manifest coverage mismatch" in error for error in errors))

    def test_generated_integrity_changes_for_every_governed_input_class(self):
        original = self.derive()
        mutations = []
        semantic = copy.deepcopy(self.data); semantic["sources"][0]["observations"][0]["statement"] += " narrowed"; mutations.append(semantic)
        conclusion = copy.deepcopy(self.data); conclusion["conclusion_rules"][0]["statement"] += " bounded"; mutations.append(conclusion)
        mechanism = copy.deepcopy(self.data); mechanism["mechanism_catalog"][0]["literal_comparison"] += " checked"; mutations.append(mechanism)
        for mutated in mutations:
            changed = self.derive(mutated)
            self.assertNotEqual(original["corpus_sha256"], changed["corpus_sha256"])
        changed_hash = copy.deepcopy(self.data); changed_hash["sources"][0]["sha256"] = "0" * 64
        self.assertTrue(any("source hash mismatch" in error for error in corpus.validate(changed_hash)))

    def test_generator_schema_and_frozen_manifest_changes_invalidate_identities(self):
        original = self.derive()
        with tempfile.NamedTemporaryFile(suffix=".py") as generator:
            generator.write(b"changed generator\n"); generator.flush()
            with mock.patch.object(corpus, "__file__", generator.name):
                self.assertNotEqual(original["generator_sha256"], self.derive()["generator_sha256"])
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w") as schema:
            altered_schema = corpus.load_json(corpus.SCHEMA); altered_schema["title"] += " changed"
            schema.write(json.dumps(altered_schema)); schema.flush()
            # The wiring is asserted in test_real_outputs... above; here we prove altered bytes change the identity.
            self.assertNotEqual(original["schema_sha256"], corpus.digest(Path(schema.name).read_bytes()))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / "research/corpus/snapshots/pr-490-manifest-v1.0.json"; path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"candidate_count": 0, "candidate_blobs": [], "state_blobs": [], "candidate_inventory_sha256": "0" * 64, "state_inventory_sha256": "0" * 64}))
            self.assertTrue(any("inventory digest mismatch" in error for error in corpus.validate_snapshots(root)))

    def test_symlink_and_unexpected_source_type_are_rejected(self):
        invalid = copy.deepcopy(self.data); invalid["sources"][0]["path"] = "README.exe"
        self.assertTrue(any("unexpected source file type" in error for error in corpus.validate(invalid)))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); candidates = root / "research/living/inbox/candidates"; candidates.mkdir(parents=True)
            target = root / "candidate.json"; target.write_text('{}')
            (candidates / "FAR-LIT-LINK.json").symlink_to(target)
            with self.assertRaisesRegex(ValueError, "unsafe living candidate"):
                corpus.living_leads(root)

    def test_candidate_add_remove_changes_living_identity_without_fixed_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates = root / "research/living/inbox/candidates"
            candidates.mkdir(parents=True)
            first = candidates / "FAR-LIT-A.json"; first.write_text('{"id":"FAR-LIT-A","source_key":"doi:a"}')
            one = corpus.write_living(root)
            second = candidates / "FAR-LIT-B.json"; second.write_text('{"id":"FAR-LIT-B","source_key":"doi:b"}')
            two = corpus.write_living(root)
            second.unlink()
            one_again = corpus.write_living(root)
            self.assertEqual(two["candidate_count"], one["candidate_count"] + 1)
            self.assertNotEqual(one["candidate_set_sha256"], two["candidate_set_sha256"])
            self.assertEqual(one["candidate_set_sha256"], one_again["candidate_set_sha256"])


if __name__ == "__main__":
    unittest.main()
