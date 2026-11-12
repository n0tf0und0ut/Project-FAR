"""Regression tests for unambiguous software-factory work-order intake."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.software_factory import FactoryError, parse_order_text

BASE = Path(__file__).resolve().parents[1]
GOOD = {
    "schema": "far-software-factory/work-order/1",
    "id": "json-intake-pilot",
    "repository": "n0tf0und0ut/Project-FAR",
    "base_sha": "4d5397eed52e933fe2c9a96a600ceee70c0585a7",
    "tasks": [
        {"id": "repair", "objective": "Reject ambiguous JSON", "acceptance": ["Duplicate keys rejected"], "depends_on": []}
    ],
}


class StrictIntakeTests(unittest.TestCase):
    def test_valid_order_is_unchanged(self):
        raw = json.dumps(GOOD, ensure_ascii=False)
        self.assertEqual(parse_order_text(raw), GOOD)

    def test_rejects_duplicate_top_level_key(self):
        raw = json.dumps(GOOD).replace('"id": "json-intake-pilot"', '"id": "allowed", "id": "json-intake-pilot"', 1)
        with self.assertRaisesRegex(FactoryError, "duplicate JSON object key"):
            parse_order_text(raw)

    def test_rejects_duplicate_nested_key(self):
        raw = json.dumps(GOOD).replace('"objective": "Reject ambiguous JSON"', '"objective": "ignored", "objective": "Reject ambiguous JSON"', 1)
        with self.assertRaisesRegex(FactoryError, "duplicate JSON object key"):
            parse_order_text(raw)

    def test_rejects_nonstandard_numeric_tokens(self):
        for token in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(token=token), self.assertRaisesRegex(FactoryError, "non-finite"):
                parse_order_text('{"untrusted": ' + token + '}')

    def test_rejects_trailing_content(self):
        with self.assertRaisesRegex(FactoryError, "malformed JSON"):
            parse_order_text(json.dumps(GOOD) + ' {"extra":true}')

    def test_cli_fails_closed_without_persisting_ambiguous_order(self):
        raw = json.dumps(GOOD).replace('"objective": "Reject ambiguous JSON"', '"objective": "ignored", "objective": "Reject ambiguous JSON"', 1)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            order_file = path / "order.json"
            db_file = path / "factory.db"
            order_file.write_text(raw, encoding="utf-8")
            proc = subprocess.run([
                sys.executable, str(BASE / "tools" / "software_factory.py"),
                "--db", str(db_file), "submit", str(order_file),
            ], capture_output=True, text=True, timeout=15, check=False)
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertIn("duplicate JSON object key", proc.stderr)
            import sqlite3
            with sqlite3.connect(db_file) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
