"""FAR-WORLD/0.1 bounded model-state, provenance, causality and hostile controls."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from mechanization.far_mechanization.world_model import WorldModel, WorldModelError, ORTHODOX

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/world-model/orthodox-example.json"


def sample():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


class WorldModelTests(unittest.TestCase):
    def setUp(self):
        self.doc = sample()

    def load(self, data=None):
        return WorldModel.from_dict(self.doc if data is None else data)

    def fails(self, mutate):
        doc = copy.deepcopy(self.doc)
        mutate(doc)
        with self.assertRaises(WorldModelError):
            self.load(doc)

    def test_world_model_runs_and_digest_is_stable(self):
        model = self.load()
        self.assertEqual(model.digest, self.load(model.to_dict()).digest)
        self.assertEqual(model.digest, hashlib.sha256(model._raw).hexdigest())
        self.assertEqual(len(model.to_dict()['sources']), 7)
        self.assertEqual(model.to_dict()['worldview_profile'], ORTHODOX)

    def test_christological_foundation_is_a_confessional_premise(self):
        model = self.load()
        axiom = model.foundational_confession()
        self.assertEqual(axiom['kind'], 'CONFESSIONAL_AXIOM')
        self.assertEqual(axiom['proposition_ref'], 'jesus-is-god')
        self.assertEqual(axiom['source_refs'], ['nicene-creed'])
        self.assertIn('NOT_EMPIRICALLY_PROVED', axiom['assurance'])
        state = model.derive(known_at='2026-10-27T23:00:00Z')
        self.assertEqual(state.status('jesus-is-god'), 'SUPPORTED')
        self.assertEqual(state.inspect('jesus-is-god')['supports']['positive']['assertions'], ['nicene-confession'])

    def test_christological_axiom_does_not_imply_unrelated_facts(self):
        doc = copy.deepcopy(self.doc)
        excluded = {'scriptural-reading', 'report-a', 'report-b', 'correction-b'}
        doc['assertions'] = [a for a in doc['assertions'] if a['id'] not in excluded]
        state = self.load(doc).derive(known_at='2026-10-29T23:00:00Z')
        self.assertEqual(state.status('jesus-is-god'), 'SUPPORTED')
        self.assertEqual(state.status('scriptural-prohibition'), 'UNKNOWN')
        self.assertEqual(state.status('false-witness-wrong'), 'UNKNOWN')
        self.assertEqual(state.status('lamp-on'), 'UNKNOWN')

    def test_explicit_foundation_required(self):
        self.fails(lambda d: d.pop('christological_foundation'))
        self.fails(lambda d: d['christological_foundation'].update(proposition_ref='lamp-on'))
        self.fails(lambda d: d['christological_foundation'].update(source_refs=['report-on']))
        self.fails(lambda d: d['christological_foundation'].update(source_refs=['exodus']))

    def test_logos_grounding_is_not_extra_formal_antecedent(self):
        model = self.load()
        founding = model.foundational_confession()
        relation = founding["ontological_grounding"]
        self.assertEqual(relation["relation"], "METAPHYSICAL_GROUNDING_NOT_ENTAILMENT")
        self.assertEqual(relation["realism"], "DISCOVERED_NOT_HUMAN_INVENTED")
        self.assertEqual(relation["source_refs"], ["orthodox-creation"])
        self.assertEqual(relation["claim_classification"]["mathematical_order"], "RESEARCH_EXTENSION")
        self.assertEqual(set(relation["targets"]),
                         {"logical_order", "mathematical_order", "created_intelligibility"})
        # An independent, sourced moral rule need not include the root as an
        # extraneous logical premise: ontology and entailment are different.
        rule = model.to_dict()["rules"][0]
        self.assertNotIn("jesus-is-god", [p["proposition_ref"] for p in rule["premises"]])
        state = model.derive(known_at="2026-10-29T23:00:00Z")
        self.assertEqual(state.status("false-witness-wrong"), "SUPPORTED")
        self.assertEqual(state.inspect("false-witness-wrong")["supports"]["positive"]["assertions"],
                         ["scriptural-reading"])

    def test_metaphysical_realism_contract_is_inspectable_not_empirical(self):
        self.fails(lambda d: d["christological_foundation"].pop("ontological_grounding"))
        self.fails(lambda d: d["christological_foundation"]["ontological_grounding"].update(
            relation="DEDUCTIVE_ENTAILMENT"))
        self.fails(lambda d: d["christological_foundation"]["ontological_grounding"].update(
            realism="HUMAN_INVENTED"))
        self.fails(lambda d: d["christological_foundation"]["ontological_grounding"].update(
            targets=["logical_order", "logical_order"]))
        self.assertNotIn("ontological_grounding", self.load().derive(
            known_at="2026-10-29T23:00:00Z").project("empirical")[0])

    def test_foundation_requires_positive_source_committed_confession(self):
        def remove_root(doc):
            doc['assertions'] = [a for a in doc['assertions'] if a['id'] != 'nicene-confession']
        self.fails(remove_root)

    def test_christological_root_is_not_revisable_inside_profile(self):
        def contradictory_root(doc):
            row = dict(doc['assertions'][0])
            row.update(id='deny-root', polarity=False, supersedes=None)
            doc['assertions'].append(row)
        self.fails(contradictory_root)

        def supersede_root(doc):
            row = dict(doc['assertions'][0])
            row.update(id='replace-root', recorded_at='2026-10-30T00:00:00Z',
                       supersedes='nicene-confession')
            doc['assertions'].append(row)
        self.fails(supersede_root)

    def test_empirical_projection_excludes_christological_premise(self):
        model = self.load()
        state = model.derive(known_at='2026-10-29T23:00:00Z')
        empirical = state.project('empirical')
        self.assertNotIn('jesus-is-god', {p['proposition_id'] for p in empirical})
        self.assertEqual([p['proposition_id'] for p in empirical], ['lamp-on'])

    def test_no_hindsight_leakage_and_four_valued_conflict(self):
        model = self.load()
        before = model.derive(known_at='2026-10-27T23:00:00Z')
        conflicted = model.derive(known_at='2026-10-28T23:00:00Z')
        corrected = model.derive(known_at='2026-10-29T23:00:00Z')
        self.assertEqual(before.status('lamp-on'), 'SUPPORTED')
        self.assertEqual(conflicted.status('lamp-on'), 'BOTH')
        self.assertEqual(corrected.status('lamp-on'), 'SUPPORTED')
        self.assertEqual(conflicted.inspect('lamp-on')['supports']['negative']['assertions'], ['report-b'])
        self.assertEqual(corrected.inspect('lamp-on')['supports']['negative']['assertions'], [])
        self.assertEqual(corrected.inspect('lamp-on')['supports']['positive']['assertions'], ['correction-b','report-a'])

    def test_bitemporal_cutoff_excludes_future_world_events(self):
        doc = copy.deepcopy(self.doc)
        doc['assertions'].append({'id':'future-fact','proposition_ref':'lamp-on','polarity':False,
             'source_refs':['report-off'],'valid_at':'2026-10-30T00:00:00Z',
             'recorded_at':'2026-10-30T00:00:00Z','supersedes':None})
        model = self.load(doc)
        self.assertEqual(model.derive(known_at='2026-10-31T00:00:00Z', valid_at='2026-10-29T00:00:00Z').status('lamp-on'), 'SUPPORTED')
        self.assertEqual(model.derive(known_at='2026-10-31T00:00:00Z').status('lamp-on'), 'BOTH')

    def test_default_moral_projection_preserves_internal_orthodox_basis(self):
        state = self.load().derive(known_at='2026-10-29T23:00:00Z')
        plain = state.project('moral')
        self.assertEqual(len(plain), 1)
        self.assertEqual(plain[0]['status'], 'SUPPORTED')
        self.assertNotIn('framework_id', plain[0])
        self.assertNotIn('supports', plain[0])
        biblical = state.project('biblical')
        self.assertEqual({x['domain'] for x in biblical}, {'normative','theological'})
        self.assertEqual(next(p for p in biblical if p['domain']=='normative')['framework_id'], ORTHODOX)
        audit = state.inspect('false-witness-wrong')
        self.assertEqual(audit['supports']['positive']['assertions'], ['scriptural-reading'])
        self.assertEqual(audit['supports']['positive']['rules'], ['orthodox-prohibition-to-norm'])
        self.assertEqual(audit['supports']['positive']['sources'], ['exodus'])

    def test_inspection_cannot_mutate_active_world_state(self):
        state = self.load().derive(known_at='2026-10-29T23:00:00Z')
        audit = state.inspect('false-witness-wrong')
        audit['proposition']['framework_id'] = None
        audit['supports']['positive']['rules'].clear()
        again = state.inspect('false-witness-wrong')
        self.assertEqual(again['proposition']['framework_id'], ORTHODOX)
        self.assertEqual(again['supports']['positive']['rules'], ['orthodox-prohibition-to-norm'])

    def test_empirical_projection_does_not_include_religious_conclusions(self):
        rows = self.load().derive(known_at='2026-10-29T23:00:00Z').project('empirical')
        self.assertEqual([r['proposition_id'] for r in rows], ['lamp-on'])
        self.assertNotIn('framework_id', rows[0])

    def test_unknown_and_negative_inferences_are_not_explosion(self):
        doc = copy.deepcopy(self.doc)
        doc['assertions'] = [x for x in doc['assertions'] if x['proposition_ref'] != 'lamp-on']
        state = self.load(doc).derive(known_at='2026-10-29T23:00:00Z')
        self.assertEqual(state.status('lamp-on'), 'UNKNOWN')
        self.assertEqual(state.status('false-witness-wrong'), 'SUPPORTED')
        self.assertRaises(WorldModelError, state.status, 'not-a-proposition')

    def test_zero_premise_rejected(self):
        self.fails(lambda d: d['rules'][0].update(premises=[]))

    def test_empirical_normative_type_separation(self):
        def mutation(d):
            d['rules'].append({'id':'bad','premises':[{'proposition_ref':'false-witness-wrong','polarity':True}],
                'conclusion':{'proposition_ref':'lamp-on','polarity':True},
                'framework_id':None, 'justification_refs':['report-on']})
        self.fails(mutation)

    def test_empirical_facts_cannot_create_moral_norms_without_normative_premise(self):
        def mutation(d):
            d['rules'][0]['premises'] = [{'proposition_ref':'lamp-on','polarity':True}]
        self.fails(mutation)

    def test_framework_cannot_be_stripped_from_normative_rule(self):
        self.fails(lambda d: d['rules'][0].update(framework_id=None))

    def test_no_unverified_biblical_axiom_source(self):
        self.fails(lambda d: d['assertions'][0].update(source_refs=['report-on']))

    def test_provenance_tampering_is_rejected(self):
        self.fails(lambda d: d['sources'][0].update(text='A different alleged verse'))

    def test_duplicate_json_keys_and_nonfinite_values_rejected(self):
        with self.assertRaises(WorldModelError):
            WorldModel.loads('{"format_version":"FAR-WORLD/0.1","format_version":"malicious"}')
        with self.assertRaises(WorldModelError):
            WorldModel.loads('{"x": NaN}')
        with self.assertRaises(WorldModelError):
            self.load(dict(self.doc, bogus=1.0))

    def test_temporal_revisions_must_be_ordered_and_unique(self):
        self.fails(lambda d: d['assertions'][-1].update(recorded_at='2026-10-27T00:00:00Z'))
        self.fails(lambda d: d['assertions'][-1].update(supersedes='scriptural-reading'))
        self.fails(lambda d: d['assertions'].append(dict(d['assertions'][-1], id='duplicate-successor')))

    def test_deduction_invariant_under_proposition_order(self):
        model = self.load()
        reversed_doc = copy.deepcopy(self.doc)
        reversed_doc['propositions'].reverse()
        for pid in ('lamp-on','false-witness-wrong','scriptural-prohibition'):
            self.assertEqual(model.derive(known_at='2026-10-28T23:00:00Z').status(pid),
                             self.load(reversed_doc).derive(known_at='2026-10-28T23:00:00Z').status(pid))

    def test_cycles_do_not_create_truth_from_empty_support(self):
        doc = copy.deepcopy(self.doc)
        doc['propositions'].append({'id':'other-norm','statement':'Some other normative proposition',
                                   'domain':'normative','framework_id':ORTHODOX})
        doc['rules'].append({'id':'norm-to-other','premises':[{'proposition_ref':'jesus-is-god','polarity':True},{'proposition_ref':'false-witness-wrong','polarity':True}],
                             'conclusion':{'proposition_ref':'other-norm','polarity':True},
                             'framework_id':ORTHODOX,'justification_refs':['exodus']})
        doc['rules'].append({'id':'other-to-norm','premises':[{'proposition_ref':'jesus-is-god','polarity':True},{'proposition_ref':'other-norm','polarity':True}],
                             'conclusion':{'proposition_ref':'false-witness-wrong','polarity':True},
                             'framework_id':ORTHODOX,'justification_refs':['exodus']})
        doc['assertions'] = [a for a in doc['assertions'] if a['id']!='scriptural-reading']
        state = self.load(doc).derive(known_at='2026-10-29T23:00:00Z')
        self.assertEqual(state.status('false-witness-wrong'), 'UNKNOWN')
        self.assertEqual(state.status('other-norm'), 'UNKNOWN')

    def test_causal_simulation_and_counterfactual(self):
        model = self.load()
        self.assertEqual(model.simulate('rain-to-wet-ground', context={'rain':False}), {'rain':False,'wet_ground':False})
        self.assertEqual(model.simulate('rain-to-wet-ground', context={'rain':True}), {'rain':True,'wet_ground':True})
        result = model.counterfactual('rain-to-wet-ground', context={'rain':False},interventions={'rain':True})
        self.assertEqual(result['changed_variables'], ['rain','wet_ground'])
        result = model.counterfactual('rain-to-wet-ground',context={'rain':True},interventions={'wet_ground':False})
        self.assertEqual(result['changed_variables'], ['wet_ground'])
        self.assertIn('MODEL_RELATIVE', result['assurance'])

    def test_invalid_causal_intervention_rejected(self):
        m = self.load()
        for args in ({'context':{}}, {'context':{'rain':1}}, {'context':{'unknown':True}},
                     {'context':{'rain':True},'interventions':{'bad':False}},
                     {'context':{'rain':True},'interventions':{'rain':False}}):
            with self.subTest(args=args), self.assertRaises(WorldModelError):
                m.simulate('rain-to-wet-ground', **args)

    def test_causal_cycle_rejected(self):
        self.fails(lambda d: d['causal_models'][0]['variables'][0].update(parents=['wet_ground'],table={'0':False,'1':True}))

    def test_causal_table_must_be_complete(self):
        self.fails(lambda d: d['causal_models'][0]['variables'][1].update(table={'0':False}))

    def test_no_unreferenced_or_unsupported_mechanism(self):
        self.fails(lambda d: d['causal_models'][0].update(source_refs=['exodus']))

    def test_query_api_fails_closed(self):
        state = self.load().derive(known_at='2026-10-29T23:00:00Z')
        with self.assertRaises(WorldModelError):
            state.project('fantasy')
        with self.assertRaises(WorldModelError):
            state.inspect('not-defined')

if __name__ == '__main__':
    unittest.main()
