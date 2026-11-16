"""Tests of the evaluator only. Synthetic fixtures are not agent benchmark runs."""
import copy
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / 'benchmark/fpt_2025/tools.py'
spec = importlib.util.spec_from_file_location('fpt_tools', PATH)
fpt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fpt)

def fixture(qid='q', answerable=True):
    ids = [qid+':E1', qid+':E2'] if answerable else []
    case = {'id': qid, 'primary_category': 'multi_hop', 'answerable': answerable,
            'gold': [{'id': x} for x in ids], 'evidence_groups': [{'all_of': ids}] if ids else []}
    trace = {'query_id': qid, 'status': 'answered' if answerable else 'abstain',
             'answer': 'Synthetic evaluator fixture, not a model output.',
             'context_ids': ['c1','c2'], 'citations': ['c1','c2'] if ids else [],
             'events': [{'event': 'search'}], 'elapsed_ms': 12, 'cost_usd': 0}
    review = {'query_id': qid, 'reviewer': 'unit-test fixture', 'human_confirmed': True,
              'reason': 'Synthetic fixture validates aggregation only.', 'unsupported_claims': False,
              'answer_grade': 2 if ids else None, 'context_grade': 2 if ids else None,
              'abstention_correct': True if not ids else None,
              'retrieval_evidence_at_1': ids[:1], 'retrieval_evidence_at_3': ids,
              'context_evidence': ids,
              'citations': [{'id': 'c'+str(i), 'supports_answer': True, 'source_locatable': True,
                             'evidence_ids': [e]} for i,e in enumerate(ids,1)]}
    return case, trace, review

class FptBenchmarkTests(unittest.TestCase):
    def test_package_is_complete_and_frozen(self):
        result = fpt.validate()
        self.assertEqual((result['questions'],result['system_specifications']), (240,60))

    def test_safe_exact_arithmetic(self):
        self.assertEqual(fpt.arithmetic('13043632833797-1916998192442+105704809379'),11232339450734)
        self.assertEqual(fpt.arithmetic('0.1+0.2'),fpt.Fraction('0.3'))
        with self.assertRaises(ValueError): fpt.arithmetic('__import__("os")')

    def test_full_answer_passes(self):
        c,t,r=fixture(); result=fpt.score([c],[t],[r])
        self.assertEqual(result['strict_pass']['n'],1)
        self.assertEqual(result['tool_use_successful_runs']['n'],1)
        self.assertIsNone(result['bonus_awarded'])

    def test_partial_hop_is_hit_but_not_complete(self):
        c,t,r=fixture(); r['context_evidence']=r['context_evidence'][:1]
        r['retrieval_evidence_at_3']=r['retrieval_evidence_at_1']
        result=fpt.score([c],[t],[r])
        self.assertEqual(result['evidence_hit_at_3']['n'],1)
        self.assertEqual(result['full_evidence_at_3']['n'],0)
        self.assertEqual(result['context_evidence_rate']['n'],0)
        self.assertEqual(result['strict_pass']['n'],0)

    def test_alternative_complete_group(self):
        c,_,_=fixture(); c['evidence_groups']=[{'all_of':['q:E1']},{'all_of':['q:E2']}]
        self.assertTrue(fpt.complete(c,['q:E2']))
        self.assertFalse(fpt.complete(c,[]))

    def test_citation_outside_context_fails(self):
        c,t,r=fixture(); t['context_ids']=['c1']
        result=fpt.score([c],[t],[r])
        self.assertEqual(result['valid_citations']['n'],1)
        self.assertEqual(result['strict_pass']['n'],0)

    def test_wrong_semantics_or_unlocatable_source_fails(self):
        for field in ('supports_answer','source_locatable'):
            c,t,r=fixture(); r['citations'][0][field]=False
            self.assertEqual(fpt.score([c],[t],[r])['strict_pass']['n'],0)

    def test_one_citation_missing_hop_fails(self):
        c,t,r=fixture(); t['citations']=['c1']; r['citations']=r['citations'][:1]
        self.assertEqual(fpt.score([c],[t],[r])['strict_pass']['n'],0)

    def test_human_confirmation_required(self):
        c,t,r=fixture(); r['human_confirmed']=False
        result=fpt.score([c],[t],[r])
        self.assertEqual(result['unreviewed'],1)
        self.assertEqual(result['strict_pass']['n'],0)

    def test_missing_timeout_and_error_remain_in_denominator(self):
        cs=[];ts=[]
        for i,status in enumerate(('missing','timeout','error')):
            c,t,_=fixture(str(i)); cs.append(c)
            if status!='missing': t['status']=status;ts.append(t)
        result=fpt.score(cs,ts,[])
        self.assertEqual(result['strict_pass'],{'n':0,'N':3,'rate':0})
        self.assertEqual(result['cost_unknown_cases'],1)

    def test_abstention_must_not_hallucinate(self):
        c,t,r=fixture(answerable=False)
        self.assertEqual(fpt.score([c],[t],[r])['correct_abstention']['n'],1)
        r['unsupported_claims']=True
        self.assertEqual(fpt.score([c],[t],[r])['correct_abstention']['n'],0)

    def test_false_abstention_grade_zero(self):
        c,t,r=fixture(); t['status']='abstain'
        result=fpt.score([c],[t],[r])
        self.assertEqual(result['false_abstention']['n'],1)
        self.assertEqual(result['grounded_answer_normalized']['n'],0)

    def test_duplicate_and_unknown_ids_rejected(self):
        c,t,r=fixture()
        for traces,reviews in [([t,t],[r]),([t],[r,r]),([dict(t,query_id='other')],[r])]:
            with self.assertRaises(ValueError): fpt.score([c],traces,reviews)

    def test_bad_evidence_labels_rejected(self):
        c,t,r=fixture(); r['context_evidence']=['other:E1']
        with self.assertRaises(ValueError): fpt.score([c],[t],[r])

    def test_no_answerable_denominator_is_na(self):
        c,t,r=fixture(answerable=False)
        self.assertEqual(fpt.score([c],[t],[r])['hit_at_1'],{'n':0,'N':0,'rate':None})

    def test_90_percent_threshold_uses_full_70(self):
        rows=[fixture(str(i)) for i in range(70)]
        for count in (62,63):
            cs=[row[0] for row in rows]
            ts=[row[1] for row in rows[:count]]
            rs=[row[2] for row in rows[:count]]
            result=fpt.score(cs,ts,rs)
            self.assertEqual(result['strict_pass']['N'],70)
            self.assertEqual(result['meets_90_percent_numeric_threshold'],count==63)

    def test_unknown_cost_not_zero(self):
        c,t,r=fixture();t.pop('cost_usd');t.pop('elapsed_ms')
        result=fpt.score([c],[t],[r])
        self.assertEqual(result['cost_unknown_cases'],1)
        self.assertIsNone(result['latency_ms_median'])

    def test_empty_review_template_does_not_pass(self):
        c,t,_=fixture(); result=fpt.score([c],[t],fpt.review_template([c]))
        self.assertEqual(result['strict_pass']['n'],0)

if __name__=='__main__': unittest.main()
