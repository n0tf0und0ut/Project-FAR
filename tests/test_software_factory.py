"""Deterministic controls for the software-factory operational prototype."""
import tempfile
import unittest
from pathlib import Path
from tools.software_factory import Factory, FactoryError, digest, validate_order

A = "a" * 40
B = "b" * 40


def order():
    return {"schema": "far-software-factory/work-order/1", "id": "pilot", "repository": "n0tf0und0ut/Project-FAR",
            "base_sha": A, "tasks": [
                {"id": "alpha", "objective": "Add tested software-factory controller", "acceptance": ["Tests catch stale evidence"], "depends_on": []},
                {"id": "beta", "objective": "Integrate controlled worker", "acceptance": ["Runner preserves gates"], "depends_on": ["alpha"]}]}


class TestFactory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.f = Factory(Path(self.tmp.name) / "factory.sqlite")
        self.f.submit(order())

    def test_order_validation_and_cycle(self):
        bad = order()
        bad["tasks"][0]["depends_on"] = ["beta"]
        with self.assertRaisesRegex(FactoryError, "cyclic"):
            validate_order(bad)
        bad = order()
        bad["tasks"][0]["acceptance"] = []
        with self.assertRaisesRegex(FactoryError, "acceptance"):
            validate_order(bad)

    def test_idempotent_and_immutable(self):
        self.assertTrue(self.f.submit(order())["idempotent"])
        changed = order()
        changed["tasks"][0]["objective"] += "!"
        with self.assertRaisesRegex(FactoryError, "immutable"):
            self.f.submit(changed)

    def test_dependencies_and_stage_sequence(self):
        claim = self.f.claim("pilot", "builder", now=100)
        self.assertEqual((claim["task_id"], claim["stage"]), ("alpha", "build"))
        self.assertIsNone(self.f.claim("pilot", "other", now=101))
        self.assertEqual(self.f.record("pilot", "alpha", claim["token"],
                                       {"head_sha": B, "pr_number": 123, "branch": "test"}, now=102)["state"], "queued")
        testing = self.f.claim("pilot", "tester", now=103)
        self.assertEqual(testing["stage"], "test")
        with self.assertRaisesRegex(FactoryError, "exact head"):
            self.f.record("pilot", "alpha", testing["token"], {"head_sha": A, "checks": ["unit"], "result": "passed"}, now=104)
        self.f.record("pilot", "alpha", testing["token"], {"head_sha": B, "checks": ["unit"], "result": "passed"}, now=105)
        review = self.f.claim("pilot", "review-worker", now=106)
        with self.assertRaisesRegex(FactoryError, "independent"):
            self.f.record("pilot", "alpha", review["token"], {"head_sha": B, "reviewer": "review-worker",
                          "review_url": "https://github.com/x/y/pull/1", "result": "clean", "unresolved": 0}, now=107)
        self.f.record("pilot", "alpha", review["token"], {"head_sha": B, "reviewer": "other-reviewer",
                      "review_url": "https://github.com/x/y/pull/1", "result": "clean", "unresolved": 0}, now=108)
        self.assertEqual(self.f.snapshot("pilot")["tasks"][0]["state"], "awaiting_protected_merge")
        self.assertIsNone(self.f.claim("pilot", "builder", now=109))

    def test_stale_token_and_lease_expiration(self):
        c = self.f.claim("pilot", "builder", now=1, ttl=10)
        with self.assertRaisesRegex(FactoryError, "lease expired"):
            self.f.record("pilot", "alpha", c["token"], {"head_sha": B, "pr_number": 3, "branch": "x"}, now=11)
        retry = self.f.claim("pilot", "new", now=12)
        self.assertNotEqual(c["token"], retry["token"])
        with self.assertRaisesRegex(FactoryError, "stale"):
            self.f.record("pilot", "alpha", c["token"], {"head_sha": B, "pr_number": 3, "branch": "x"}, now=13)

    def test_failure_bounded_retry(self):
        for i in range(3):
            c = self.f.claim("pilot", "builder", now=i * 100)
            status = self.f.fail("pilot", "alpha", c["token"], "model failure", now=i * 100+1)
        self.assertEqual(status["state"], "failed")
        self.assertIsNone(self.f.claim("pilot", "builder", now=1000))

    def _get_reviewed(self):
        claim = self.f.claim("pilot", "builder", now=100)
        self.f.record("pilot", "alpha", claim["token"],
                      {"head_sha": B, "pr_number": 123, "branch": "test"}, now=101)
        claim = self.f.claim("pilot", "tester", now=102)
        self.f.record("pilot", "alpha", claim["token"],
                      {"head_sha": B, "checks": ["unit"], "result": "passed"}, now=103)
        return self.f.claim("pilot", "review", now=104)

    def test_builder_cannot_self_review_through_another_worker(self):
        review = self._get_reviewed()
        with self.assertRaisesRegex(FactoryError, "independent"):
            self.f.record("pilot", "alpha", review["token"], {"head_sha": B, "reviewer": "builder",
                          "review_url": "https://github.com/x/y/pull/1", "result": "clean", "unresolved": 0}, now=105)

    def test_reconcile_merge_an_releases_dependency(self):
        review = self._get_reviewed()
        self.f.record("pilot", "alpha", review["token"], {"head_sha": B, "reviewer": "another",
                      "review_url": "https://github.com/x/y/pull/1", "result": "clean", "unresolved": 0}, now=105)
        def github(url):
            if url.endswith("/pulls/123"):
                return {"state": "closed", "merged": True, "merged_at": "2026-11-09T00:00:00Z",
                        "head": {"sha": B}, "base": {"ref": "main", "repo": {"full_name": "n0tf0und0ut/Project-FAR"}},
                        "merge_commit_sha": A}
            if url.endswith("/branches/main"):
                return {"commit": {"sha": A}}
            if url.endswith(f"/compare/{A}...{A}"):
                return {"status": "identical"}
            raise ValueError("unexpected GitHub request")
        self.assertEqual(self.f.reconcile_delivery("pilot", "alpha", github)["state"], "delivered")
        self.assertEqual(self.f.claim("pilot", "builder", now=106)["task_id"], "beta")

    def test_forged_merged_pr_does_not_advance(self):
        review = self._get_reviewed()
        self.f.record("pilot", "alpha", review["token"], {"head_sha": B, "reviewer": "another",
                      "review_url": "https://github.com/x/y/pull/1", "result": "clean", "unresolved": 0}, now=105)
        def github(url):
            return {"state": "closed", "merged": True, "merged_at": "yes", "head": {"sha": A},
                    "base": {"ref": "main", "repo": {"full_name": "n0tf0und0ut/Project-FAR"}}, "merge_commit_sha": A}
        with self.assertRaisesRegex(FactoryError, "exact head"):
            self.f.reconcile_delivery("pilot", "alpha", github)
        self.assertEqual(self.f.snapshot("pilot")["tasks"][0]["state"], "awaiting_protected_merge")

    def test_nonancestor_merge_does_not_release_dependency(self):
        review = self._get_reviewed()
        self.f.record("pilot", "alpha", review["token"], {"head_sha": B, "reviewer": "another",
                      "review_url": "https://github.com/x/y/pull/1", "result": "clean", "unresolved": 0}, now=105)
        def github(url):
            if url.endswith("/pulls/123"):
                return {"state": "closed", "merged": True, "merged_at": "yes", "head": {"sha": B},
                        "base": {"ref": "main", "repo": {"full_name": "n0tf0und0ut/Project-FAR"}},
                        "merge_commit_sha": A}
            if url.endswith("/branches/main"):
                return {"commit": {"sha": B}}
            return {"status": "diverged"}
        with self.assertRaisesRegex(FactoryError, "ancestor"):
            self.f.reconcile_delivery("pilot", "alpha", github)
        self.assertIsNone(self.f.claim("pilot", "builder", now=106))

    def test_lease_exhaustion_is_bounded(self):
        for i in range(3):
            token = self.f.claim("pilot", "builder", now=i*100, ttl=1)["token"]
        self.assertIsNone(self.f.claim("pilot", "builder", now=300, ttl=1))
        self.assertEqual(self.f.snapshot("pilot")["tasks"][0]["state"], "failed")


    def test_record_rechecks_lease_expiry_after_waiting_for_sqlite_writer(self):
        import threading
        import time

        claim = self.f.claim("pilot", "builder", ttl=1)
        started = threading.Event()
        ready = threading.Event()
        errors = []
        def worker():
            connection = Factory(Path(self.tmp.name) / "factory.sqlite")
            ready.set()
            started.wait(timeout=5)
            try:
                connection.record("pilot", "alpha", claim["token"],
                                  {"head_sha": B, "pr_number": 123, "branch": "task"})
            except FactoryError as exc:
                errors.append(str(exc))
            finally:
                connection.db.close()
        thread = threading.Thread(target=worker)
        thread.start()
        self.assertTrue(ready.wait(timeout=5))
        self.f.db.execute("BEGIN IMMEDIATE")
        try:
            started.set()
            # Old code captures the timestamp outside the transaction and
            # incorrectly accepts the expired lease once BEGIN IMMEDIATE unblocks.
            time.sleep(max(0.0, claim["expires_at"] - time.time() + 0.3))
        finally:
            self.f.db.execute("ROLLBACK")
        thread.join(timeout=6)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, ["lease expired"])
        self.assertEqual(self.f.snapshot("pilot")["tasks"][0]["state"], "running")

    def test_reconcile_accepts_repository_case_only_but_rejects_other_repository(self):
        example = order()
        example["id"] = "mixedcase"
        example["repository"] = "N0TF0UND0UT/project-far"
        self.f.submit(example)
        claim = self.f.claim("mixedcase", "builder", now=100)
        self.f.record("mixedcase", "alpha", claim["token"],
                      {"head_sha": B, "pr_number": 123, "branch": "topic"}, now=101)
        claim = self.f.claim("mixedcase", "tester", now=102)
        self.f.record("mixedcase", "alpha", claim["token"],
                      {"head_sha": B, "checks": ["unit"], "result": "passed"}, now=103)
        claim = self.f.claim("mixedcase", "review", now=104)
        self.f.record("mixedcase", "alpha", claim["token"],
                      {"head_sha": B, "reviewer": "independent",
                       "review_url": "https://github.com/x/y/pull/123",
                       "result": "clean", "unresolved": 0}, now=105)
        observed_name = ["different/Project-FAR"]
        def github(url):
            if url.endswith("/pulls/123"):
                return {"state": "closed", "merged": True,
                        "merged_at": "2026-11-09T00:00:00Z",
                        "head": {"sha": B},
                        "base": {"ref": "main", "repo": {"full_name": observed_name[0]}},
                        "merge_commit_sha": A}
            if url.endswith("/branches/main"):
                return {"commit": {"sha": A}}
            if url.endswith(f"/compare/{A}...{A}"):
                return {"status": "identical"}
            raise AssertionError(url)
        with self.assertRaisesRegex(FactoryError, "intended main"):
            self.f.reconcile_delivery("mixedcase", "alpha", github)
        self.assertEqual(self.f.snapshot("mixedcase")["tasks"][0]["state"], "awaiting_protected_merge")
        observed_name[0] = "n0tf0und0ut/Project-FAR"
        self.assertEqual(self.f.reconcile_delivery("mixedcase", "alpha", github)["state"], "delivered")

    def test_bad_evidence_atomic(self):
        c = self.f.claim("pilot", "builder", now=0)
        before = self.f.snapshot("pilot")
        with self.assertRaises(FactoryError):
            self.f.record("pilot", "alpha", c["token"], {"head_sha": "bad"}, now=1)
        self.assertEqual(before, self.f.snapshot("pilot"))


    def test_reconcile_delivery_does_not_block_unrelated_worker_claim(self):
        """A slow GitHub observation must not hold SQLite's write transaction."""
        import threading

        review = self._get_reviewed()
        self.f.record("pilot", "alpha", review["token"],
                      {"head_sha": B, "reviewer": "external",
                       "review_url": "https://github.com/x/y/pull/123",
                       "result": "clean", "unresolved": 0}, now=105)
        independent = order()
        independent["id"] = "parallel"
        independent["tasks"] = [{"id": "solo", "objective": "Independent maintenance",
                                  "acceptance": ["Worker can claim"], "depends_on": []}]
        self.f.submit(independent)

        entered, release = threading.Event(), threading.Event()
        errors = []
        db_path = Path(self.tmp.name) / "factory.sqlite"

        def github(url):
            if url.endswith("/pulls/123"):
                entered.set()
                if not release.wait(timeout=5):
                    raise RuntimeError("test synchronization timed out")
                return {"state": "closed", "merged": True, "merged_at": "2026-11-09T00:00:00Z",
                        "head": {"sha": B},
                        "base": {"ref": "main", "repo": {"full_name": "n0tf0und0ut/Project-FAR"}},
                        "merge_commit_sha": A}
            if url.endswith("/branches/main"):
                return {"commit": {"sha": A}}
            if url.endswith(f"/compare/{A}...{A}"):
                return {"status": "identical"}
            raise AssertionError(url)

        def reconcile():
            worker = Factory(db_path)
            try:
                worker.reconcile_delivery("pilot", "alpha", fetch_json=github)
            except Exception as exc:
                errors.append(exc)
            finally:
                worker.db.close()

        thread = threading.Thread(target=reconcile)
        thread.start()
        try:
            self.assertTrue(entered.wait(timeout=5))
            self.f.db.execute("PRAGMA busy_timeout=200")
            claimed = self.f.claim("parallel", "other-builder", now=200)
            self.assertIsNotNone(claimed)
            self.assertEqual(claimed["task_id"], "solo")
        finally:
            release.set()
            thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(self.f.snapshot("pilot")["tasks"][0]["state"], "delivered")



if __name__ == "__main__":
    unittest.main()
