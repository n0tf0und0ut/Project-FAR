import builtins
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fargraph.core import MAX_SOURCE_BYTES, PythonVisitor, build, git_changed_files
from fargraph.mcp import Server


class RepoFixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.write('pkg/__init__.py','')
        self.write('pkg/base.py', '''def leaf():\n    return 1\n\ndef middle():\n    return leaf()\n\nclass C:\n    def action(self):\n        return self.helper()\n    def helper(self):\n        return middle()\n''')
        self.write('pkg/use.py','from pkg import base\n\ndef outer():\n    return base.middle()\n')
        self.write('docs/start.md','Read [the spec](../spec/contract.md#section) and [missing](../missing.md).\n')
        self.write('docs/home.md','Read [start](start.md) or [root](/README.md).\n')
        self.write('spec/contract.md','# Contract\n')
        self.write('README.md','# Repo\n')
        self.write('Lean/Alpha.lean','def x : Nat := 3\n')
        self.write('Lean/Beta.lean','import Lean.Alpha\nimport Mathlib.Data.Nat.Basic\n')
        self.write('.github/actions/demo/action.yml','name: demo\n')
        self.write('.github/workflows/ci.yml','jobs:\n  build:\n    steps:\n      - uses: ./.github/actions/demo\n      - uses: actions/checkout@v4\n')

    def write(self,path,content):
        dest=self.root/path
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(content)

    def test_inventory(self):
        g=build(self.root)
        self.assertEqual(len(g.hashes),11)
        self.assertEqual(g.stats()['schema'],'fargraph/0.1')

    def test_markdown_impact(self):
        g=build(self.root)
        result=g.impact(['spec/contract.md'])
        impacted={x['path'] for x in result['possibly_affected']}
        self.assertIn('docs/start.md',impacted)
        self.assertIn('docs/home.md',impacted)
        self.assertEqual(result['missing'],[])

    def test_invalid_markdown_link_preserves_other_link_evidence(self):
        self.write('docs/links.md', 'Broken [URL](https://[broken)\nSee [home](home.md).\n')
        graph = build(self.root)
        self.assertTrue(any(
            item['kind'] == 'invalid_link' and item['path'] == 'docs/links.md' and item['line'] == 1
            for item in graph.diagnostics
        ))
        self.assertTrue(any(
            edge.path == 'docs/links.md' and edge.target == 'file:docs/home.md' and edge.line == 2
            for edge in graph.edges
        ))

    def test_invalid_decoded_markdown_path_does_not_hide_valid_link(self):
        self.write('docs/links.md', 'Broken [path](broken%00.md)\nSee [home](home.md).\n')
        graph = build(self.root)
        self.assertIn(
            {'kind': 'invalid_link', 'path': 'docs/links.md', 'line': 1, 'detail': 'broken%00.md'},
            graph.diagnostics,
        )
        self.assertTrue(any(edge.path == 'docs/links.md' and edge.target == 'file:docs/home.md'
                            and edge.line == 2 for edge in graph.edges))

    def test_python_call_impact(self):
        g=build(self.root)
        result=g.impact(['pkg/base.py'])
        affected={a['path'] for a in result['possibly_affected']}
        self.assertIn('pkg/use.py',affected)
        self.assertGreaterEqual(len([e for e in g.edges if e.kind=='python_call']),2)

    def test_symbol_trace(self):
        g=build(self.root)
        start=next(n.id for n in g.nodes.values() if n.path=='pkg/base.py' and n.label=='middle')
        end=next(n.id for n in g.nodes.values() if n.path=='pkg/base.py' and n.label=='leaf')
        t=g.trace(start,end)
        self.assertTrue(t['found'])
        self.assertEqual(t['edges'][0]['certainty'],'syntactic_candidate')

    def test_lean_import(self):
        g=build(self.root)
        known=[e for e in g.edges if e.kind=='lean_import' and e.certainty=='resolved_path']
        self.assertEqual(len(known),1)
        self.assertEqual(known[0].target,'file:Lean/Alpha.lean')
        self.assertTrue(any(x['kind']=='unresolved_lean_import' for x in g.diagnostics))

    def test_workflow_local_action(self):
        g=build(self.root)
        uses=[e for e in g.edges if e.kind=='workflow_uses']
        self.assertEqual(len(uses),1)
        self.assertEqual(uses[0].target,'file:.github/actions/demo/action.yml')

    def test_missing_link_visible_not_safe(self):
        g=build(self.root)
        self.assertTrue(any(e.certainty=='unresolved' and e.kind=='markdown_link' for e in g.edges))
        result=g.impact(['docs/start.md'])
        self.assertIn('coverage_warning',result)

    def test_escape_rejected(self):
        g=build(self.root)
        with self.assertRaises(ValueError):g.impact(['../secret.env'])
        with self.assertRaises(ValueError):g.impact(['/etc/passwd'])

    def test_invalid_python_recorded(self):
        self.write('pkg/bad.py','def wrong(:\n')
        g=build(self.root)
        self.assertTrue(any(d['kind']=='python_syntax_error' and d['path']=='pkg/bad.py' for d in g.diagnostics))

    def test_python_analysis_depth_error_isolated_from_other_sources(self):
        self.write('limited.py', 'import pkg.base\n')
        original_run = PythonVisitor.run

        def run(visitor):
            original_run(visitor)
            if visitor.rel == 'limited.py':
                raise RecursionError('fixture analysis limit')

        with patch.object(PythonVisitor, 'run', run):
            graph = build(self.root)
        self.assertTrue(any(d['kind'] == 'python_ast_depth_limit' and d['path'] == 'limited.py'
                            for d in graph.diagnostics))
        self.assertFalse(any(edge.path == 'limited.py' for edge in graph.edges))
        self.assertTrue(any(edge.path == 'pkg/use.py' for edge in graph.edges))

    def test_python_package_precedes_same_named_module(self):
        self.write('pkg.py', 'value = 0\n')
        self.write('caller.py', 'import pkg\n')
        sources = frozenset({'pkg.py', 'pkg/__init__.py', 'caller.py'})
        for source_paths in (None, sources):
            with self.subTest(pinned=source_paths is not None):
                graph = build(self.root, source_paths=source_paths)
                targets = {edge.target for edge in graph.edges if edge.path == 'caller.py'}
                self.assertEqual(targets, {'file:pkg/__init__.py'})

    def test_equal_bytes_do_not_hide_retargeted_internal_symlink(self):
        self.write('a.py', 'value = 1\n')
        self.write('b.py', 'value = 1\n')
        self.write('caller.py', 'import alias\n')
        alias = self.root / 'alias.py'
        alias.symlink_to('a.py')
        graph = build(self.root)
        self.assertTrue(graph.freshness()['fresh'])
        alias.unlink()
        alias.symlink_to('b.py')
        self.assertEqual(graph.freshness()['changed_or_removed'], ['alias.py'])
        affected = build(self.root).impact(['b.py'])['possibly_affected']
        self.assertIn('caller.py', {entry['path'] for entry in affected})

    def test_dependency_lookup_detects_retargeted_directory_symlink(self):
        for package in ('first', 'second'):
            self.write(f'{package}/__init__.py', 'value = 1\n')
            self.write(f'{package}/README.md', '# Package\n')
        self.write('links.md', '[Guide](alias/README.md)\n[Package](alias/)\n')
        self.write('caller.py', 'import alias\n')
        alias = self.root / 'alias'
        alias.symlink_to('first', target_is_directory=True)
        graph = build(self.root)
        self.assertTrue(graph.freshness()['fresh'])
        self.assertEqual({edge.target for edge in graph.edges if edge.path == 'links.md'},
                         {'file:first/README.md'})
        self.assertEqual({edge.target for edge in graph.edges if edge.path == 'caller.py'},
                         {'file:first/__init__.py'})

        alias.unlink()
        alias.symlink_to('second', target_is_directory=True)
        self.assertFalse(graph.freshness()['fresh'])
        refreshed = build(self.root)
        self.assertEqual({edge.target for edge in refreshed.edges if edge.path == 'links.md'},
                         {'file:second/README.md'})
        self.assertEqual({edge.target for edge in refreshed.edges if edge.path == 'caller.py'},
                         {'file:second/__init__.py'})

    def test_nonregular_paths_are_excluded_before_opening_sources(self):
        self.write('placeholder.py', 'value = 1\n')
        placeholder = self.root / 'placeholder.py'
        alias = self.root / 'alias.py'
        alias.symlink_to(placeholder)
        original_stat = Path.stat

        def source_stat(path, *args, **kwargs):
            result = original_stat(path, *args, **kwargs)
            if path in (placeholder, alias) and kwargs.get('follow_symlinks', True):
                return os.stat_result((stat.S_IFDIR, *tuple(result)[1:]))
            return result

        def guard_open(path, *args, **kwargs):
            self.assertNotIn(path, (placeholder, alias))
            return builtins.open(path, *args, **kwargs)

        with (patch.object(Path, 'stat', source_stat),
              patch('fargraph.core.open', guard_open, create=True)):
            graph = build(self.root)
            self.assertTrue(graph.freshness()['fresh'])
        for path in ('placeholder.py', 'alias.py'):
            self.assertNotIn(path, graph.hashes)
            self.assertIn(path, {d['path'] for d in graph.diagnostics if d['kind'] == 'unreadable'})

    def test_determinism(self):
        g1=build(self.root).to_dict()
        g2=build(self.root).to_dict()
        self.assertEqual(json.dumps(g1,sort_keys=True),json.dumps(g2,sort_keys=True))

    def test_hash_change(self):
        g1=build(self.root)
        self.write('spec/contract.md','# Contract revised\n')
        g2=build(self.root)
        self.assertNotEqual(g1.hashes['spec/contract.md'],g2.hashes['spec/contract.md'])

    def test_no_tree_mutation(self):
        before=sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        build(self.root)
        after=sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        self.assertEqual(before,after)

    def test_mcp_tooling(self):
        s=Server(str(self.root))
        result=s.handle({'jsonrpc':'2.0','id':1,'method':'tools/list'})
        self.assertEqual(len(result['result']['tools']),5)
        result=s.handle({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'fargraph_impact','arguments':{'files':['pkg/base.py']}}})
        self.assertFalse(result['result']['isError'])
        self.assertIn('pkg/use.py',result['result']['content'][0]['text'])

    def test_mcp_security(self):
        s=Server(str(self.root))
        result=s.handle({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'fargraph_impact','arguments':{'files':['../../etc/shadow']}}})
        self.assertTrue(result['result']['isError'])

    def test_missing_changed_path(self):
        g=build(self.root)
        r=g.impact(['this-does-not-exist.md'])
        self.assertEqual(r['missing'],['this-does-not-exist.md'])

    def test_max_depth(self):
        g=build(self.root)
        a=g.impact(['spec/contract.md'],max_depth=1)
        b=g.impact(['spec/contract.md'],max_depth=6)
        self.assertLessEqual(len(a['possibly_affected']),len(b['possibly_affected']))

    def test_unsafe_symlink_excluded(self):
        external=Path(self.temp.name).parent/('fargraph-outside-'+self.root.name+'.md')
        external.write_text('private')
        self.addCleanup(lambda:external.unlink(missing_ok=True))
        (self.root/'docs/unsafe.md').symlink_to(external)
        g=build(self.root)
        self.assertNotIn('docs/unsafe.md',g.hashes)

    def test_stale_mcp_fails_closed(self):
        s=Server(str(self.root))
        self.write('spec/contract.md','# altered')
        status=s.handle({'jsonrpc':'2.0','id':11,'method':'tools/call','params':{'name':'fargraph_status','arguments':{}}})
        self.assertIn('false',status['result']['content'][0]['text'])
        result=s.handle({'jsonrpc':'2.0','id':12,'method':'tools/call','params':{'name':'fargraph_impact','arguments':{'files':['pkg/base.py']}}})
        self.assertTrue(result['result']['isError'])

    def test_new_file_detected(self):
        g=build(self.root)
        self.write('new.py','print(1)')
        state=g.freshness()
        self.assertFalse(state['fresh'])
        self.assertEqual(state['new_files'],['new.py'])

    def test_freshness_on_unchanged_repo(self):
        g=build(self.root)
        self.assertTrue(g.freshness()['fresh'])

    def test_mcp_requires_refresh_when_excluded_source_becomes_indexable(self):
        content = b'import pkg.base\n'
        caller = self.root / 'caller.py'
        for excluded in (b'\xff' * len(content), b'x' * (MAX_SOURCE_BYTES + 1)):
            with self.subTest(size=len(excluded)):
                caller.write_bytes(excluded)
                server = Server(str(self.root))
                self.assertTrue(server.graph.freshness()['fresh'])
                caller.write_bytes(content)
                state = server.graph.freshness()
                self.assertFalse(state['fresh'])
                self.assertIn('caller.py', state['changed_or_removed'])
                request = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                           'params': {'name': 'fargraph_impact', 'arguments': {'files': ['pkg/base.py']}}}
                self.assertTrue(server.handle(request)['result']['isError'])
                refresh = {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                           'params': {'name': 'fargraph_refresh', 'arguments': {}}}
                self.assertFalse(server.handle(refresh)['result']['isError'])
                result = server.handle(request)['result']
                self.assertFalse(result['isError'])
                self.assertIn('caller.py', [x['path'] for x in
                              json.loads(result['content'][0]['text'])['possibly_affected']])

    def test_file_read_failure_then_recovery_or_removal_invalidates_index(self):
        caller = self.root / 'caller.py'
        caller.write_text('import pkg.base\n')
        original_open = builtins.open

        def open_source(path, *args, **kwargs):
            if path == caller:
                raise PermissionError('fixture denied')
            return original_open(path, *args, **kwargs)

        with patch('fargraph.core.open', open_source, create=True):
            graph = build(self.root)
            self.assertTrue(graph.freshness()['fresh'])
        self.assertEqual(graph.freshness()['changed_or_removed'], ['caller.py'])
        caller.unlink()
        self.assertEqual(graph.freshness()['changed_or_removed'], ['caller.py'])

    def test_relative_imports(self):
        self.write('pkg/relative.py','from . import base\nfrom .base import middle\n')
        g=build(self.root)
        local=[e.target for e in g.edges if e.kind=='python_import' and e.source=='file:pkg/relative.py']
        self.assertIn('file:pkg/base.py',local)

    def test_self_calls_stay_syntactic(self):
        g=build(self.root)
        action=next(n.id for n in g.nodes.values() if n.label=='C.action')
        helper=next(n.id for n in g.nodes.values() if n.label=='C.helper')
        t=g.trace(action,helper)
        self.assertTrue(t['found'])
        self.assertEqual(t['edges'][0]['certainty'],'syntactic_candidate')

    def test_source_not_executed(self):
        self.write('evil.py', 'raise RuntimeError("DO NOT RUN ME")\n')
        g=build(self.root)
        self.assertIn('evil.py',g.hashes)

    def test_mcp_real_stdio(self):
        messages=[
            {'jsonrpc':'2.0','id':1,'method':'initialize',
             'params':{'protocolVersion':'2026-07-28','capabilities':{},
                       'clientInfo':{'name':'test','version':'1'}}},
            {'jsonrpc':'2.0','method':'notifications/initialized'},
            {'jsonrpc':'2.0','id':2,'method':'tools/list'},
            {'jsonrpc':'2.0','id':3,'method':'tools/call',
             'params':{'name':'fargraph_status','arguments':{}}},
        ]
        result=subprocess.run([sys.executable,'-m','fargraph.mcp','--root',str(self.root)],
              input='\n'.join(json.dumps(m) for m in messages)+'\n',
              stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        replies=[json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(replies),3)
        self.assertEqual(replies[0]['result']['protocolVersion'],'2025-11-25')
        self.assertEqual(len(replies[1]['result']['tools']),5)
        self.assertIn('"fresh": true',replies[2]['result']['content'][0]['text'])

    def test_git_diff_changed_files(self):
        def git(*args):
            return subprocess.run(['git','-C',str(self.root),*args],check=True,
                    text=True,capture_output=True).stdout.strip()
        git('init','-q')
        git('config','user.email','fargraph-test@example.invalid')
        git('config','user.name','Fargraph Test')
        git('add','.')
        git('commit','-qm','initial')
        base=git('rev-parse','HEAD')
        self.write('pkg/base.py','def leaf():\n    return 99\n')
        git('add','pkg/base.py')
        git('commit','-qm','modified')
        self.assertEqual(git_changed_files(self.root,base),['pkg/base.py'])

    def test_excluded_external_symlink_remains_fresh_and_target_mutation_invalidates(self):
        external=Path(self.temp.name).parent/('fargraph-link-one-'+self.root.name+'.md')
        external.write_text('outside one')
        other=Path(self.temp.name).parent/('fargraph-link-two-'+self.root.name+'.md')
        other.write_text('outside two')
        self.addCleanup(lambda:external.unlink(missing_ok=True))
        self.addCleanup(lambda:other.unlink(missing_ok=True))
        link=self.root/'docs/unsafe.md'
        link.symlink_to(external)
        g=build(self.root)
        self.assertTrue(g.freshness()['fresh'])
        self.assertNotIn('docs/unsafe.md',g.hashes)
        link.unlink()
        link.symlink_to(other)
        state=g.freshness()
        self.assertFalse(state['fresh'])
        self.assertIn('docs/unsafe.md',state['changed_or_removed'])

    def test_oversized_source_is_rejected_without_unbounded_read(self):
        big=self.root/'oversize.py'
        with big.open('wb') as stream:
            stream.truncate(64 * 1024 * 1024)
        g=build(self.root)
        self.assertNotIn('oversize.py',g.hashes)
        self.assertIn('oversize.py', [d['path'] for d in g.diagnostics
                                     if d['kind']=='skipped_large_file'])
        self.assertTrue(g.freshness()['fresh'])

    def test_git_changed_files_preserves_unicode_and_deleted_paths(self):
        def git(*args):
            return subprocess.run(['git','-C',str(self.root),*args],
                                  check=True,text=True,capture_output=True).stdout.strip()
        git('init','-q')
        git('config','user.email','fargraph-test@example.invalid')
        git('config','user.name','Fargraph Test')
        self.write('café.py','value = 1\n')
        git('add','.')
        git('commit','-qm','base')
        base=git('rev-parse','HEAD')
        self.write('café.py','value = 2\n')
        git('add','café.py')
        git('commit','-qm','change')
        self.assertEqual(git_changed_files(self.root,base),['café.py'])
        git('rm','café.py')
        git('commit','-qm','delete')
        self.assertEqual(git_changed_files(self.root,base,diff_filter='D'),['café.py'])

    def test_mcp_malformed_parameter_objects_do_not_crash_stdio(self):
        s=Server(str(self.root))
        bad={'jsonrpc':'2.0','id':11,'method':'tools/call',
             'params':['unexpected']}
        invalid=s.handle(bad)
        self.assertEqual(invalid['error']['code'],-32602)
        other=s.handle({'jsonrpc':'2.0','id':12,'method':'tools/call',
                        'params':{'name':'fargraph_impact','arguments':['wrong']}})
        self.assertEqual(other['error']['code'],-32602)
        self.assertEqual(s.handle({'jsonrpc':'2.0','id':13,'method':'ping'})['result'],{})
        messages=[bad,{'jsonrpc':'2.0','id':14,'method':'ping'}]
        proc=subprocess.run([sys.executable,'-m','fargraph.mcp','--root',str(self.root)],
                            input='\n'.join(json.dumps(m) for m in messages)+'\n',
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=10)
        self.assertEqual(proc.returncode,0,proc.stderr)
        replies=[json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual([x['id'] for x in replies],[11,14])
        self.assertEqual(replies[0]['error']['code'],-32602)
        self.assertEqual(replies[1]['result'],{})

    def test_mcp_refresh(self):
        s=Server(str(self.root))
        prior=s.graph.hashes['README.md']
        self.write('README.md','# updated')
        s.handle({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'fargraph_refresh','arguments':{}}})
        self.assertNotEqual(prior,s.graph.hashes['README.md'])

if __name__=='__main__':unittest.main()
