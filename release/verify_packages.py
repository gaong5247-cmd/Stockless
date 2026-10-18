#!/usr/bin/env python3
"""Independently verify every Stockless Release package."""
from __future__ import annotations
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

PLATFORMS = ("linux-x86_64-universal", "windows-x86_64-universal", "android-arm64-universal")

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--source-commit", required=True)
    ap.add_argument("--directory", type=Path, required=True)
    args = ap.parse_args()
    root = args.directory.resolve(strict=True)
    files = sorted(root.glob("*.zip"))
    expected = sorted(root / f"Stockless-{args.version}-{platform}.zip" for platform in PLATFORMS)
    if files != expected:
        raise SystemExit(f"Expected exact packages {expected}, found {files}")
    sums = []
    for path in expected:
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None:
                raise SystemExit(f"Corrupt ZIP: {path}")
            man = json.loads(z.read("manifest.json"))
            platform = path.stem.removeprefix(f"Stockless-{args.version}-")
            if man["version"] != args.version or man["platform"] != platform:
                raise SystemExit(f"Wrong metadata in {path}")
            if man["uci_id_name"] != f"Stockless {args.version}":
                raise SystemExit(f"Incorrect UCI identity in {path}")
            if man["source_commit"] != args.source_commit:
                raise SystemExit(f"Wrong source commit in {path}")
            if sha256(z.read(man["binary"])) != man["binary_sha256"]:
                raise SystemExit(f"Binary SHA mismatch in {path}")
            for required in ("LICENSE", "NOTICE.md", "UPSTREAM.md", "README.txt"):
                if required not in z.namelist():
                    raise SystemExit(f"Missing {required} in {path}")
        sums.append(f"{sha256(path.read_bytes())}  {path.name}")
    (root / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print("\n".join(sums))
    print(f"Validated {len(files)} platform archives for {args.version} at {args.source_commit}")

if __name__ == "__main__":
    main()
