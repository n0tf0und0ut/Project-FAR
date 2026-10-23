"""Local follow-up to caption coverage: only the initial block is a header."""
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from acquire import parse_captions
from full_cli import verify_package, write_package
from workflow import investigate


class CaptionHeaderContextRegressions(unittest.TestCase):
    def test_header_keyword_is_a_valid_later_cue_identifier(self):
        captions = ('WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nFirst observation.\n\n'
                    'WEBVTT\n00:00:03.000 --> 00:00:04.000\nSecond observation.\n')
        self.assertEqual(len(parse_captions(captions)['cues']), 2)
        result = investigate({'source': {'kind': 'vtt', 'text': captions}})
        self.assertIn('Second observation.', result['bundle']['sources'][0]['text'])
        with tempfile.TemporaryDirectory() as folder:
            target = pathlib.Path(folder) / 'package'
            write_package(target, result)
            self.assertTrue(verify_package(target)['replay_match'])


if __name__ == '__main__':
    unittest.main()
