"""Sixth-review boundaries: provider provenance, streamed JSON, caption times."""
import asyncio
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from acquire import AcquisitionError, parse_captions
from full_cli import verify_package, write_package
from proposals import heuristic_proposal
from workflow import investigate


class SixthReviewRegressions(unittest.TestCase):
    def test_supplied_provider_method_produces_replayable_network_disclosure(self):
        text = "The bounded source makes a claim."
        for method, network in [("model_proposed_unreviewed", True),
                                ("deterministic_sentence_candidate_v1", False)]:
            with self.subTest(method=method), tempfile.TemporaryDirectory() as folder:
                proposal = heuristic_proposal(text)
                proposal["method"] = method
                outcome = investigate({"source": {"kind": "text", "text": text},
                                       "proposal_mode": "supplied", "proposal": proposal})
                self.assertIs(outcome["manifest"]["network_used"], network)
                self.assertEqual(outcome["proposal"], proposal)
                root = pathlib.Path(folder) / "package"
                write_package(root, outcome)
                verify_package(root)

    def test_chunked_json_stops_consuming_at_the_byte_limit_and_recovers(self):
        from fastapi import HTTPException
        from starlette.requests import Request
        from webapp import analyze

        async def run():
            for length in (None, "1", "450000"):
                chunks = iter([b" " * 225000, b" " * 225001])
                consumed = []
                async def receive():
                    try:
                        chunk = next(chunks)
                    except StopIteration:
                        self.fail("read beyond the overflowing chunk")
                    consumed.append(len(chunk))
                    return {"type": "http.request", "body": chunk, "more_body": True}
                headers = [(b"content-type", b"application/json")]
                if length is not None:
                    headers.append((b"content-length", length.encode()))
                request = Request({"type": "http", "headers": headers}, receive)
                with self.subTest(content_length=length):
                    with self.assertRaises(HTTPException) as error:
                        await analyze(request)
                    self.assertEqual(error.exception.status_code, 413)
                    self.assertEqual(sum(consumed), 450001)
            payload = json.dumps({"source": {"kind": "text", "text": "A bounded claim."}}).encode()
            chunks = iter([payload[:10], payload[10:]])
            async def valid_receive():
                chunk = next(chunks)
                return {"type": "http.request", "body": chunk, "more_body": len(chunk) == 10}
            response = await analyze(Request({"type": "http", "headers": [
                (b"content-type", b"application/json")]}, valid_receive))
            self.assertEqual(response.status_code, 200)
        asyncio.run(run())

    def test_caption_two_component_and_hour_timestamps_preserve_anchors_and_replay(self):
        cases = [("WEBVTT\n\n00:01.000 --> 00:02.000\nA bounded claim.", "vtt", 1000, 2000),
                 ("WEBVTT\n\n01:02:03.000 --> 01:02:04.500\nA bounded claim.", "vtt", 3723000, 3724500),
                 ("1\n00:01:02,000 --> 00:01:03,000\nA bounded claim.", "srt", 62000, 63000)]
        for raw, kind, start, end in cases:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as folder:
                parsed = parse_captions(raw)
                cue = parsed["cues"][0]
                self.assertEqual((cue["start_ms"], cue["end_ms"]), (start, end))
                self.assertEqual(parsed["text"][cue["span"]["start"]:cue["span"]["end"]], cue["span"]["quote"])
                outcome = investigate({"source": {"kind": kind, "text": raw}})
                root = pathlib.Path(folder) / "package"
                write_package(root, outcome)
                verify_package(root)
        for time, end in (("00:60.000", "01:01.000"), ("60:00.000", "61:00.000"),
                          ("00:60:00.000", "01:00:01.000"), ("00:00:60.000", "00:01:01.000")):
            with self.subTest(invalid=time), self.assertRaises(AcquisitionError):
                parse_captions("WEBVTT\n\n" + time + " --> " + end + "\nA claim.")


if __name__ == "__main__":
    unittest.main()
