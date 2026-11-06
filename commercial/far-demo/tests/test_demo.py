from __future__ import annotations

import importlib.util
import unittest

if importlib.util.find_spec("fastapi") is None:
    raise unittest.SkipTest(
        "far-demo tests require the optional dependencies declared by commercial/far-demo"
    )

import csv
import copy
import io
import json

import yaml
from fastapi.testclient import TestClient

from far_demo.app import SAMPLE_BASELINE, SAMPLE_CANDIDATE, app
from far_demo.formats import SUPPORTED_EXTENSIONS, parse_package_file


class TestFarDemo(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_identifies_far_engine(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["engine"], "far-decision-integrity")

    def test_example_is_deterministic_and_blocks_control_regression(self) -> None:
        first = self.client.get("/api/example").json()
        second = self.client.get("/api/example").json()
        self.assertEqual(first, second)
        self.assertEqual(first["status_transition"], ["justified", "unsupported"])
        self.assertEqual(first["status"], "unsupported")
        self.assertEqual(first["release_decision"], "BLOCKED")
        self.assertEqual(len(first["structural_changes"]), 2)
        self.assertGreaterEqual(len(first["rule_findings"]), 1)
        removed = {item["node_id"] for item in first["structural_changes"]}
        self.assertEqual(removed, {"sanctions-clearance", "treasury-approval"})
        self.assertEqual(first["changes"], first["structural_changes"] + first["rule_findings"])
        self.assertEqual(len(first["artifact"]["sha256"]), 64)

    def test_report_download_contains_release_decision(self) -> None:
        response = self.client.get("/api/example/report")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["content-disposition"])
        payload = response.json()
        self.assertEqual(payload["engine"], "far-decision-integrity/1.0.0")
        self.assertEqual(payload["candidate"]["status"], "unsupported")
        self.assertEqual(payload["release_decision"], "BLOCKED")

    def test_page_presents_frontier_treasury_experience(self) -> None:
        page = self.client.get("/").text
        self.assertIn("Your eval says", page)
        self.assertIn("$2.4M", page)
        self.assertIn("NovaGrid Systems GmbH", page)
        self.assertIn("Run release-integrity audit", page)
        self.assertNotIn("$420 refund", page)
        self.assertNotIn("#d9ff6a", page.lower())

    def test_json_upload_flow_remains_evidence_bound(self) -> None:
        response = self.client.post(
            "/api/analyze",
            files={
                "baseline": ("baseline.json", json.dumps(SAMPLE_BASELINE), "application/json"),
                "candidate": ("candidate.json", json.dumps(SAMPLE_CANDIDATE), "application/json"),
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "unsupported")
        self.assertEqual(payload["release_decision"], "BLOCKED")
        self.assertEqual(len(payload["structural_changes"]), 2)
        self.assertIn("2 dependencies", payload["plain_summary"])
        self.assertNotIn("NovaGrid", payload["headline"])

    def test_all_json_upload_paths_reject_ambiguity_before_adjudication(self) -> None:
        payload = copy.deepcopy(SAMPLE_BASELINE)
        payload['metadata'] = {'probe': 'placeholder'}
        plain = json.dumps(payload)
        hostile = [plain.replace('"decision_id":', '"decision_id":"injected","decision_id":', 1),
                   plain.replace('"probe": "placeholder"', '"probe":1,"probe":2')]
        hostile += [plain.replace('"placeholder"', token)
                    for token in ('NaN', 'Infinity', '-Infinity', '1e999')]
        hostile.append('[' * 10000 + '0' + ']' * 10000)
        for raw in hostile:
            for filename, content in [('input.json', raw), ('input.jsonl', raw + '\n'),
                    ('input.txt', raw), ('input.md', '# Package\n```json\n' + raw + '\n```'),
                    ('input.md', '```jsonl\n' + raw + '\n```'),
                    ('input.md', '```\n' + raw + '\n```')]:
                with self.subTest(filename=filename, raw=raw[:100]):
                    response = self.client.post('/api/analyze', files={
                        'baseline': (filename, content, 'application/octet-stream'),
                        'candidate': ('good.json', json.dumps(SAMPLE_CANDIDATE), 'application/json'),
                    })
                    self.assertEqual(response.status_code, 400, response.text)

    def test_declared_fenced_json_cannot_be_reinterpreted_as_yaml(self) -> None:
        # Valid YAML flow syntax, invalid JSON: a JSON declaration must control.
        raw = json.dumps(SAMPLE_BASELINE)[:-1] + ',}'
        response = self.client.post('/api/analyze', files={
            'baseline': ('input.md', '```json\n' + raw + '\n```', 'text/markdown'),
            'candidate': ('good.json', json.dumps(SAMPLE_CANDIDATE), 'application/json'),
        })
        self.assertEqual(response.status_code, 400)

    def test_yaml_fallback_cannot_erase_duplicate_mapping_keys(self) -> None:
        raw = json.dumps(SAMPLE_BASELINE).replace('"decision_id":',
            '"decision_id":"injected","decision_id":', 1)[:-1] + ',}'
        for filename, content in [('input.yaml', raw), ('input.txt', raw),
                ('input.md', '```yaml\n' + raw + '\n```')]:
            with self.subTest(filename=filename):
                response = self.client.post('/api/analyze', files={
                    'baseline': (filename, content, 'application/octet-stream'),
                    'candidate': ('good.json', json.dumps(SAMPLE_CANDIDATE), 'application/json'),
                })
                self.assertEqual(response.status_code, 400, response.text)

    def test_yaml_merge_defaults_and_explicit_override_are_preserved(self) -> None:
        payload = copy.deepcopy(SAMPLE_BASELINE)
        payload['metadata'] = {}
        raw = yaml.safe_dump(payload, sort_keys=False).replace('metadata: {}',
            'metadata:\n  <<: &defaults {origin: inherited, keep: retained}\n  origin: explicit')
        for filename, content in [('input.yaml', raw), ('input.txt', raw),
                ('input.md', '```yaml\n' + raw + '\n```')]:
            with self.subTest(filename=filename):
                parsed = parse_package_file(filename, content.encode())
                self.assertEqual(parsed['metadata'], {'origin': 'explicit', 'keep': 'retained'})

    def test_yaml_and_toml_text_routes_remain_supported(self) -> None:
        def toml_value(value):
            if isinstance(value, dict):
                return '{' + ','.join(json.dumps(k) + '=' + toml_value(v) for k, v in value.items()) + '}'
            if isinstance(value, list):
                return '[' + ','.join(toml_value(v) for v in value) + ']'
            return json.dumps(value)
        yaml_text = yaml.safe_dump(SAMPLE_BASELINE, sort_keys=False)
        toml_text = '\n'.join(k + '=' + toml_value(v) for k, v in SAMPLE_BASELINE.items())
        for filename, raw in [('input.yaml', yaml_text), ('input.txt', yaml_text),
                ('input.md', '```yaml\n' + yaml_text + '\n```'), ('input.toml', toml_text),
                ('input.txt', toml_text), ('input.md', '```toml\n' + toml_text + '\n```')]:
            with self.subTest(filename=filename, raw=raw[:50]):
                response = self.client.post('/api/analyze', files={
                    'baseline': (filename, raw, 'application/octet-stream'),
                    'candidate': ('good.json', json.dumps(SAMPLE_CANDIDATE), 'application/json'),
                })
                self.assertEqual(response.status_code, 200, response.text)

    def test_yaml_and_markdown_can_be_mixed(self) -> None:
        baseline_yaml = yaml.safe_dump(SAMPLE_BASELINE, sort_keys=False)
        candidate_markdown = "# Candidate\n\n```json\n" + json.dumps(SAMPLE_CANDIDATE) + "\n```\n"
        response = self.client.post(
            "/api/analyze",
            files={
                "baseline": ("baseline.yaml", baseline_yaml, "application/yaml"),
                "candidate": ("candidate.md", candidate_markdown, "text/markdown"),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["release_decision"], "BLOCKED")

    def test_tabular_csv_adapter_handles_richer_package(self) -> None:
        stream = io.StringIO()
        fields = [
            "record_type", "key", "value", "node_id", "kind", "statement",
            "attributes", "source_id", "target_id", "relation",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for key in (
            "schema_version", "decision_id", "decision_type", "policy_version",
            "decision_root", "trace_completeness",
        ):
            writer.writerow({"record_type": "meta", "key": key, "value": json.dumps(SAMPLE_BASELINE[key])})
        for key, value in SAMPLE_BASELINE["proposed_action"].items():
            writer.writerow({"record_type": "meta", "key": f"proposed_action.{key}", "value": json.dumps(value)})
        for node in SAMPLE_BASELINE["nodes"]:
            writer.writerow({"record_type": "node", **node, "attributes": json.dumps(node["attributes"])})
        for dependency in SAMPLE_BASELINE["dependencies"]:
            writer.writerow({"record_type": "dependency", **dependency})
        for node_id in SAMPLE_BASELINE["authorization_requirements"]:
            writer.writerow({"record_type": "authorization_requirement", "node_id": node_id})
        parsed = parse_package_file("baseline.csv", stream.getvalue().encode())
        self.assertEqual(parsed["decision_id"], "treasury-wire-baseline-741")
        self.assertEqual(len(parsed["nodes"]), 8)
        self.assertEqual(len(parsed["dependencies"]), 7)
        self.assertEqual(len(parsed["authorization_requirements"]), 2)
        for value in ('{"probe":1,"probe":2}', '{"probe":NaN}', '{"probe":1e999}'):
            extra = io.StringIO()
            csv.DictWriter(extra, fieldnames=fields).writerow({
                'record_type': 'meta', 'key': 'metadata.probe', 'value': value})
            response = self.client.post('/api/analyze', files={
                'baseline': ('input.csv', stream.getvalue() + extra.getvalue(), 'text/csv'),
                'candidate': ('good.json', json.dumps(SAMPLE_CANDIDATE), 'application/json'),
            })
            self.assertEqual(response.status_code, 400)

    def test_common_extensions_are_declared(self) -> None:
        expected = {
            ".json", ".jsonl", ".yaml", ".yml", ".toml", ".xml", ".csv",
            ".txt", ".md", ".docx", ".pdf", ".xlsx",
        }
        self.assertEqual(SUPPORTED_EXTENSIONS, expected)

    def test_rejects_unknown_extension(self) -> None:
        response = self.client.post(
            "/api/analyze",
            files={
                "baseline": ("baseline.exe", b"not a package", "application/octet-stream"),
                "candidate": ("candidate.json", json.dumps(SAMPLE_CANDIDATE), "application/json"),
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file type", response.json()["detail"])

    def test_rejects_non_far_json(self) -> None:
        response = self.client.post(
            "/api/analyze",
            files={
                "baseline": ("baseline.json", "{}", "application/json"),
                "candidate": ("candidate.json", "{}", "application/json"),
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_removed_non_authorization_support_requires_review(self) -> None:
        candidate = copy.deepcopy(SAMPLE_BASELINE)
        candidate["decision_id"] = "candidate-with-support-removed"
        candidate["dependencies"] = [d for d in candidate["dependencies"] if d["source_id"] != "invoice-match"]
        response = self.client.post("/api/analyze", files={
            "baseline": ("base.json", json.dumps(SAMPLE_BASELINE), "application/json"),
            "candidate": ("candidate.json", json.dumps(candidate), "application/json"),
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "justified")
        self.assertEqual(payload["release_decision"], "REVIEW_REQUIRED")
        self.assertEqual(payload["artifact"]["release_decision"], "REVIEW_REQUIRED")
        self.assertEqual(payload["structural_changes"][0]["type"], "decision_dependency_removed")

    def test_malformed_supported_uploads_return_validation_error(self) -> None:
        for extension, raw in (("yaml", b"a: ["), ("xml", b"<unclosed>"),
                               ("xlsx", b"not a zip"), ("docx", b"not a zip"), ("pdf", b"not a pdf")):
            with self.subTest(extension=extension):
                response = self.client.post("/api/analyze", files={
                    "baseline": ("bad." + extension, raw, "application/octet-stream"),
                    "candidate": ("good.json", json.dumps(SAMPLE_BASELINE), "application/json"),
                })
                self.assertEqual(response.status_code, 400)
                self.assertIn("Invalid", response.json()["detail"])

    def test_xml_does_not_fabricate_required_trace_completeness(self) -> None:
        parsed = parse_package_file("missing.xml", b"<package><decision_id>case</decision_id></package>")
        self.assertNotIn("trace_completeness", parsed)

    def test_download_link_targets_current_rendered_artifact(self) -> None:
        page = self.client.get("/").text
        self.assertIn('id="downloadReport"', page)
        self.assertIn('updateReportDownload(d.artifact)', page)
        self.assertNotIn('href="/api/example/report"', page)
        self.assertNotIn('signed evidence report', page)


if __name__ == "__main__":
    unittest.main()
