from __future__ import annotations
import hashlib,re,unittest
from pathlib import Path
from tools import promote_living_research as p

ROOT=Path(__file__).resolve().parents[1]
SNAP=ROOT/'research/living/snapshot-authorizations-v1.0.json'
HEX64=re.compile(r'[0-9a-f]{64}')
SNAP_FIELDS={'candidate_id','candidate_sha256','source_key','disposition','review_basis','review_basis_sha256','review_record_sha256','authorization_status'}
PROP_FIELDS={'proposal_id','candidate_id','proposal_sha256','candidate_sha256','operations_sha256','lifecycle_stage','authorization_status','provenance_sha256'}

class PromotionAuthorizationRegistryTests(unittest.TestCase):
    def test_policy_keeps_control_plane_outside_automatic_payloads(self):
        policy=p.load(ROOT/p.POLICY)
        self.assertEqual('1.1',policy['schema_version'])
        self.assertTrue(policy['snapshot_requires_explicit_authorization'])
        self.assertEqual('research/living/snapshot-authorizations-v1.0.json',policy['snapshot_authorization_registry'])
        self.assertIn('docs/governance/',policy['canonical_forbidden_prefixes'])
        self.assertIn('research/living/',policy['canonical_forbidden_prefixes'])
        self.assertIn('research/living/snapshot-authorizations-v1.0.json',policy['protected_exact_paths'])
        for root in ('.github','tools','tests','validation','validation_bootstrap','far_validation'):
            self.assertNotIn(root,policy['canonical_write_roots'])
        for suffix in ('.py','.sh','.js','.ts','.exe'):
            self.assertNotIn(suffix,policy['canonical_write_extensions'])
        self.assertEqual({'docs/research/living-repository-status.md','research/living/repository-state-v1.0.json',
                          'research/corpus/synthesis-v1.0.json','docs/research/current-research-frontier.md'},
                         set(policy['trusted_generated_paths']))

    def test_snapshot_authorizations_are_exact_and_bound_to_review_and_basis(self):
        data=p.load(SNAP); self.assertEqual('1.1',data.get('schema_version')); self.assertEqual('FAR-LIVING-SNAPSHOT-AUTHORIZATIONS-001',data.get('program_id')); self.assertEqual('Research',data.get('authority'))
        rows=data.get('authorizations'); self.assertIsInstance(rows,list)
        review_data=p.load(ROOT/p.REVIEWS); reviews={r['candidate_id']:r for r in review_data['reviewed_candidates']}
        self.assertEqual(len(reviews),len(review_data['reviewed_candidates']))
        seen=set(); allowed=set(p.load(ROOT/p.POLICY)['snapshot_review_dispositions'])
        for row in rows:
            self.assertEqual(SNAP_FIELDS,set(row)); cid=row['candidate_id']; self.assertRegex(cid,p.CANDIDATE_RE); self.assertNotIn(cid,seen); seen.add(cid)
            self.assertEqual('ACCEPTED_FOR_MECHANICAL_SNAPSHOT',row['authorization_status']); self.assertIn(row['disposition'],allowed)
            for field in ('candidate_sha256','review_basis_sha256','review_record_sha256'): self.assertRegex(row[field],HEX64)
            review=reviews.get(cid); self.assertIsNotNone(review); self.assertEqual(review['source_key'],row['source_key']); self.assertEqual(review['disposition'],row['disposition']); self.assertEqual(review['review_basis'],row['review_basis'])
            self.assertEqual(p.canonical_json_sha(review),row['review_record_sha256'])
            basis=ROOT/p.safe(row['review_basis']); self.assertTrue(basis.is_file()); self.assertEqual(hashlib.sha256(basis.read_bytes()).hexdigest(),row['review_basis_sha256'])

    def test_canonical_proposal_authorizations_have_closed_schema(self):
        data=p.load(ROOT/p.AUTHS); self.assertEqual('1.1',data.get('schema_version')); self.assertEqual('FAR-LIVING-PROMOTION-AUTHORIZATIONS-001',data.get('program_id')); self.assertEqual('Research',data.get('authority'))
        rows=data.get('authorizations'); self.assertIsInstance(rows,list); seen=set()
        for row in rows:
            self.assertEqual(PROP_FIELDS,set(row)); pid=row['proposal_id']; self.assertRegex(pid,p.PROPOSAL_RE); self.assertNotIn(pid,seen); seen.add(pid); self.assertRegex(row['candidate_id'],p.CANDIDATE_RE)
            self.assertEqual('PROMOTION_PROPOSED',row['lifecycle_stage']); self.assertEqual(p.AUTH_STATUS,row['authorization_status'])
            for field in ('proposal_sha256','candidate_sha256','operations_sha256'): self.assertRegex(row[field],HEX64)
            prov=row['provenance_sha256']; self.assertEqual(set(p.PROV_KEYS),set(prov))
            for value in prov.values(): self.assertRegex(value,HEX64)

if __name__=='__main__': unittest.main()
