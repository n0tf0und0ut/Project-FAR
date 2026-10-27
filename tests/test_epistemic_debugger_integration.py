"""Run the downstream suite in isolation so generic module names cannot alias."""
from pathlib import Path
import subprocess
import sys
import unittest


class DebuggerIntegration(unittest.TestCase):
    def test_debugger_integration(self):
        root=Path(__file__).resolve().parents[1]
        result=subprocess.run([sys.executable,"-m","unittest","discover","-s",
                               "commercial/far-investigation-audit/tests","-p","test_debugger*.py"],
                              cwd=root,text=True,capture_output=True,timeout=180)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
