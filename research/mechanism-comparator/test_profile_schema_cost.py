"""Adversarial diagnostics and cache invalidation controls, research only.

These tests do not authorize production use of a temporary module override.
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import compare
import profile_schema_cost as probe
from mechanization.far_mechanization import contract_v2, contract_v2_errata1


class TestSchemaCacheProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.primary, cls.integrity = compare.prepare_corpus()

    def test_all_24_finite_inputs_diagnostic_identity(self):
        inputs = [x["document"] for x in self.primary + self.integrity]
        inputs.extend([{}, None, {**self.primary[0]["document"], "format_version": "bad"}])
        self.assertEqual(len(inputs), 24)
        for index, document in enumerate(inputs):
            original = probe.inspect(document)
            with probe.research_only_override():
                cached = probe.inspect(document)
            self.assertEqual(cached, original, "input number " + str(index))

    def test_content_cache_change_causes_new_compilation(self):
        probe._compiled_validator.cache_clear()
        original = contract_v2.SCHEMA_PATH.read_text(encoding="utf-8")
        changed_schema = json.loads(original)
        changed_schema["$comment"] = "research synthetic source-content change"
        changed = json.dumps(changed_schema, sort_keys=True)
        a = probe._compiled_validator(original)
        self.assertIs(a, probe._compiled_validator(original))
        b = probe._compiled_validator(changed)
        self.assertIsNot(a, b)
        info = probe._compiled_validator.cache_info()
        self.assertEqual(info.misses, 2)
        self.assertGreaterEqual(info.hits, 1)
        probe._compiled_validator.cache_clear()

    def test_actual_schema_file_content_change_is_respected(self):
        with tempfile.TemporaryDirectory() as temp:
            fake = pathlib.Path(temp) / "schema.json"
            fake.write_text('{"type":"object"}', encoding="utf-8")
            probe._compiled_validator.cache_clear()
            with patch.object(contract_v2, "SCHEMA_PATH", fake):
                self.assertEqual(probe.cached_schema_errors({"a": 1}), [])
                fake.write_text('{"type":"integer"}', encoding="utf-8")
                self.assertTrue(probe.cached_schema_errors({"a": 1}))
                self.assertEqual(probe.cached_schema_errors(17), [])
            self.assertEqual(probe._compiled_validator.cache_info().misses, 2)
            probe._compiled_validator.cache_clear()

    def test_override_restores_original_on_exception(self):
        original = contract_v2_errata1._schema_errors
        with self.assertRaisesRegex(RuntimeError, "deliberate"):
            with probe.research_only_override():
                self.assertIs(contract_v2_errata1._schema_errors, probe.cached_schema_errors)
                raise RuntimeError("deliberate")
        self.assertIs(contract_v2_errata1._schema_errors, original)

    def test_original_frozen_verifier_bytes_never_changed(self):
        path = pathlib.Path(contract_v2.__file__)
        original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        doc = copy.deepcopy(self.primary[0]["document"])
        with probe.research_only_override():
            probe.inspect(doc)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), original_hash)
        self.assertIsNot(contract_v2_errata1._schema_errors, probe.cached_schema_errors)


if __name__ == "__main__":
    unittest.main()
