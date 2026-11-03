"""Mutations of retained model traces; zero new inference observations."""
import copy
import json
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

from tools import check_weight_space_publication as audit


class PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = audit.read(audit.DEFAULT)
        with zipfile.ZipFile(audit.ROOT / cls.manifest["archive"]["path"]) as z:
            cls.members = {name: z.read(name) for name in z.namelist()}

    def altered(self, mutate, *, duplicate=False, refresh=True):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        manifest = copy.deepcopy(self.manifest)
        members = dict(self.members)
        mutate(members)
        if refresh:
            inner = {k: v for k, v in manifest.items() if k != "archive"}
            inner["files"] = [{"path": name, "size": len(data), "sha256": audit.sha(data)}
                              for name, data in sorted(members.items()) if name != "manifest.json"]
            members["manifest.json"] = audit.canonical(inner)
            manifest = dict(inner, archive=manifest["archive"])
        archive = root / "evidence.zip"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
                for name, data in members.items():
                    z.writestr(name, data)
                if duplicate:
                    z.writestr("attempt/slot-0000.json", members["attempt/slot-0000.json"])
        manifest["archive"] = {"path": str(archive), "size": archive.stat().st_size,
                               "sha256": audit.sha(archive.read_bytes()),
                               "members": len(members) + int(duplicate)}
        path = root / "smol135m-v01-manifest.json"
        path.write_bytes(audit.canonical(manifest))
        (root / "smol135m-v01-analysis.json").write_bytes(
            (audit.DEFAULT.parent / "smol135m-v01-analysis.json").read_bytes())
        return path

    @staticmethod
    def edit_json(members, name, edit):
        value = json.loads(members[name])
        edit(value)
        members[name] = audit.canonical(value)

    def test_retained_actual_archive_reconstructs(self):
        result = audit.check()
        self.assertEqual(result["scored_records_regraded"], 432)
        self.assertEqual(result["new_model_observations"], 0)
        self.assertFalse(result["production_eligible"])

    def test_corrupted_member_rejected(self):
        path = self.altered(lambda m: m.__setitem__("attempt/slot-0000.json", b"{}"), refresh=False)
        with self.assertRaisesRegex(ValueError, "member bytes"):
            audit.check(path)

    def test_missing_slot_rejected_after_rehash(self):
        path = self.altered(lambda m: m.pop("attempt/slot-0000.json"))
        with self.assertRaisesRegex(ValueError, "scored slots"):
            audit.check(path)

    def test_duplicate_members_rejected(self):
        path = self.altered(lambda _: None, duplicate=True)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit.check(path)

    def test_unsafe_member_rejected(self):
        path = self.altered(lambda m: m.__setitem__("../outside.json", b"{}"))
        with self.assertRaisesRegex(ValueError, "noncanonical"):
            audit.check(path)

    def test_forged_grade_rejected_after_rehash(self):
        def mutate(members):
            self.edit_json(members, "attempt/slot-0000.json",
                           lambda r: r["grade"].__setitem__("correct", not r["grade"]["correct"]))
        with self.assertRaisesRegex(ValueError, "grade differs"):
            audit.check(self.altered(mutate))

    def test_fabricated_source_rejected_after_rehash(self):
        def mutate(members):
            self.edit_json(members, "attempt/registration.json",
                           lambda r: r.__setitem__("source_commit", "0" * 40))
        with self.assertRaisesRegex(ValueError, "registration identity"):
            audit.check(self.altered(mutate))

    def test_favorable_analysis_rejected_after_rehash(self):
        def mutate(members):
            self.edit_json(members, "attempt/analysis.json",
                           lambda r: r.__setitem__("production_eligible", True))
        with self.assertRaisesRegex(ValueError, "published analysis"):
            audit.check(self.altered(mutate))


if __name__ == "__main__":
    unittest.main()
