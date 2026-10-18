#!/usr/bin/env python3
"""Fail closed if an OS build is missing or a Stockless release ZIP is malformed."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from package_release import PLATFORMS, read_version

REQUIRED = ("LICENSE", "NOTICE.md", "UPSTREAM.md", "engine-branding.json",
            "stockless-logo.svg", "README.txt", "manifest.json")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-commit", default=None)
    args = parser.parse_args()
    version = read_version()
    actual = {p.name for p in args.directory.glob("*.zip")}
    expected = {f"Stockless-{version}-{platform}.zip" for platform in PLATFORMS}
    missing, unexpected = expected - actual, actual - expected
    if missing or unexpected:
        raise RuntimeError(f"Expected 5 platforms; missing={sorted(missing)}, extra={sorted(unexpected)}")

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

    print(f"All {len(expected)} platform packages verified for {version}.")


if __name__ == "__main__":
    main()
