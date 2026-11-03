"""Non-scored adversarial tests of matched-parameter architecture replication."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import model_architecture_replication as rep
import model_architecture_search as old

try:
    import torch
except ImportError:
    torch = None



def toy():
    p=json.loads((Path(__file__).resolve().parents[1]/'research/model-architecture-search/protocol-v0.2.json').read_text())
    p.update(study_id='FAR-MAS-TEST-ONLY',lengths=[8,9],train_size=40,validation_size=20,test_size=30,steps_budgets=[2,3],seeds=[11,12,13,14,15],batch_size=8)
    p['acceptance'].update(primary_length=8,primary_steps=2)
    return p


class ReplicationTests(unittest.TestCase):
    @unittest.skipUnless(torch is not None, "optional PyTorch not installed")
    def test_capacity_is_actually_matched(self):
        p=toy()
        for length in (13,15,17):
            specs=rep.model_specs(p,length)
            ref=specs[0]['parameters']
            self.assertEqual([x['id'] for x in specs],list(rep.OPS))
            for x in specs:
                self.assertLess(abs(x['parameters']/ref-1),0.05)

    def test_protocol_fails_closed(self):
        p=toy()
        rep.protocol_check(p)
        for key,value in [('device','gpu'),('conditions',list(reversed(p['conditions']))),('lengths',[8,8]),
                          ('seeds',[11,12,13,14,14]),('train_size',True),('steps_budgets',[2,2])]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                rep.protocol_check({**p,key:value})

    def test_noncanonical_bits_rejected(self):
        self.assertEqual(rep.bitunpack(rep.bitpack([1,0,1]),3),[True,False,True])
        for value in ('ff','00ff','0z',''):
            with self.subTest(value=value),self.assertRaises(ValueError):
                rep.bitunpack(value,3)

    def completed(self,dir):
        p=toy()
        outfile=Path(dir)/'output.json'
        report=rep.run(p,outfile,rep.encode(p)+b'\n')
        journal=Path(str(outfile)+'.journal.jsonl').read_bytes()
        rep.validate_report(report,journal)
        return outfile,report,journal

    @unittest.skipUnless(torch is not None, "optional PyTorch not installed")
    def test_real_training_and_full_prediction_scoring(self):
        with tempfile.TemporaryDirectory() as d:
            outfile,report,journal=self.completed(d)
            self.assertEqual(len(report['records']),2*2*4*5)
            self.assertEqual(report['status'],'COMPLETE_RESEARCH_REPLICATION')
            rep.validate_report(report,journal,replay=True)
            with self.assertRaises(FileExistsError):
                rep.run(toy(),outfile,rep.encode(toy())+b'\n')

    @unittest.skipUnless(torch is not None, "optional PyTorch not installed")
    def test_regrading_detects_forged_prediction_metrics_and_source(self):
        with tempfile.TemporaryDirectory() as d:
            outfile,report,journal=self.completed(d)
            for case in ('bits','metrics','source','missing','journal'):
                modified=copy.deepcopy(report)
                if case=='bits':
                    modified['records'][0]['test']['predictions_bits']='ff'*4
                elif case=='metrics':
                    modified['records'][0]['test']['metrics']['by_task']['remember_first']['correct']=999
                elif case=='source':
                    modified['model_source_sha256']='deadbeef'*8
                elif case=='missing':
                    modified['records'].pop()
                else:
                    modified['journal_sha256']='abc'
                modified['report_sha256']=rep.sha(rep.encode({k:v for k,v in modified.items() if k!='report_sha256'}))
                with self.subTest(case=case),self.assertRaises(ValueError):
                    rep.validate_report(modified,journal)

    @unittest.skipUnless(torch is not None, "optional PyTorch not installed")
    def test_failure_is_permanently_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            p=toy()
            out=Path(d)/'failed.json'
            with mock.patch.object(rep,'fit',side_effect=RuntimeError('deliberate fault')):
                with self.assertRaisesRegex(RuntimeError,'deliberate fault'):
                    rep.run(p,out,rep.encode(p)+b'\n')
            failed=json.loads(Path(str(out)+'.failure.json').read_text())
            self.assertEqual(failed['status'],'FAILED_OR_INCOMPLETE')
            self.assertEqual(failed['completed'],[])
            self.assertFalse(out.exists())
            with self.assertRaises(FileExistsError):
                rep.run(p,out,rep.encode(p)+b'\n')

if __name__=='__main__':
    unittest.main()
