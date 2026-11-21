"""Regression audit of exact hosted, NON-SCORED Qwen replanning capability smoke.

This test checks archive identity, reported negative outcomes and scope, not
independent provider attestations or FAR-REPLAN-001 experimental efficacy.
"""
from __future__ import annotations

import base64
import hashlib
import json
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'research/workflow-efficacy/evidence/replanning-smoke-20261121.zip.base64'
MANIFEST = ROOT / 'research/workflow-efficacy/evidence/replanning-smoke-20261121-manifest.json'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class SmokeArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_bytes())
        encoded = ARCHIVE.read_bytes()
        cls.raw = base64.b64decode(encoded.strip(), validate=True)
        cls.container = zipfile.ZipFile(BytesIO(cls.raw))
        cls.records = {arm: json.loads(cls.container.read(cls.manifest['arms'][arm]['record_path']))
                       for arm in ('control', 'replanning')}

    def test_archive_bytes_exactly_match_hosted_record(self):
        self.assertEqual(len(self.raw), 12353)
        self.assertEqual(len(self.raw), self.manifest['archive_bytes'])
        self.assertEqual(sha(self.raw), 'c8761815985b9938d52cd292653d5e5bd480ba7aeb7ff9f0e0d0afbed7da75c8')
        self.assertEqual(sha(self.raw), self.manifest['archive_sha256'])
        self.assertEqual(self.manifest['github_run_id'], 44946362557)
        self.assertEqual(self.manifest['exact_head'], '053bb91c4518159cea311f332ba214e715ccd177')

    def test_all_exact_members_and_digests(self):
        self.assertEqual(set(self.container.namelist()), set(self.manifest['members']))
        for name, meta in self.manifest['members'].items():
            raw = self.container.read(name)
            with self.subTest(name=name):
                self.assertEqual(len(raw), meta['bytes'])
                self.assertEqual(sha(raw), meta['sha256'])

    def test_model_identity_probed_but_no_scored_executions(self):
        probe = json.loads(self.container.read('preflight.json'))
        self.assertEqual(probe['mode'], 'PREFLIGHT_ONLY_NO_TASK_EXPOSURE')
        self.assertEqual(probe['verified_digest'], self.manifest['model_digest'])
        self.assertEqual(probe['model']['name'], 'qwen2.5-coder:7b')
        self.assertEqual(probe['scored_runs'], 0)
        self.assertEqual(self.manifest['pilot_pair_count'], 0)
        self.assertEqual(self.manifest['scored_task_count'], 0)
        self.assertIs(self.manifest['test_case_in_candidate_cohort'], False)

    def test_both_real_arms_are_negative_and_unscored(self):
        for arm, record in self.records.items():
            with self.subTest(arm=arm):
                self.assertEqual(record['task_id'], 'FWE-001')
                self.assertEqual(record['arm'], arm)
                self.assertEqual(record['provenance'], 'LOCAL_OLLAMA')
                self.assertEqual(record['model']['digest'], self.manifest['model_digest'])
                self.assertIs(record['cohort_member'], False)
                self.assertIs(record['study_score'], False)
                self.assertEqual(record['smoke_label'], 'NONCOHORT_CAPABILITY_ONLY')
                self.assertEqual(record['status'], 'DIAGNOSTIC_ONLY_NOT_INDEPENDENTLY_ATTESTED')
                self.assertIs(record['fault_injected'], True)
                self.assertEqual(record['initial_file_sha256'], record['final_file_sha256'])
                self.assertIs(record['grade']['executed'], True)
                self.assertIs(record['grade']['success'], False)
                self.assertEqual(record['grade']['exit_status'], 1)
                self.assertEqual(record['grade']['source'], 'trusted-host-docker-grader')
                self.assertEqual(sha(record['grade']['trace'].encode()), record['grade']['trace_sha256'])
                self.assertEqual(len(record['model_requests']), self.manifest['arms'][arm]['model_requests'])
                self.assertEqual(len(record['tool_execution_receipts']), self.manifest['arms'][arm]['tool_calls'])
                self.assertEqual(len(record['orchestration_result_sha256']), self.manifest['arms'][arm]['orchestration_rounds'])
                self.assertEqual(record['usage']['model_tokens'], self.manifest['arms'][arm]['model_tokens'])

    def test_one_shot_fault_and_extra_round_do_not_claim_success(self):
        for arm, rec in self.records.items():
            failures = [r for r in rec['tool_execution_receipts']
                        if r['result'].get('error') == 'INJECTED_TRANSIENT_WRITE_FAILURE']
            self.assertEqual(len(failures), 1, arm)
            self.assertIs(failures[0]['result']['executed'], False)
        self.assertEqual(len(self.records['control']['orchestration_result_sha256']), 1)
        self.assertEqual(len(self.records['replanning']['orchestration_result_sha256']), 2)
        self.assertEqual(len(self.records['control']['model_requests']), 4)
        self.assertEqual(len(self.records['replanning']['model_requests']), 7)
        self.assertEqual(self.records['replanning']['trace_status'], 'NO_NEW_VERIFIED_EVENT')


if __name__ == '__main__':
    unittest.main()
