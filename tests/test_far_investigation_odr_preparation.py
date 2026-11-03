"""Optional actual-graph conformance uses scripted fixtures, never efficacy data."""
import asyncio
import copy
import importlib
import importlib.util
import sys
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from tools.far_investigation_odr_preparation import (
    UPSTREAM_BLOBS, ScriptedPreparationModel, prepare_graph, read_tools, verify_upstream,
)

UPSTREAM = os.environ.get('FAR_ODR_UPSTREAM_DIR')
OPTIONAL = bool(UPSTREAM and importlib.util.find_spec('langgraph') and importlib.util.find_spec('langchain'))


class ODRPreparationBoundaryTests(unittest.TestCase):
    def test_live_model_is_rejected_before_optional_import_or_source_access(self):
        with self.assertRaisesRegex(ValueError, 'no live dispatch'):
            asyncio.run(prepare_graph('/nonexistent', None, object()))

    def test_missing_original_source_is_not_fabricated(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(OSError):
                verify_upstream(root)


@unittest.skipUnless(OPTIONAL, 'optional upstream graph checkout and preparation dependencies required')
class ActualUpstreamGraphTests(unittest.TestCase):
    def runtime(self):
        from tools.far_investigation_engine import Investigation
        from tools.far_investigation_retrieval import RetrievalPolicy
        from tests.test_far_investigation_engine import FixtureRetriever, QUESTION, URL_A
        return Investigation(QUESTION, RetrievalPolicy(('example.org',)), mode='deterministic',
                             seeds=[URL_A], fetcher=FixtureRetriever())

    def script(self):
        from tests.test_far_investigation_engine import URL_A
        return [
            {'research_brief': 'SCRIPTED FIXTURE: retain source observation; no efficacy claim.'},
            {'content': '', 'tool_calls': [{'name': 'ConductResearch', 'args': {'research_topic': 'Fixture source'}, 'id': 'delegate1'}]},
            {'content': '', 'tool_calls': [{'name': 'retrieve', 'args': {'url': URL_A}, 'id': 'read1'}]},
            {'content': '', 'tool_calls': [{'name': 'ResearchComplete', 'args': {}, 'id': 'complete1'}]},
            {'content': 'SCRIPTED FIXTURE research notes.'},
            {'content': '', 'tool_calls': [{'name': 'ResearchComplete', 'args': {}, 'id': 'complete2'}]},
            {'content': 'SCRIPTED FIXTURE final report; not an empirical observation.'},
        ]

    def test_actual_pinned_graph_executes_adapted_read_tool_without_network(self):
        runtime = self.runtime()
        model = ScriptedPreparationModel(self.script())
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('network forbidden in preparation')):
            result = asyncio.run(prepare_graph(UPSTREAM, runtime, model))
        self.assertEqual(result['status'], 'SCRIPTED_PREPARATION_ONLY')
        self.assertEqual(result['live_model_calls'], 0)
        self.assertIsNone(result['performance_estimate'])
        self.assertIn('SCRIPTED FIXTURE', result['graph_return']['final_report'])
        self.assertEqual(len(model.calls), 7)
        self.assertEqual(len(runtime.state['sources']), 1)
        self.assertEqual(runtime.state['http_calls'], 1)
        self.assertTrue(any(e['kind'] == 'TOOL_RESULT' and e['payload']['tool'] == 'retrieve'
                            for e in runtime.state['events']))
        self.assertIn('retrieve', next(c for c in model.calls if 'retrieve' in c['bound_tools'])['bound_tools'])
        self.assertEqual(set(result['upstream']['git_blobs']), set(UPSTREAM_BLOBS))

    def test_adapter_uses_existing_tool_rejection_and_restores_native_bindings(self):
        with patch.object(sys, 'path', [str(Path(UPSTREAM)/'src'), *sys.path]):
            module=importlib.import_module('open_deep_research.deep_researcher')
        original_model, original_tools = module.configurable_model, module.get_all_tools
        runtime = self.runtime()
        script = self.script()
        script[2]['tool_calls'][0]['args']['url'] = 'https://unknown.example/source'
        asyncio.run(prepare_graph(UPSTREAM, runtime, ScriptedPreparationModel(script)))
        self.assertEqual(runtime.state['rejected_calls'], 1)
        self.assertEqual(runtime.state['sources'], {})
        self.assertIs(module.configurable_model, original_model)
        self.assertIs(module.get_all_tools, original_tools)

    def test_failed_graph_restores_native_bindings_and_preserves_failed_fixture_call(self):
        with patch.object(sys, 'path', [str(Path(UPSTREAM)/'src'), *sys.path]):
            module=importlib.import_module('open_deep_research.deep_researcher')
        original_model, original_tools = module.configurable_model, module.get_all_tools
        model=ScriptedPreparationModel([])
        with self.assertRaisesRegex(ValueError,'exhausted'):
            asyncio.run(prepare_graph(UPSTREAM,self.runtime(),model))
        self.assertEqual(model.calls[0]['error'],'SCRIPT_EXHAUSTED')
        self.assertIs(module.configurable_model,original_model)
        self.assertIs(module.get_all_tools,original_tools)

    def test_mutated_upstream_program_fails_source_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary)/'src/open_deep_research'
            package.mkdir(parents=True)
            (package/'configuration.py').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'source drift'):
                verify_upstream(temporary)

    def test_only_read_operations_are_exposed_and_policy_cannot_be_supplied(self):
        tools = read_tools(self.runtime())
        self.assertEqual([t.name for t in tools], ['retrieve', 'search'])
        self.assertNotIn('policy', tools[0].args)
        self.assertNotIn('shell', [t.name for t in tools])


if __name__ == '__main__':
    unittest.main()
