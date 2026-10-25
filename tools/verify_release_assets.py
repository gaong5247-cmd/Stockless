#!/usr/bin/env python3
"""Fail closed if an OS build is missing or a Stockless release ZIP is malformed."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

from package_release import PLATFORMS, read_version

REQUIRED = ("LICENSE", "NOTICE.md", "UPSTREAM.md", "engine-branding.json",
            "stockless-logo.svg", "README.txt", "manifest.json")
STRENGTH_PLATFORM = "linux-x86_64-avx2-pgo"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_strength_identity(package: Path, report: dict, expected_commit: str | None) -> None:
    """Bind the actual released executable bytes to approved match evidence."""
    if not expected_commit:
        raise RuntimeError("Strength identity verification requires --expected-commit")
    if not (report.get("valid") is True and report.get("approved") is True
            and report.get("mode") == "confirmation"
            and report.get("candidate_sha") == expected_commit
            and report.get("candidate_build_profile") == "pgo-avx2"):
        raise RuntimeError("Strength report is not approved PGO confirmation for the expected source")
    tested_digest = report.get("candidate_binary_sha256")
    if not isinstance(tested_digest, str) or re.fullmatch(r"[0-9a-f]{64}", tested_digest) is None:
        raise RuntimeError("Strength report has no valid tested candidate SHA-256")
    with zipfile.ZipFile(package, "r") as archive:
        manifest = json.loads(archive.read("manifest.json"))
        if not (manifest.get("platform") == STRENGTH_PLATFORM
                and manifest.get("build_profile") == "pgo"
                and manifest.get("source_commit") == expected_commit):
            raise RuntimeError("Strength package has the wrong platform, profile, or source commit")
        executable = manifest.get("binary")
        if not isinstance(executable, str) or executable not in archive.namelist():
            raise RuntimeError("Strength package executable is missing")
        binary = archive.read(executable)
        actual_digest = digest(binary)
        if not binary or actual_digest != tested_digest:
            raise RuntimeError("Released Linux PGO executable differs from the strength-tested bytes")
        if manifest.get("binary_sha256") != actual_digest:
            raise RuntimeError("Strength package executable hash disagrees with its manifest")
    print(f"PASS tested-binary identity: {package.name} SHA-256={tested_digest}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-commit", default=None)
    parser.add_argument("--strength-report", type=Path,
                        help="Require exact Linux AVX2 PGO binary identity with approved confirmation")
    args = parser.parse_args()
    version = read_version()
    actual = {p.name for p in args.directory.glob("*.zip")}
    expected = {f"Stockless-{version}-{platform}.zip" for platform in PLATFORMS}
    missing, unexpected = expected - actual, actual - expected
    if missing or unexpected:
        raise RuntimeError(f"Expected {len(expected)} packages; missing={sorted(missing)}, extra={sorted(unexpected)}")

    for platform in sorted(PLATFORMS):
        path = args.directory / f"Stockless-{version}-{platform}.zip"
        with zipfile.ZipFile(path, "r") as archive:
            if archive.testzip() is not None:
                raise RuntimeError(f"Corrupt ZIP: {path}")
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise RuntimeError(f"Duplicate ZIP entries: {path}")
            manifest = json.loads(archive.read("manifest.json"))
            if manifest["platform"] != platform or manifest["uci_id_name"] != f"Stockless {version}":
                raise RuntimeError(f"Version/platform mismatch: {path}")
            if args.expected_commit is not None and manifest["source_commit"] != args.expected_commit:
                raise RuntimeError(f"Wrong source commit in {path}")
            for name in REQUIRED:
                if name not in names:
                    raise RuntimeError(f"{path}: missing {name}")
            executable = manifest["binary"]
            if executable not in names or archive.getinfo(executable).file_size == 0:
                raise RuntimeError(f"{path}: binary missing/empty")
            if digest(archive.read(executable)) != manifest["binary_sha256"]:
                raise RuntimeError(f"{path}: failed binary SHA-256 check")
            branding = json.loads(archive.read("engine-branding.json"))
            if branding.get("version") != version or branding.get("match", {}).get("uci_id_name") != f"Stockless {version}":
                raise RuntimeError(f"{path}: branding mismatch")
            if not executable.endswith(".exe") and not (archive.getinfo(executable).external_attr >> 16 & 0o111):
                raise RuntimeError(f"{path}: non-Windows binary is not executable")
        print(f"PASS {path.name} ({path.stat().st_size:,} bytes)")

    if args.strength_report is not None:
        report = json.loads(args.strength_report.read_text(encoding="utf-8"))
        verify_strength_identity(
            args.directory / f"Stockless-{version}-{STRENGTH_PLATFORM}.zip",
            report,
            args.expected_commit,
        )

    print(f"All {len(expected)} platform packages verified for {version}.")


if __name__ == "__main__":
    main()
