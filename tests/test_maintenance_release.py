"""Maintenance publication must reject gameplay changes and wrong identities."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from verify_maintenance_release import compare_sources, verify_plan


class MaintenanceGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.before = Path(self.temp.name) / "before"
        self.after = Path(self.temp.name) / "after"
        for directory, version in ((self.before, "v0.9.0"), (self.after, "v0.9.1")):
            directory.mkdir()
            (directory / "config.h").write_text(
                f'inline constexpr const char* Version = "{version}";\n'
                'inline constexpr int DefaultHybridAggression = 145;\n')
            (directory / "search.cpp").write_text("int reduction = 640;\n")

    def test_only_version_change_passes(self):
        self.assertEqual(compare_sources(self.before, self.after), 2)

    def test_search_or_default_change_rejected(self):
        for filename, old, new in (("search.cpp", "640", "641"), ("config.h", "145", "146")):
            with self.subTest(filename=filename):
                path = self.after / filename
                original = path.read_text()
                path.write_text(original.replace(old, new))
                with self.assertRaisesRegex(RuntimeError, "changes engine sources"):
                    compare_sources(self.before, self.after)
                path.write_text(original)

    def test_missing_or_added_source_rejected(self):
        (self.after / "extra.h").write_text("new search feature")
        with self.assertRaisesRegex(RuntimeError, "extra.h"):
            compare_sources(self.before, self.after)
        (self.after / "extra.h").unlink()
        (self.after / "search.cpp").unlink()
        with self.assertRaisesRegex(RuntimeError, "search.cpp"):
            compare_sources(self.before, self.after)

    def test_valid_patch_plan(self):
        plan = json.loads((ROOT / "release/maintenance.json").read_text())
        verify_plan(plan, "v0.9.0", "v0.9.1")

    def test_strength_claim_wrong_version_and_source_rejected(self):
        plan = json.loads((ROOT / "release/maintenance.json").read_text())
        for key, value in (("playing_strength_claim", True), ("tag", "Stockless_v0.9.0"),
                           ("baseline_commit", "main"), ("notes", "README.md")):
            with self.subTest(key=key):
                changed = copy.deepcopy(plan)
                changed[key] = value
                with self.assertRaises(RuntimeError):
                    verify_plan(changed, "v0.9.0", "v0.9.1")
        with self.assertRaisesRegex(RuntimeError, "next patch"):
            verify_plan(plan, "v0.9.0", "v0.10.0")


if __name__ == "__main__":
    unittest.main()
