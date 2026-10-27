"""Execute the native job's real shell across deployment/failure boundaries."""
import base64
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/required-pr-review-convergence.yml"
BASE = "e4d936ca0ba9770be6f72e0435220987882f4146"
HEAD = "a" * 40
PIN = "dc4924a288bb658c2a12e860d6c31ac7bff80c4c"
DIGEST = "778404e527824a170041a5bd8e9ae67421291246a8eff19682b53af4f58909fc"
# The dormant e4d/#578 exception pins this historical file, not whichever
# collector a later protected main supplies. Retain its actual original bytes.
PINNED_COLLECTOR = ROOT / "tests/fixtures/pr-review-collector-dc4924a.py.txt"


def enforcement_script():
    workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    return workflow["jobs"]["required-review"]["steps"][1]["run"]


STUBS = r'''
gh() {
  [[ "$1" == api ]] || return 31
  if [[ "$#" -eq 2 && "$2" == "/repos/$GITHUB_REPOSITORY/pulls/$PR_NUMBER" ]]; then
    printf '{"base":{"ref":"main"},"head":{"sha":"%s"}}\n' "$MOCK_HEAD"
  elif [[ "$#" -eq 4 && "$2" == "/repos/$GITHUB_REPOSITORY/pulls/$PR_NUMBER" &&
          "$3" == --jq && "$4" == .head.sha ]]; then
    printf '%s\n' "$MOCK_CURRENT"
  elif [[ "$#" -eq 4 && "$2" == "/repos/$GITHUB_REPOSITORY/contents/tools/pr_review_convergence.py?ref=dc4924a288bb658c2a12e860d6c31ac7bff80c4c" &&
          "$3" == --jq && "$4" == .content ]]; then
    printf 'download\n' >> "$MOCK_CALLS"
    command python3 -c 'import pathlib,sys; sys.stdout.write(pathlib.Path(sys.argv[1]).read_text())' "$MOCK_PAYLOAD"
    return "$MOCK_DOWNLOAD_EXIT"
  else
    return 32
  fi
}
jq() {
  [[ "$#" -eq 2 && "$1" == -r ]] || return 33
  command python3 -c 'import json,sys
value=json.load(sys.stdin)
for key in sys.argv[1].lstrip(".").split("."): value=value[key]
print(value)' "$2"
}
git() {
  [[ "$#" -eq 2 && "$1" == rev-parse && "$2" == HEAD ]] || return 34
  printf '%s\n' "$MOCK_MAIN"
}
base64() {
  [[ "$#" -eq 1 && "$1" == --decode ]] || return 36
  command python3 -c 'import base64,sys; sys.stdout.buffer.write(base64.b64decode(sys.stdin.buffer.read(), validate=True))'
}
sha256sum() {
  [[ "$#" -eq 2 && "$1" == --check && "$2" == --status ]] || return 37
  command python3 -c 'import hashlib,pathlib,sys
digest,path=sys.stdin.read().rstrip("\n").split("  ",1)
sys.exit(0 if hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()==digest else 1)'
}
python3() {
  [[ "$#" -eq 11 && "$2" == --repository && "$3" == "$GITHUB_REPOSITORY" &&
     "$4" == --pr && "$5" == "$PR_NUMBER" && "$6" == --expected-head &&
     "$7" == "$EVENT_HEAD" && "$8" == --output &&
     "$9" == "$RUNNER_TEMP/pr-review-required.json" &&
     "${10}" == --mode && "${11}" == enforce ]] || return 35
  printf '%s\n' "$1" >> "$MOCK_CALLS"
  return "$MOCK_COLLECTOR_EXIT"
}
'''


class BootstrapTests(unittest.TestCase):
    def execute(self, *, main=BASE, pr="578", repository="n0tf0und0ut/Project-FAR",
                payload=None, download_exit=0, collector_exit=0,
                event_head=HEAD, current=HEAD):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = PINNED_COLLECTOR.read_bytes() if payload is None else payload
            (root / "payload").write_bytes(base64.b64encode(raw))
            env = dict(os.environ, GITHUB_REPOSITORY=repository, PR_NUMBER=pr,
                       EVENT_HEAD=event_head, RUNNER_TEMP=directory, GH_TOKEN="synthetic",
                       MOCK_MAIN=main, MOCK_HEAD=HEAD, MOCK_CURRENT=current,
                       MOCK_PAYLOAD=str(root / "payload"), MOCK_CALLS=str(root / "calls"),
                       MOCK_DOWNLOAD_EXIT=str(download_exit), MOCK_COLLECTOR_EXIT=str(collector_exit))
            result = subprocess.run(["bash", "-c", STUBS + "\n" + enforcement_script()],
                                    env=env, text=True, capture_output=True, timeout=10)
            calls = (root / "calls").read_text().splitlines() if (root / "calls").exists() else []
            return result, calls

    def test_pin_digest_matches_the_exact_collector(self):
        self.assertEqual(hashlib.sha256(PINNED_COLLECTOR.read_bytes()).hexdigest(),
                         DIGEST)
        self.assertIn("?ref=" + PIN, enforcement_script())
        self.assertIn(DIGEST, enforcement_script())

    def test_authorized_base_pr_repository_loads_only_pinned_verified_file(self):
        result, calls = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[0], "download")
        self.assertTrue(calls[1].endswith("/pr-review-policy-v1.1.py"))
        self.assertEqual(len(calls), 2)

    def test_other_pr_or_repository_at_old_base_cannot_inherit_exception(self):
        for kwargs in ({"pr": "588"}, {"repository": "attacker/fork"}):
            with self.subTest(kwargs=kwargs):
                result, calls = self.execute(**kwargs)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls, [])

    def test_after_main_moves_normal_collector_runs_without_download(self):
        result, calls = self.execute(main="b" * 40, pr="590")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["tools/pr_review_convergence.py"])

    def test_bad_digest_or_failed_download_never_executes(self):
        for kwargs in ({"payload": b"print('forged pass')\n"}, {"download_exit": 1}):
            with self.subTest(kwargs=kwargs):
                result, calls = self.execute(**kwargs)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls, ["download"])

    def test_enforcement_failure_and_pre_post_head_drift_fail_job(self):
        for kwargs in ({"collector_exit": 2}, {"event_head": "b" * 40},
                       {"current": "b" * 40}):
            with self.subTest(kwargs=kwargs):
                result, _ = self.execute(**kwargs)
                self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
