#!/usr/bin/env python3
"""Apply an evidence-gated history default to the EXPERIMENTAL branch.

Never changes the default if ON/OFF confidence, long holdout, Stockfish guard,
or minimum sample/book checks fail. This script DOES NOT merge into main.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def replace_exact(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected exactly one occurrence, found {count}")
    return text.replace(old, new, 1)


def apply(result_path: Path, root: Path) -> bool:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    verdict = result["promotion"]
    if not verdict["approved"]:
        print("Promotion NOT approved:", verdict["reason"])
        return False

    github_run_id = os.environ.get("GITHUB_RUN_ID")
    if github_run_id and str(result["github_run_id"]) != github_run_id:
        raise ValueError("Decision file belongs to a different GitHub Actions run")
    if result["profile"] != "full":
        raise ValueError("Smoke profile must never change engine defaults")

    requested = result["games_requested"]
    if (requested["confirm"] < 600 or requested["stockfish"] < 600
            or requested["long"] < 400):
        raise ValueError("Insufficient independent confirmation sample")
    book = result["book"]
    if not book["sets_disjoint"] or book["book_unique_positions"] < 2800:
        raise ValueError("Opening book too small or datasets overlap")
    weight = verdict["weight"]
    if not isinstance(weight, int) or not (1 <= weight <= 200):
        raise ValueError("Invalid selected history weight")
    if result["candidate"]["weight"] != weight or not result["candidate"]["enabled"]:
        raise ValueError("Candidate and selected weight mismatch")
    for stage in ("confirmation", "long_confirmation"):
        stat = result[stage]
        if not stat or stat["score_ci95"][0] <= 0.5:
            raise ValueError(f"{stage} did not show an independent improvement")
    stockfish = result["stockfish"]
    if (not stockfish or not stockfish["candidate"] or
            stockfish["difference"]["ci95"][0] <= -0.025):
        raise ValueError("Stockfish non-regression guard did not pass")
    for stage, stat in (
        ("confirm", result["confirmation"]),
        ("long", result["long_confirmation"]),
        ("stockfish", stockfish["candidate"]),
    ):
        if stat["games"] != requested["stockfish" if stage == "stockfish" else stage]:
            raise ValueError(f"{stage} games do not match requested sample size")

    config = root / "src/stockless/config.h"
    old = config.read_text(encoding="utf-8")
    new = replace_exact(
        old, "inline constexpr bool DefaultThreatHistory = false;",
        "inline constexpr bool DefaultThreatHistory = true;", str(config)
    )
    new = replace_exact(
        new, "inline constexpr int  DefaultThreatHistoryWeight = 100;",
        f"inline constexpr int  DefaultThreatHistoryWeight = {weight};", str(config)
    )

    english = (
        "Experimental research: v0.7 threat history is now enabled by default "
        f"at weight {weight} on this experiment branch following internal "
        "short-time-control tests; this is not an official Elo rating."
    )
    korean = (
        f"실험 브랜치의 v0.7 위협 History 기본값은 ON/가중치 {weight}입니다. "
        "내부 대국 검증 결과이며 공식 레이팅은 아닙니다."
    )
    readme = root / "README.md"
    readme_old = readme.read_text(encoding="utf-8")
    readme_new = replace_exact(
        readme_old,
        "This feature is OFF by default; no Elo gain is claimed.",
        english,
        str(readme),
    )
    readme_new = replace_exact(
        readme_new,
        "기본값은 OFF이며 Elo 상승이 검증된 것은 아닙니다.",
        korean,
        str(readme),
    )

    doc = root / "docs/EXPERIMENT_07.md"
    doc_old = doc.read_text(encoding="utf-8")
    doc_new = doc_old + (
        "\n\n## Confirmed experiment-branch default\n\n"
        f"See docs/HISTORY_TUNING_REPORT.md: History ON, weight {weight} "
        "was approved by the automated fixed-sample tests for this "
        "experimental branch. Main is unchanged until PR merge.\n"
    )

    # All validation is done before writing any file.
    config.write_text(new, encoding="utf-8")
    readme.write_text(readme_new, encoding="utf-8")
    doc.write_text(doc_new, encoding="utf-8")
    report = result_path.with_name("report.md").read_text(encoding="utf-8")
    (root / "docs/HISTORY_TUNING_REPORT.md").write_text(
        report + "\n\nGitHub Actions run: "
        + str(result.get("github_run_id")) + "\n", encoding="utf-8"
    )
    print(f"Evidence-backed experiment default set: History ON, weight {weight}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", type=Path,
                        default=Path("results/history-tuning/decision.json"))
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    promoted = apply(args.decision, args.root)
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fp:
            fp.write(f"promoted={'true' if promoted else 'false'}\n")


if __name__ == "__main__":
    main()
