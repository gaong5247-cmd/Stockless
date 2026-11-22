#!/usr/bin/env python3
"""Exercise release ZIPs as a GUI/extractor would consume them."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from package_release import PLATFORMS, read_version
from verify_release_assets import verify_package


class PackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="stockless packaging ")
        self.directory = Path(self.temporary.name)
        self.binary = self.directory / "input files" / "stockless"
        self.binary.parent.mkdir()
        self.binary.write_bytes(b"package fixture; not an executable engine")
        self.version = read_version()
        self.commit = "a" * 40

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def package(self, platform: str = "linux-x86_64-universal") -> Path:
        # Both input and output are intentionally relative to an unrelated CWD
        # and contain spaces, as Windows extraction/build directories often do.
        subprocess.run(
            [sys.executable, str(ROOT / "tools/package_release.py"),
             "--platform", platform, "--binary", "input files/stockless",
             "--output-dir", "release files", "--source-sha", self.commit],
            cwd=self.directory, check=True, capture_output=True, text=True,
        )
        return self.directory / "release files" / f"Stockless-{self.version}-{platform}.zip"

    def rewrite(self, source: Path, *, omit: str | None = None,
                manifest_changes: dict | None = None,
                branding_changes: dict | None = None) -> Path:
        modified = self.directory / "modified.zip"
        with zipfile.ZipFile(source) as original, zipfile.ZipFile(modified, "w") as output:
            for info in original.infolist():
                if info.filename == omit:
                    continue
                content = original.read(info.filename)
                if info.filename == "manifest.json" and manifest_changes:
                    content = json.dumps({**json.loads(content), **manifest_changes}).encode()
                if info.filename == "engine-branding.json" and branding_changes:
                    branding = json.loads(content)
                    branding["branding"].update(branding_changes)
                    content = json.dumps(branding).encode()
                output.writestr(info, content)
        return modified

    def test_all_platforms_have_resolvable_branding_and_verify_together(self) -> None:
        for platform in PLATFORMS:
            with self.subTest(platform=platform):
                package = self.package(platform)
                verify_package(package, self.version, platform, self.commit)
                with zipfile.ZipFile(package) as archive:
                    branding = json.loads(archive.read("engine-branding.json"))
                    for kind in ("logo", "icon"):
                        self.assertEqual(archive.read(branding["branding"][kind]),
                                         archive.read("stockless-logo.svg"))
                    notes = archive.read("README.txt").decode()
                    self.assertIn("Results from an earlier release do not establish", notes)
        subprocess.run(
            [sys.executable, str(ROOT / "tools/verify_release_assets.py"),
             "release files", "--expected-commit", self.commit],
            cwd=self.directory, check=True, capture_output=True, text=True,
        )

    def test_relative_space_paths_and_reproducible_zip(self) -> None:
        package = self.package()
        first = package.read_bytes()
        self.assertEqual(first, self.package().read_bytes())
        with zipfile.ZipFile(package) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(archive.read(manifest["binary"]), self.binary.read_bytes())
            self.assertTrue(archive.getinfo(manifest["binary"]).external_attr >> 16 & 0o111)

    def test_old_missing_branding_asset_is_rejected(self) -> None:
        # v0.9.0 shipped only the root logo although branding named assets/.
        package = self.rewrite(self.package(), omit="assets/stockless-logo.svg")
        with self.assertRaisesRegex(RuntimeError, "branding logo does not resolve"):
            verify_package(package, self.version, "linux-x86_64-universal", self.commit)

    def test_unresolvable_icon_is_rejected_even_when_logo_exists(self) -> None:
        package = self.rewrite(self.package(), branding_changes={"icon": "missing.svg"})
        with self.assertRaisesRegex(RuntimeError, "branding icon does not resolve"):
            verify_package(package, self.version, "linux-x86_64-universal", self.commit)

    def test_manifest_version_must_match_uci_identity(self) -> None:
        package = self.rewrite(self.package(), manifest_changes={"version": "v0.0.0"})
        with self.assertRaisesRegex(RuntimeError, "Version/platform mismatch"):
            verify_package(package, self.version, "linux-x86_64-universal", self.commit)


if __name__ == "__main__":
    unittest.main()
