import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
FAR = ROOT / "far"
VALID = ROOT / "examples" / "mechanization" / "minimal-investigation.json"
GRAPH_VALID = ROOT / "tests" / "fixtures" / "mechanization" / "graph" / "valid" / "valid-graph.json"
BROKEN = ROOT / "tests" / "fixtures" / "mechanization" / "graph" / "invalid" / "broken-reference.json"

class CLITests(unittest.TestCase):
    def run_far(self, *args, input_text=None):
        return subprocess.run([sys.executable, str(FAR), *map(str, args)], input=input_text, text=True, capture_output=True, cwd=ROOT)

    def test_help_and_version(self):
        help_result = self.run_far("help")
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("validate", help_result.stdout)
        version = self.run_far("version", "--output", "json")
        self.assertEqual(version.returncode, 0)
        self.assertEqual(json.loads(version.stdout)["schema_version"], "far-ir/1.0")

    def test_validate_exit_codes_stdout_stderr_and_json(self):
        ok = self.run_far("validate", VALID)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn("VALID", ok.stdout)
        bad = self.run_far("validate", "--output", "json", BROKEN)
        self.assertNotEqual(bad.returncode, 0)
        payload = json.loads(bad.stdout)
        self.assertFalse(payload["valid"])
        self.assertGreater(payload["summary"]["error"], 0)

    def test_parse_normalize_export_and_stdin(self):
        parsed = self.run_far("parse", "--output", "json", VALID)
        self.assertEqual(parsed.returncode, 0, parsed.stderr)
        self.assertEqual(json.loads(parsed.stdout)["format_version"], "far-ir/1.0")
        normalized = self.run_far("normalize", "--output", "yaml", VALID)
        self.assertEqual(normalized.returncode, 0, normalized.stderr)
        self.assertIn("format_version: far-ir/1.0", normalized.stdout)
        stdin = self.run_far("parse", "--format", "json", "-", input_text=VALID.read_text())
        self.assertEqual(stdin.returncode, 0, stdin.stderr)
        exported = self.run_far("export", "--kind", "json", VALID)
        self.assertEqual(exported.returncode, 0, exported.stderr)
        self.assertEqual(json.loads(exported.stdout)["id"], "DOC-minimal")

    def test_graph_stats_diagnostics_and_inspect(self):
        graph = self.run_far("graph", "--output", "json", GRAPH_VALID)
        self.assertEqual(graph.returncode, 0, graph.stderr)
        self.assertIn("statistics", json.loads(graph.stdout))
        stats = self.run_far("stats", "--output", "json", GRAPH_VALID)
        self.assertEqual(stats.returncode, 0, stats.stderr)
        self.assertGreater(json.loads(stats.stdout)["node_count"], 0)
        diags = self.run_far("diagnostics", "--sort", "code", BROKEN)
        self.assertNotEqual(diags.returncode, 0)
        self.assertIn("FAR-GRAPH-001", diags.stdout)
        inspect = self.run_far("inspect", "--output", "json", GRAPH_VALID, "C1")
        self.assertEqual(inspect.returncode, 0, inspect.stderr)
        self.assertEqual(json.loads(inspect.stdout)["type"], "claim")

    def test_missing_file_configuration_graph_export_and_write_protection(self):
        missing = self.run_far("validate", ROOT / "no-such-file.json")
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("FAR-PARSE-006", missing.stdout + missing.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "far.yaml"
            cfg.write_text("output: json\nquiet: false\n", encoding="utf-8")
            cfg_result = self.run_far("--config", cfg, "version")
            self.assertEqual(cfg_result.returncode, 0)
            self.assertTrue(cfg_result.stdout.lstrip().startswith("{"))
            graph_out = Path(tmp) / "graph.json"
            graph = self.run_far("graph", GRAPH_VALID, "--export", graph_out)
            self.assertEqual(graph.returncode, 0, graph.stderr)
            self.assertTrue(graph_out.exists())
            target = Path(tmp) / "normalized.json"
            target.write_text("exists", encoding="utf-8")
            blocked = self.run_far("normalize", "--write", target, VALID)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("Refusing to overwrite", blocked.stderr)

if __name__ == "__main__":
    unittest.main()
