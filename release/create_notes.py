#!/usr/bin/env python3
"""Generate accurate release notes from a pinned manifest."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, default=Path("release/v08-series-manifest.json"))
    ap.add_argument("--version", required=True)
    ap.add_argument("--source-commit", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    versions = json.loads(args.manifest.read_text(encoding="utf-8"))["releases"]
    selected = next((v for v in versions if v["version"] == args.version), None)
    if not selected:
        raise SystemExit("Version not in locked manifest")
    kind = "Pre-release" if selected["prerelease"] else "Historical research release"
    lines = [
        f"# Stockless {args.version} — {kind}", "",
        selected["notes"], "",
        "**Playing strength:** version numbering is not an Elo guarantee. Earlier v0.8 runs were experimental; several tweaks failed independent holdouts.",
        "ZIP binaries use the historical research defaults, without claiming retroactive improvement.", "",
        "## Downloads", "",
        "Three native UCI archives: Windows x86-64 Universal, Linux x86-64 Universal, and Android ARM64 Universal. Android is NOT an APK.",
        "Each ZIP includes SHA-256 binary digest and notices; SHA256SUMS.txt verifies ZIP downloads.", "",
        "## Provenance", "",
        f"- Versioned source tag: {selected['tag']}",
        f"- Versioned source commit: {args.source_commit}",
        f"- Archived experiment parent: {selected['sha']}",
        f"- Official Stockfish SHA: {'effdc3fd3f6de6e75fe1374a51a7a7eed66f880b (SFNNv18)' if selected['modern'] else '0a215d6c9e48856ef630013b8ab8312941a59057'}",
        "- Original Stockfish and Reckless submodule references and copyright notices are preserved.", "",
        "## Important limitations", "",
        "Universal packages are NOT PGO trained, so CPU-specific experimental PGO Elo/NPS results are not transferable directly.",
        "v0.8.8-rc1 is a PRE-RELEASE; the attempted dual-queen fastpath is opt-in only because it regressed NPS in testing.",
        "No release should be described as stronger than Stockfish without independent evidence.", "",
    ]
    args.output.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    main()
