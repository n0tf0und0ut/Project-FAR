"""Cold integrity restoration of permanently retained MAS v0.2 evidence.

Standard-library only: must remain executable on FAR's core CI without torch.
"""
import base64
import hashlib
import io
import json
from pathlib import Path
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'research/model-architecture-search/replication-v0.2-evidence.zip.b64'
ZIP_DIGEST = '47b4d2acfe68d6fbe059f1043f55f71e79b72f48a3de3f01e7710ab82c5032ac'


def verify_archive(encoded):
    try:
        if any(c not in b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n' for c in encoded):
            raise ValueError('noncanonical base64 input')
        raw = base64.b64decode(encoded.replace(b'\n',b''), validate=True)
    except Exception as e:
        raise ValueError('invalid archive encoding') from e
    if hashlib.sha256(raw).hexdigest() != ZIP_DIGEST:
        raise ValueError('archive SHA-256 mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP member CRC failure')
        files = set(z.namelist())
        manifest = json.loads(z.read('manifest.json'))
        if files != set(manifest['contents']) | {'manifest.json'}:
            raise ValueError('archive contents mismatch')
        for name, props in manifest['contents'].items():
            data=z.read(name)
            if len(data) != props['bytes'] or hashlib.sha256(data).hexdigest()!=props['sha256']:
                raise ValueError('member content digest mismatch')
        for internal, external in [
            ('protocol-v0.2.json','research/model-architecture-search/protocol-v0.2.json'),
            ('model-source-v0.1.py','tools/model_architecture_search.py'),
            ('runner-v0.2.py','tools/model_architecture_replication.py')
        ]:
            if z.read(internal) != (ROOT/external).read_bytes():
                raise ValueError('frozen source differs from archived source')
        report=json.loads(z.read('report.json'))
        if report['report_sha256']!=hashlib.sha256(json.dumps({k:v for k,v in report.items() if k!='report_sha256'},sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest():
            raise ValueError('original report self-digest mismatch')
        if len(report['records'])!=80 or report['analysis']['predeclared_screen_passed'] is not False:
            raise ValueError('original negative result changed or dropped')
        if report['journal_sha256'] != hashlib.sha256(z.read('journal.jsonl')).hexdigest():
            raise ValueError('journal binding broken')
        if not z.read('full-pinned-replay-success.log').strip().endswith(b'80 records'):
            raise ValueError('expected original replay completion receipt missing')
        if b'exact deterministic training replay mismatch' not in z.read('preflight-unpinned-replay-failure.log'):
            raise ValueError('original failure history removed')
        return report


class EvidenceArchiveTests(unittest.TestCase):
    def test_cold_reconstruction_and_original_negative_result(self):
        report=verify_archive(PATH.read_bytes())
        self.assertEqual(report['study_id'],'FAR-MAS-MATCHED-002')
        self.assertEqual(len(report['records']),80)
        self.assertEqual(report['analysis']['positive_seed_count'],2)

    def test_single_byte_archive_mutation_is_detected(self):
        raw=bytearray(PATH.read_bytes())
        i=raw.index(b'UEsD')+8
        raw[i]=ord('A') if raw[i]!=ord('A') else ord('B')
        with self.assertRaises(ValueError):
            verify_archive(bytes(raw))


if __name__=='__main__':
    unittest.main()
