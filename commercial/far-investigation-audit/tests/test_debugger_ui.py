"""User-visible pasted and uploaded sources must use the same investigation engine."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from webapp import app


class DebuggerUIIntegration(unittest.TestCase):
    def test_pasted_and_uploaded_text_share_debugger_report(self):
        with TestClient(app) as client:
            text='Some birds are blue. Therefore all birds are blue.'
            paste=client.post('/api/investigate',json={'source':{'kind':'text','text':text},'debugger':True})
            upload=client.post('/api/upload',files={'file':('source.txt',text.encode(),'text/plain')})
            for response in (paste,upload):
                self.assertEqual(response.status_code,200,response.text)
                result=response.json()
                self.assertEqual(result.get('debugger',{}).get('schema'),'far-epistemic-debugger/1.0')
                self.assertIn('Epistemic debugger',result['report_md'])
                self.assertTrue(all(r['acceptance']=='NOT_ACCEPTED' for r in result['debugger']['readings']))
            self.assertEqual(paste.json()['debugger']['claims']['c1']['status'],upload.json()['debugger']['claims']['c1']['status'])

if __name__=='__main__':unittest.main()
