#!/usr/bin/env python3
"""Split a real, diverse EPD book into disjoint, reproducible tuning sets.

Recommended source: official-stockfish/books 6mvs_+90_+99.epd.zip (CC0).
Keeps screening, confirmation and Stockfish matches on different positions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import zipfile
from pathlib import Path

import chess


def load_epd(path: Path) -> tuple[list[str], str]:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist() if n.lower().endswith(".epd")]
            if len(names) != 1:
                raise ValueError(f"Expected one .epd in {path}, found {names!r}")
            payload = archive.read(names[0])
    else:
        payload = path.read_bytes()

    lines = []
    seen = set()
    for line_number, raw in enumerate(payload.decode("utf-8-sig").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 4:
            raise ValueError(f"{path}:{line_number}: incomplete EPD")
        epd = " ".join(fields[:4])
        try:
            board = chess.Board(epd + " 0 1")
        except ValueError as error:
            raise ValueError(f"{path}:{line_number}: invalid EPD: {error}") from error
        if not board.is_valid():
            raise ValueError(f"{path}:{line_number}: invalid legal position")
        canonical = board.epd()
        if canonical not in seen:
            lines.append(canonical)
            seen.add(canonical)
    return lines, hashlib.sha256(payload).hexdigest()


def split(
    source: Path,
    out_dir: Path,
    profile: str,
    seed: int,
) -> dict:
    lines, digest = load_epd(source)
    counts = ({"screen": 10, "confirm": 10, "stockfish": 10, "long": 10}
              if profile == "smoke" else
              {"screen": 600, "confirm": 700, "stockfish": 800, "long": 700})
    needed = sum(counts.values())
    if len(lines) < needed:
        raise ValueError(
            f"{len(lines)} unique positions found; {profile} requires at least "
            f"{needed}. Use official-stockfish/books 6mvs_+90_+99.epd.zip."
        )
    random.Random(seed).shuffle(lines)
    out_dir.mkdir(parents=True, exist_ok=True)
    sets = {}
    offset = 0
    for stage, count in counts.items():
        selected = lines[offset : offset + count]
        offset += count
        destination = out_dir / f"{stage}.epd"
        destination.write_text("\n".join(selected) + "\n", encoding="utf-8")
        sets[stage] = {"path": str(destination), "positions": len(selected)}

    manifest = {
        "source": str(source),
        "source_sha256": digest,
        "book_unique_positions": len(lines),
        "profile": profile,
        "seed": seed,
        "sets": sets,
        "sets_disjoint": True,
        "source_url": (
            "https://github.com/official-stockfish/books/blob/master/"
            "6mvs_%2B90_%2B99.epd.zip"
        ),
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("results/openings"))
    parser.add_argument("--profile", choices=("smoke", "full"), default="full")
    parser.add_argument("--seed", type=int, default=20261017)
    args = parser.parse_args()
    split(args.source, args.output, args.profile, args.seed)


if __name__ == "__main__":
    main()
