"""Guard retry bounds and immutable pins in every Lean-download workflow."""
from pathlib import Path
import shlex
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
URL = "https://github.com/leanprover/lean4/releases/download/v4.19.0/lean-4.19.0-linux.tar.zst"
PIN = "6fe3ce97a58f44e2b3567d455b994eacec5bfe9ae7774f2a573444480ba813fe"
WORKFLOWS = ("validator-assurance.yml", "exact-head-assurance.yml", "lean.yml",
             "far-core-v11-formalization.yml", "pca-w5.yml")


def download_step(filename):
    workflow = yaml.safe_load((ROOT / ".github/workflows" / filename).read_text())
    matches = [step["run"] for job in workflow["jobs"].values()
               for step in job.get("steps", []) if URL in step.get("run", "")]
    if len(matches) != 1:
        raise AssertionError(f"{filename}: expected one pinned Lean download step")
    script = matches[0]
    commands = [shlex.split(line.strip()) for line in script.splitlines()
                if line.strip().startswith("curl ")]
    if len(commands) != 1:
        raise AssertionError(f"{filename}: expected one curl command")
    return script, commands[0]


class PinnedLeanTransportTests(unittest.TestCase):
    def test_every_lane_bounds_retries_and_preserves_release_and_digest(self):
        commands = []
        for filename in WORKFLOWS:
            with self.subTest(workflow=filename):
                script, argv = download_step(filename)
                self.assertIn("-sSfL", argv)
                for flag, ceiling in (("--retry", 3), ("--retry-max-time", 120),
                                      ("--connect-timeout", 15), ("--max-time", 120)):
                    self.assertIn(flag, argv)
                    value = int(argv[argv.index(flag) + 1])
                    self.assertGreater(value, 0)
                    self.assertLessEqual(value, ceiling)
                self.assertIn("--retry-delay", argv)
                self.assertEqual("1", argv[argv.index("--retry-delay") + 1])
                self.assertEqual(1, argv.count(URL))
                self.assertNotIn("--insecure", argv)
                self.assertIn(f'echo "{PIN}  $archive" | sha256sum -c -', script)
                self.assertIn("set -euo pipefail", script)
                commands.append(argv)
        self.assertEqual(len(WORKFLOWS), len(commands))
        self.assertTrue(all(argv == commands[0] for argv in commands))


if __name__ == "__main__":
    unittest.main()
