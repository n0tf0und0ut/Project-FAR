"""Defect-detecting tests for the Codex specialist adapters."""
import tempfile
import tomllib
import unittest
from pathlib import Path
from tools import check_codex_far_specialists as adapter

NAMES = (
    'far-canonical-source-resolver', 'far-claim-registry',
    'far-clean-room-auditor', 'far-contradiction-detector',
    'far-counterexample-hunter', 'far-discovery-engine',
    'far-embedding-tester', 'far-evidence-ledger', 'far-formalizer',
    'far-prior-art-adversary', 'far-project-state-manager',
    'far-research-orchestrator', 'far-research-quality-gate',
    'far-theory-auditor',
)


class CodexSpecialistTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in NAMES:
            src = self.root / '.claude/skills' / name / 'SKILL.md'
            src.parent.mkdir(parents=True, exist_ok=True)
            src.write_text(f'---\nname: {name}\ndescription: "Test {name}"\n---\n\nCanonical behavior.\n')
            skill = self.root / '.agents/skills' / name / 'SKILL.md'
            skill.parent.mkdir(parents=True, exist_ok=True)
            skill.write_text(adapter.render_skill(name, f'Test {name}'))
            agent = self.root / '.codex/agents' / f'{adapter.agent_id(name)}.toml'
            agent.parent.mkdir(parents=True, exist_ok=True)
            agent.write_text(adapter.render_agent(name, f'Test {name}'))

    def test_exact_14_adapters_pass_and_toml_parses(self):
        self.assertEqual(adapter.check(self.root), [])
        for name in NAMES:
            agent = self.root / '.codex/agents' / f'{adapter.agent_id(name)}.toml'
            config = tomllib.loads(agent.read_text())
            self.assertEqual(config['name'], adapter.agent_id(name))
            self.assertIn(f'.claude/skills/{name}/SKILL.md', config['developer_instructions'])

    def test_canonical_source_change_requires_adapter_sync(self):
        src = self.root / '.claude/skills' / NAMES[0] / 'SKILL.md'
        src.write_text(src.read_text().replace('Test far-', 'Changed far-'))
        errors = adapter.check(self.root)
        self.assertTrue(any('Codex adapter drift' in e for e in errors), errors)

    def test_modified_agent_cannot_drop_runtime_source_load(self):
        f = self.root / '.codex/agents' / f'{adapter.agent_id(NAMES[0])}.toml'
        f.write_text(f.read_text().replace('.claude/skills/', '.unknown/skills/'))
        self.assertTrue(any('Codex adapter drift' in e for e in adapter.check(self.root)))

    def test_missing_adapter_fails(self):
        (self.root / '.agents/skills' / NAMES[0] / 'SKILL.md').unlink()
        self.assertTrue(any('missing or symlinked Codex adapter' in e for e in adapter.check(self.root)))

    def test_stale_specialist_fails(self):
        (self.root / '.codex/agents/far_unknown.toml').write_text('')
        self.assertTrue(any('stale/unregistered FAR agent' in e for e in adapter.check(self.root)))

    def test_vendor_security_audit_is_not_counted(self):
        vendor = self.root / '.claude/skills/security-audit'
        vendor.mkdir()
        (vendor / 'SKILL.md').write_text('vendor')
        self.assertEqual(adapter.check(self.root), [])

    def test_rejects_symlinked_source(self):
        target = self.root / '.claude/skills' / NAMES[0] / 'SKILL.md'
        target.unlink()
        target.symlink_to(self.root / '.claude/skills' / NAMES[1] / 'SKILL.md')
        self.assertTrue(any('missing or symlinked canonical skill' in e for e in adapter.check(self.root)))

    def test_unsupported_source_name_fails(self):
        path = self.root / '.claude/skills/far-bad-name_'
        path.mkdir()
        self.assertTrue(any('unexpected specialist entry' in e for e in adapter.check(self.root)))

    def test_duplicate_metadata_fails(self):
        p = self.root / '.claude/skills' / NAMES[0] / 'SKILL.md'
        p.write_text(p.read_text().replace('---\n\n', 'name: override\n---\n\n', 1))
        self.assertTrue(any('invalid canonical metadata' in e for e in adapter.check(self.root)))


if __name__ == '__main__':
    unittest.main()
