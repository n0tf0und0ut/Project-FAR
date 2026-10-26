"""Fail-closed compatibility for the observed completed/null Codex response.

These fixtures model independent GitHub API observations, not a fabricated
completed/false state. Unknown finding values must survive every passing path.
"""
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import pr_review_convergence as gate

HEAD = "ab12cd34ef" + "a" * 30
PREFIX = HEAD[:10]
PR = {"number": 578, "draft": False, "head": {"sha": HEAD},
      "base": {"sha": "b" * 40}, "user": {"login": "author", "type": "User"}}


def bot(body, ident, moment):
    return {"id": ident, "created_at": moment, "updated_at": moment,
            "user": {"login": "chatgpt-codex-connector[bot]", "type": "Bot"},
            "performed_via_github_app": {"id": 1144995, "slug": "chatgpt-codex-connector"},
            "body": body}


def summary(unresolved=None, status="completed", ident=10,
            moment="2026-10-23T20:53:22Z", sha=HEAD):
    state = {"code_review": {"commit_sha": sha, "has_any_findings": None,
                             "has_unresolved_findings": unresolved, "status": status}}
    return bot("<!-- codex-pull-request-review-summary -->\n"
               "<!-- codex-review-state:v1 " + json.dumps(state) + " -->", ident, moment)


# Exact observed authenticated bot boilerplate, not derived from the parser
# constant (so a parser change cannot silently move the test oracle).
CANONICAL_BOT_FOOTER = "<details> <summary>ℹ️ About Codex in GitHub</summary>\n<br/>\n\n[Your team has set up Codex to review pull requests in this repo](https://chatgpt.com/codex/cloud/settings/general). Reviews are triggered when you\n- Open a pull request for review\n- Mark a draft as ready\n- Comment \"@codex review\".\n\nIf Codex has suggestions, it will comment; otherwise it will react with 👍.\n\n\n\n\nCodex can also answer questions or update the PR. Try commenting \"@codex address that feedback\".\n            \n</details>"


def receipt(sha=PREFIX, ident=11, moment="2026-10-23T20:53:20Z"):
    return bot("<!-- codex-review-receipt:v1 -->\n\n"
               "Codex Review: Didn't find any major issues. Keep them coming!\n\n"
               "**Reviewed commit:** `" + sha + "`\n\n"
               + CANONICAL_BOT_FOOTER, ident, moment)


def evaluate(records=None, resolutions=None, **kwargs):
    return gate.evaluate(copy.deepcopy(PR), kwargs.get("reviews", []),
                         kwargs.get("threads", []), [], HEAD,
                         [summary(), receipt()] if records is None else records,
                         {PREFIX: HEAD} if resolutions is None else resolutions)


class ReceiptContractTests(unittest.TestCase):
    def test_real_completed_null_shape_qualifies_without_changing_unknown(self):
        record = evaluate()
        self.assertTrue(record["review_metadata_converged"])
        codex = record["trusted_codex_review_on_exact_head"]
        self.assertIsNone(codex["unresolved"])
        self.assertIsNone(codex["review_state_sources"][0]["has_unresolved_findings"])
        self.assertEqual(codex["completion_basis"], "authenticated_no_major_issues_receipt")
        self.assertEqual(codex["source_comment_id"], 10)
        self.assertEqual(codex["receipt_source"]["comment_id"], 11)
        self.assertEqual(codex["receipt_source"]["resolved_commit_sha"], HEAD)
        self.assertFalse(record["substantive_review_verified"])
        self.assertFalse(record["software_correctness_proven"])
        self.assertFalse(record["merge_authorization_verified"])

    def test_authenticated_cosmetic_completion_suffixes_with_exact_head(self):
        # All observed bot variants retain the same strict, authenticated,
        # contiguous exact-head completion declaration.
        for suffix in ("Keep them coming!", "Chef's kiss.", "Swish!",
                       "Nice work!", ":tada:"):
            record = receipt()
            record["body"] = record["body"].replace(
                "Keep them coming!", suffix)
            with self.subTest(suffix=suffix):
                result = evaluate([summary(), record])
                self.assertTrue(result["review_metadata_converged"])
                codex = result["trusted_codex_review_on_exact_head"]
                self.assertIsNone(codex["unresolved"])
                self.assertEqual(codex["receipt_source"]["comment_id"], 11)

    def test_unrecognized_or_semantically_negative_suffix_rejected(self):
        for suffix in (":bug:", "However, a critical bug remains.",
                       "No; there are unresolved findings.", "Nice work! NOTE"):
            record = receipt()
            record["body"] = record["body"].replace(
                "Keep them coming!", suffix)
            with self.subTest(suffix=suffix), self.assertRaises(gate.EvidenceError):
                evaluate([summary(), record])

    def test_unknown_or_contradictory_footer_content_never_qualifies(self):
        original = receipt()
        for body in (
            original["body"] + "\nHowever, a critical bug remains.\n<details>unrecognized trailer</details>",
            original["body"].replace("If Codex has suggestions", "However, a critical bug remains. If Codex has suggestions"),
            original["body"].replace("Codex can also answer questions", "Unknown message. Codex can also answer questions"),
            original["body"].replace("</details>", "</details>\n<details>Other</details>"),
            original["body"].replace("https://chatgpt.com/codex/cloud/settings/general",
                                     "https://attacker.example/review"),
        ):
            record = dict(original, body=body)
            with self.subTest(body=body[-110:]), self.assertRaises(gate.EvidenceError):
                evaluate([summary(), record])

    def test_null_without_receipt_still_fails_even_with_human_approval(self):
        review = {"id": 4, "state": "APPROVED", "commit_id": HEAD,
                  "submitted_at": "2026-10-23T21:00:00Z",
                  "user": {"login": "reviewer", "type": "User"}}
        with self.assertRaises(gate.EvidenceError):
            evaluate([summary()], reviews=[review])

    def test_each_origin_field_is_required_for_both_sources(self):
        for index in (0, 1):
            for field, replacement in (("login", "attacker"), ("type", "User"),
                                       ("id", 9), ("slug", "attacker"), ("id", True)):
                records = [summary(), receipt()]
                origin = records[index]["user" if field in ("login", "type")
                                        else "performed_via_github_app"]
                origin[field] = replacement
                with self.subTest(source=index, field=field, value=replacement):
                    try:
                        record = evaluate(records)
                    except gate.EvidenceError:
                        continue
                    self.assertFalse(record["review_metadata_converged"])

    def test_abbreviated_commit_requires_unambiguous_api_resolution(self):
        for resolutions in ({}, {PREFIX: "c" * 40}, {PREFIX: HEAD[:-1] + "b"}):
            with self.subTest(resolutions=resolutions), self.assertRaises(gate.EvidenceError):
                evaluate(resolutions=resolutions)

    def test_receipt_must_match_full_summary_head(self):
        for sha in ("c" * 10, HEAD[:-1] + "b"):
            with self.subTest(sha=sha), self.assertRaises(gate.EvidenceError):
                evaluate([summary(), receipt(sha=sha)])
        self.assertFalse(evaluate([summary(sha="c" * 40), receipt()])
                         ["review_metadata_converged"])

    def test_receipt_time_window_is_bounded_and_directional(self):
        for moment in ("2026-10-23T20:53:16Z", "2026-10-23T20:53:23Z",
                       "2026-10-20T20:53:20Z", "bad", "2026-10-23T20:53:20"):
            with self.subTest(moment=moment), self.assertRaises(gate.EvidenceError):
                evaluate([summary(), receipt(moment=moment)])

    def test_edited_receipt_and_duplicate_contemporaneous_receipts_reject(self):
        edited = receipt()
        edited["updated_at"] = "2026-10-23T20:53:21Z"
        for records in ([summary(), edited], [summary(), receipt(), receipt(ident=12)]):
            with self.assertRaises(gate.EvidenceError):
                evaluate(records)

    def test_quoted_negated_altered_or_ambiguous_receipt_is_not_a_verdict(self):
        original = receipt()
        variants = ["> " + original["body"], "Example:\n" + original["body"],
                    original["body"].replace("Didn't find", "Did find"),
                    original["body"].replace("Keep them coming!", "However, a critical bug remains."),
                    original["body"] + "\n" + original["body"],
                    original["body"].replace(PREFIX, PREFIX[:7]),
                    original["body"] + "\n**Reviewed commit:** `" + PREFIX + "`"]
        for body in variants:
            changed = dict(original, body=body)
            with self.subTest(body=body), self.assertRaises(gate.EvidenceError):
                evaluate([summary(), changed])

    def test_known_unresolved_findings_are_never_cleared_by_receipt(self):
        records = [summary(True, ident=8, moment="2026-10-23T20:00:00Z"),
                   summary(), receipt()]
        result = evaluate(records)
        self.assertFalse(result["review_metadata_converged"])
        self.assertTrue(result["trusted_codex_review_on_exact_head"]["unresolved"])
        result = evaluate([summary(True), receipt()])
        self.assertFalse(result["review_metadata_converged"])

    def test_running_and_failed_unresolved_flags_survive_later_null_receipt(self):
        for status in ("running", "failed"):
            prior = summary(True, status=status, ident=8, moment="2026-10-23T20:00:00Z")
            result = evaluate([prior, summary(), receipt()])
            with self.subTest(status=status):
                self.assertFalse(result["review_metadata_converged"])
                codex = result["trusted_codex_review_on_exact_head"]
                self.assertTrue(codex["unresolved"])
                self.assertFalse(codex["passed"])

    def test_intervening_explicit_completed_clean_state_clears_older_flags(self):
        for status in ("running", "failed", "completed"):
            prior = summary(True, status=status, ident=8, moment="2026-10-23T20:00:00Z")
            clean = summary(False, ident=9, moment="2026-10-23T20:30:00Z")
            result = evaluate([prior, clean, summary(), receipt()])
            with self.subTest(status=status):
                self.assertTrue(result["review_metadata_converged"])
                self.assertIsNone(result["trusted_codex_review_on_exact_head"]["unresolved"])

    def test_running_or_failed_review_blocks_receipt_and_prior_clean_state(self):
        for status in ("running", "failed"):
            result = evaluate([summary(False, ident=8, moment="2026-10-23T20:00:00Z"),
                               summary(status=status), receipt()])
            self.assertFalse(result["review_metadata_converged"])

    def test_threads_and_changes_requested_remain_independent_blockers(self):
        result = evaluate(threads=[{"id": "thread", "resolved": False, "outdated": True}])
        self.assertFalse(result["review_metadata_converged"])
        result = evaluate(reviews=[{"id": 4, "state": "CHANGES_REQUESTED",
                                   "user": {"login": "reviewer", "type": "User"}}])
        self.assertFalse(result["review_metadata_converged"])

    def test_duplicate_summary_keys_and_nonboolean_flags_reject(self):
        first = summary()
        bad = first["body"].replace('"status": "completed"',
                                    '"status": "running", "status": "completed"')
        for body in (bad, first["body"].replace('"has_unresolved_findings": null',
                                               '"has_unresolved_findings": 0')):
            with self.assertRaises(gate.EvidenceError):
                evaluate([dict(first, body=body), receipt()])

    def test_actual_cli_resolves_prefix_via_read_only_commit_endpoint(self):
        observed = []
        root = "https://api.github.com/repos/n0tf0und0ut/Project-FAR"

        def api(url, token, data=None):
            observed.append((url, data))
            self.assertEqual(token, "synthetic-read-only")
            if url == root + "/commits/" + PREFIX:
                return {"sha": HEAD}
            if url == root + "/pulls/578":
                return copy.deepcopy(PR)
            raise AssertionError(url)

        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "evidence.json"
            with patch.dict("os.environ", {"GH_TOKEN": "synthetic-read-only"}), \
                    patch.object(gate, "api", side_effect=api), \
                    patch.object(gate, "threads_for", return_value=[]), \
                    patch.object(gate, "paginate", side_effect=[[], [], [summary(), receipt()]]):
                result = gate.main(["--repository", "n0tf0und0ut/Project-FAR", "--pr", "578",
                                    "--expected-head", HEAD, "--output", str(output)])
            self.assertEqual(result, 0)
            self.assertTrue(json.loads(output.read_text())["review_metadata_converged"])
        self.assertEqual([url for url, _ in observed].count(root + "/commits/" + PREFIX), 1)
        self.assertTrue(all(data is None for _, data in observed))


if __name__ == "__main__":
    unittest.main()
