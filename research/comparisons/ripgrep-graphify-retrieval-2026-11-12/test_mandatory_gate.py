#!/usr/bin/env python3
"""Regression tests for the nonproduction tool-conditioned synthetic-refactor pilot."""
import ast
import hashlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch

D=Path(__file__).resolve().parent
_real_exists=Path.exists
def _research_only_import_guard(path):
    # The runner intentionally rejects replay over completed evidence; importing
    # pure helpers does not constitute another study execution.
    if str(path)==str(D/'mandatory_gate_raw.jsonl'):return False
    return _real_exists(path)
with patch.object(Path,'exists',_research_only_import_guard):
    import mandatory_gate_run as m

class Tests(unittest.TestCase):
    def test_pinned_graph_source_and_original_runner(self):
        assert len(m.TRACKED)==945
        assert m.P['graph_sha256']==hashlib.sha256(m.GRAPH.read_bytes()).hexdigest()
        assert m.P['source_sha']=='8c6dc6cf840a0d82fb4dcde114c1af471b3f74fe'
        assert len(m.P['tasks'])==24

    def test_prior_pilot_tasks_disjoint(self):
        earlier=json.loads((D/'protocol.json').read_text())
        old={x['function'] for x in earlier['tasks']}
        new={x['function'] for x in m.P['tasks']}
        self.assertEqual(len(old&new),0)
        self.assertEqual(len(new),24)

    def test_ast_name_and_attribute_calls_without_strings_or_comments(self):
        code='''def alpha_long_name():\n    return 1\n\ndef foo():\n    a=alpha_long_name()\n    b=obj.alpha_long_name()\n    c="alpha_long_name()"\n    # alpha_long_name()\n    return a+b\n'''
        edited,count=m.mutation_spans(code,'alpha_long_name',rename_defs=True)
        self.assertEqual(count,3)
        self.assertEqual(edited.count('alpha_long_name_farref_v2'),3)
        self.assertIn('"alpha_long_name()"',edited)
        self.assertIn('# alpha_long_name()',edited)
        self.assertEqual(len([n for n in ast.walk(ast.parse(edited)) if m.caller_match(n,'alpha_long_name')]),0)

    def test_noncall_references_are_preserved(self):
        src='''my_thing="alpha_long_name()"\n# alpha_long_name()\ndef beta():\n    return my_thing\n'''
        edited,count=m.mutation_spans(src,'alpha_long_name',rename_defs=False)
        self.assertEqual(edited,src)
        self.assertEqual(count,0)

    def test_rejects_unrecognized_model_actions(self):
        for invalid in [
            '{"action":"run_shell","command":"rm -rf /"}',
            '{"action":"apply_patch","files":"file.py"}',
            '{"action":"apply_patch","files":["../../outside.py"]}',
            '{"action":"apply_patch","files":["tools/run_tests.py","tools/run_tests.py"]}',
            '{"action":"graphify","files":[]}',
            'not-json'
        ]:
            with self.subTest(invalid=invalid):
                act,files,error=m.parse_action(invalid)
                self.assertEqual(act,'error')
                self.assertEqual(files,[])
                self.assertIsNotNone(error)

    def test_bounded_graph_and_rg_search(self):
        task=m.P['tasks'][0]
        rg=m.rg_lookup(task['function'])
        graph=m.graph_lookup(task['function'],task['definition_file'])
        self.assertTrue(rg)
        self.assertTrue(set(rg)<=m.TRACKED)
        self.assertTrue(set(graph)<=m.TRACKED)

    def test_isolated_patch_does_not_modify_pinned_source(self):
        task=m.P['tasks'][0];f=task['definition_file']
        before=(m.ROOT/f).read_bytes();digest=hashlib.sha256(before).hexdigest()
        result=m.patch_and_test(task['function'],f,[])
        self.assertTrue(result['syntax_valid'],result['tool_error'])
        self.assertIn(f,result['edit_files'])
        self.assertEqual(hashlib.sha256((m.ROOT/f).read_bytes()).hexdigest(),digest)

    def test_source_paths_cannot_escape_or_modify_original(self):
        task=m.P['tasks'][0]
        _,_,e=m.parse_action('{"action":"apply_patch","files":["/etc/passwd"]}')
        self.assertIsNotNone(e)
        _,_,e=m.parse_action('{"action":"apply_patch","files":["../far/AGENTS.md"]}')
        self.assertIsNotNone(e)
if __name__=='__main__':unittest.main(verbosity=2)
