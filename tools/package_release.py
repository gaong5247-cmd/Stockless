#!/usr/bin/env python3
"""Package a Stockless UCI binary and its required source/license notices.

Every release asset is platform-specific. The x86-64 and ARM64 "universal"
builds select CPU instruction sets at runtime; they are not one binary that
runs on Windows, Linux, and Android interchangeably.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = {
    "windows-x86_64-universal": ("Windows 64-bit", "x86-64 to AVX-512 runtime dispatch"),
    "linux-x86_64-universal": ("Linux 64-bit", "x86-64 to AVX-512 runtime dispatch"),
    "linux-arm64-universal": ("Linux ARM64", "ARMv8/ARMv8-dotprod runtime dispatch"),
    "android-arm64-universal": ("Android 8+ ARM64", "ARMv8/ARMv8-dotprod runtime dispatch"),
    "android-armeabi-v7a": ("Android 8+ ARMv7", "ARMv7 NEON fixed instruction set"),
}


def read_version() -> str:
    text = (ROOT / "src/stockless/config.h").read_text(encoding="utf-8")
    match = re.search(r'inline constexpr const char\* Version = "(v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)?)";', text)
    if match is None:
        raise RuntimeError("Expected a semantic UCI Version in src/stockless/config.h")
    return match.group(1)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def add_entry(archive: zipfile.ZipFile, name: str, data: bytes, executable: bool = False) -> None:
    # Fixed metadata keeps release ZIPs reproducible for the same input bytes.
    info = zipfile.ZipInfo(name, date_time=(2026, 10, 18, 0, 0, 0))
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = ((0o100755 if executable else 0o100644) << 16)
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=PLATFORMS, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--source-sha", default="unknown")
    args = parser.parse_args()

    version = read_version()
    binary = args.binary.resolve(strict=True)
    if not binary.is_file() or binary.stat().st_size == 0:
        parser.error("Binary is missing or empty")

    os_label, cpu = PLATFORMS[args.platform]
    name = f"stockless-{version}-{args.platform}" + (".exe" if args.platform.startswith("windows-") else "")
    asset = f"Stockless-{version}-{args.platform}.zip"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = args.output_dir / asset

    binary_bytes = binary.read_bytes()
    manifest = {
        "engine": "Stockless",
        "uci_id_name": f"Stockless {version}",
        "version": version,
        "platform": args.platform,
        "platform_label": os_label,
        "cpu_dispatch": cpu,
        "binary": name,
        "binary_sha256": sha256(binary_bytes),
        "source_commit": args.source_sha,
        "nnue": "Embedded by pinned Stockfish build; external NNUE not required for defaults",
        "source": "https://github.com/gaong5247-cmd/Stockless",
        "license": "AGPL-3.0; upstream notices included",
    }

    instructions = (
        f"Stockless {version} — {os_label}\n\n"
        f"UCI executable: {name}\n"
        f"CPU support: {cpu}\n\n"
        "Windows: extract the ZIP, select the EXE as a UCI engine in your chess GUI.\n"
        "Linux: extract, run chmod +x on the executable if necessary, then register it as a UCI engine.\n"
        "Android: extract the binary and import/select it through a chess GUI supporting external UCI engines, e.g. DroidFish.\n"
        "This is a native UCI engine, NOT an Android APK.\n\n"
        "The executable includes the Stockfish NNUE networks used by the pinned build.\n"
        "Default: Hybrid true; aggression 145; Threats true; Overdrive false; ThreatHistory false.\n"
        "No Elo increase relative to v0.7 is established merely by the new version.\n"
        f"Source commit: {args.source_sha}\n"
        f"Binary SHA-256: {manifest['binary_sha256']}\n"
    )
    additions = {
        name: binary_bytes,
        "LICENSE": (ROOT / "LICENSE").read_bytes(),
        "NOTICE.md": (ROOT / "NOTICE.md").read_bytes(),
        "UPSTREAM.md": (ROOT / "docs/UPSTREAM.md").read_bytes(),
        "engine-branding.json": (ROOT / "engine-branding.json").read_bytes(),
        "stockless-logo.svg": (ROOT / "assets/stockless-logo.svg").read_bytes(),
        "README.txt": instructions.encode("utf-8"),
        "manifest.json": (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    }
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for fname, contents in additions.items():
            add_entry(archive, fname, contents, executable=(fname == name and not name.endswith(".exe")))

    with zipfile.ZipFile(archive_path, "r") as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Corrupt ZIP was generated")
        if archive.read("manifest.json") != additions["manifest.json"]:
            raise RuntimeError("Manifest roundtrip mismatch")
        if sha256(archive.read(name)) != manifest["binary_sha256"]:
            raise RuntimeError("Binary hash mismatch after packaging")

    print(f"{archive_path} SHA-256={sha256(archive_path.read_bytes())}")


if __name__ == "__main__":
    main()
