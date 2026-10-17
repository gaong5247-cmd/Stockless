#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "upstream" / "stockfish"
RECKLESS = ROOT / "upstream" / "reckless"
OVERLAY = ROOT / "src" / "stockless"
DEFAULT_OUT = ROOT / "build" / "stockless-src"

STOCKFISH_SHA = "0a215d6c9e48856ef630013b8ab8312941a59057"
RECKLESS_SHA = "7300f044812d80397960e3a27a4f085e9487419a"
STOCKLESS_VERSION = "0.5-dev"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one patch anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def ensure_submodules() -> None:
    if (UPSTREAM / "src" / "search.cpp").exists() and (RECKLESS / "src" / "search.rs").exists():
        return
    subprocess.run(["git", "submodule", "update", "--init", "--recursive"], cwd=ROOT, check=True)


def verify_pin(path: Path, expected: str, label: str) -> None:
    actual = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    if actual != expected:
        raise RuntimeError(
            f"{label} submodule is {actual}, expected pinned {expected}. "
            "Update docs/UPSTREAM.md and patch anchors before changing the pin."
        )


def materialize(out: Path) -> None:
    ensure_submodules()
    verify_pin(UPSTREAM, STOCKFISH_SHA, "Stockfish")
    verify_pin(RECKLESS, RECKLESS_SHA, "Reckless")

    if out.exists():
        shutil.rmtree(out)

    shutil.copytree(UPSTREAM, out, ignore=shutil.ignore_patterns(".git"))

    target_overlay = out / "src" / "stockless_core"
    shutil.copytree(OVERLAY, target_overlay)

    search_cpp = out / "src" / "search.cpp"
    search_h = out / "src" / "search.h"
    movepick_h = out / "src" / "movepick.h"
    movepick_cpp = out / "src" / "movepick.cpp"
    engine_cpp = out / "src" / "engine.cpp"
    misc_cpp = out / "src" / "misc.cpp"
    makefile = out / "src" / "Makefile"

    # Keep the experimental history owned by each Stockfish search Worker.
    replace_once(
        search_h,
        '#include "history.h"\n',
        '#include "history.h"\n#include "stockless_core/threat_history.h"\n',
    )
    replace_once(
        search_h,
        "    ButterflyHistory mainHistory;\n    LowPlyHistory    lowPlyHistory;\n",
        "    ButterflyHistory mainHistory;\n    LowPlyHistory    lowPlyHistory;\n"
        "    Stockless::ThreatQuietHistory threatQuietHistory;\n",
    )

    replace_once(
        movepick_h,
        '#include "history.h"\n',
        '#include "history.h"\n#include "stockless_core/threat_history.h"\n',
    )
    replace_once(
        movepick_h,
        "               const SharedHistories*,\n               int);\n",
        "               const SharedHistories*,\n               int,\n"
        "               const Stockless::ThreatQuietHistory* = nullptr);\n",
    )
    replace_once(
        movepick_h,
        "    const SharedHistories*       sharedHistory;\n",
        "    const SharedHistories*       sharedHistory;\n"
        "    const Stockless::ThreatQuietHistory* threatQuietHistory = nullptr;\n",
    )
    replace_once(
        movepick_cpp,
        '#include "position.h"\n',
        '#include "position.h"\n#include "stockless_core/config.h"\n'
        '#include "stockless_core/threat_signal.h"\n',
    )
    replace_once(
        movepick_cpp,
        "                       const SharedHistories*       sh,\n"
        "                       int                          pl) :\n",
        "                       const SharedHistories*       sh,\n"
        "                       int                          pl,\n"
        "                       const Stockless::ThreatQuietHistory* th) :\n",
    )
    replace_once(
        movepick_cpp,
        "    sharedHistory(sh),\n",
        "    sharedHistory(sh),\n    threatQuietHistory(th),\n",
    )
    # Compute enemy attack map once per generated quiet-move list, not per move.
    replace_once(
        movepick_cpp,
        "    Color us = pos.side_to_move();\n",
        "    Color us = pos.side_to_move();\n"
        "\n"
        "    [[maybe_unused]] int stocklessHistoryWeight = 0;\n"
        "    [[maybe_unused]] Bitboard stocklessEnemyAttacks = 0;\n"
        "    if constexpr (Type == QUIETS)\n"
        "        if (threatQuietHistory && Stockless::threat_history_enabled())\n"
        "        {\n"
        "            stocklessHistoryWeight = Stockless::threat_history_weight();\n"
        "            if (stocklessHistoryWeight)\n"
        "                stocklessEnemyAttacks = Stockless::attacks_for(pos, ~us);\n"
        "        }\n",
    )
    replace_once(
        movepick_cpp,
        "            int value = 2 * (*mainHistory)[us][m.raw()];\n",
        "            int value = 2 * (*mainHistory)[us][m.raw()];\n"
        "            if (stocklessHistoryWeight)\n"
        "                value += stocklessHistoryWeight\n"
        "                       * threatQuietHistory->get(stocklessEnemyAttacks, us, m) / 100;\n",
    )

    replace_once(
        search_cpp,
        '#include "search.h"\n',
        '#include "search.h"\n#include "stockless_core/search_policy.h"\n#include "stockless_core/threat_signal.h"\n',
    )

    node_anchor = """    MovePicker mp(pos, ttData.move, depth, &mainHistory, &lowPlyHistory, &captureHistory, contHist,
                  &sharedHistory, ss->ply);
"""
    node_patch = """    const auto stocklessThreat =
      Stockless::compute_threat_signal(pos, int(depth), ss->ttPv || PvNode || depth >= 8);

""" + node_anchor.replace(
        "                  &sharedHistory, ss->ply);\n",
        "                  &sharedHistory, ss->ply,\n"
        "                  Stockless::threat_history_enabled() ? &threatQuietHistory : nullptr);\n",
    )
    replace_once(search_cpp, node_anchor, node_patch)

    policy_anchor = """        // Increase reduction for ttPv nodes
        // (*Scaler) Larger values scale well.
        if (ss->ttPv)
            r += 929;
"""
    policy_patch = policy_anchor + """
        const int stocklessCorrectionSignal =
          std::min(256, int(std::abs(correctionValue) / 131072));

        const auto stocklessPolicy = Stockless::make_search_policy({
          int(depth),
          moveCount,
          int(beta - alpha),
          ss->staticEval == VALUE_NONE ? 0 : int(ss->staticEval),
          int(alpha),
          int(beta),
          stocklessCorrectionSignal,
          int((ss + 1)->cutoffCnt),
          improving,
          capture,
          givesCheck,
          ss->inCheck,
          ss->ttPv,
          PvNode,
          cutNode,
          stocklessThreat,
        });
"""
    replace_once(search_cpp, policy_anchor, policy_patch)

    replace_once(
        search_cpp,
        """            if (moveCount >= (3 + depth * depth) / (2 - improving))
                mp.skip_quiet_moves();
""",
        """            if (moveCount >= (3 + depth * depth) / (2 - improving)
                              + stocklessPolicy.quietMoveAllowance)
                mp.skip_quiet_moves();
""",
    )

    # Preserve the normal Stockfish history lifecycle.
    replace_once(
        search_cpp,
        "    mainHistory.fill(-5);\n",
        "    mainHistory.fill(-5);\n    threatQuietHistory.clear();\n",
    )
    replace_once(
        search_cpp,
        "    lowPlyHistory.fill(102);\n",
        "    lowPlyHistory.fill(102);\n"
        "    if (Stockless::threat_history_enabled())\n"
        "        threatQuietHistory.age();\n",
    )

    # Reinforce successful quiet moves and penalize searched unsuccessful ones.
    # The reduced amplitudes limit disruption to Stockfish's primary history.
    replace_once(
        search_cpp,
        "        update_quiet_histories(pos, ss, workerThread, bestMove, bonus * 899 / 1024);\n",
        "        update_quiet_histories(pos, ss, workerThread, bestMove, bonus * 899 / 1024);\n"
        "        const bool stocklessTrainHistory = Stockless::threat_history_enabled()\n"
        "                                        && Stockless::threat_history_weight() > 0;\n"
        "        const Bitboard stocklessEnemyAttacks =\n"
        "          stocklessTrainHistory ? Stockless::attacks_for(pos, ~pos.side_to_move()) : 0;\n"
        "        if (stocklessTrainHistory)\n"
        "            workerThread.threatQuietHistory.update(\n"
        "              stocklessEnemyAttacks, pos.side_to_move(), bestMove, bonus * 450 / 1024);\n",
    )
    replace_once(
        search_cpp,
        "            update_quiet_histories(pos, ss, workerThread, move, -actualMalus);\n",
        "            update_quiet_histories(pos, ss, workerThread, move, -actualMalus);\n"
        "            if (stocklessTrainHistory)\n"
        "                workerThread.threatQuietHistory.update(\n"
        "                  stocklessEnemyAttacks, pos.side_to_move(), move, -actualMalus / 2);\n",
    )

    replace_once(
        search_cpp,
        "            int lmrDepth = newDepth - r / 1024;\n",
        "            int lmrDepth = newDepth - r / 1024 + stocklessPolicy.pruningDepthBoost;\n",
    )

    lmr_anchor = """        // Apply the computed LMR
        if (depth >= 2 && moveCount > 1)
"""
    lmr_patch = """        r += stocklessPolicy.lmrAdjustment;

""" + lmr_anchor
    replace_once(search_cpp, lmr_anchor, lmr_patch)

    replace_once(
        search_cpp,
        """                newDepth += doDeeperSearch - doShallowerSearch;
""",
        """                newDepth += doDeeperSearch - doShallowerSearch;
                if (stocklessPolicy.reSearchDepthBonus && value > bestValue + 20)
                    newDepth += stocklessPolicy.reSearchDepthBonus;
""",
    )

    replace_once(
        engine_cpp,
        '#include "search.h"\n',
        '#include "search.h"\n#include "stockless_core/config.h"\n',
    )

    option_anchor = '    options.add("UCI_ShowWDL", Option(false));\n'
    option_patch = option_anchor + """
    options.add(
      "StocklessHybrid", Option(true, [](const Option& o) {
          Stockless::set_hybrid_enabled(bool(o));
          return std::nullopt;
      }));

    options.add(
      "StocklessAggression", Option(Stockless::default_hybrid_aggression(), 0, 200, [](const Option& o) {
          Stockless::set_hybrid_aggression(int(o));
          return std::nullopt;
      }));

    options.add(
      "StocklessThreats", Option(true, [](const Option& o) {
          Stockless::set_threats_enabled(bool(o));
          return std::nullopt;
      }));

    options.add(
      "StocklessOverdrive", Option(Stockless::default_overdrive(), [](const Option& o) {
          Stockless::set_overdrive_enabled(bool(o));
          return std::nullopt;
      }));

    options.add(
      "StocklessMobile", Option(Stockless::default_mobile_profile(), [](const Option& o) {
          Stockless::set_mobile_profile(bool(o));
          return std::nullopt;
      }));

    options.add(
      "StocklessThreatHistory", Option(Stockless::default_threat_history(), [](const Option& o) {
          Stockless::set_threat_history_enabled(bool(o));
          return std::nullopt;
      }));

    options.add(
      "StocklessHistoryWeight", Option(Stockless::default_threat_history_weight(), 0, 200, [](const Option& o) {
          Stockless::set_threat_history_weight(int(o));
          return std::nullopt;
      }));
"""
    replace_once(engine_cpp, option_anchor, option_patch)

    replace_once(
        misc_cpp,
        '    ss << "Stockfish " << version << std::setfill(\'0\');\n',
        '    ss << "Stockless 0.5" << std::setfill(\'0\');\n',
    )
    replace_once(
        misc_cpp,
        '         + "the Stockfish developers (see AUTHORS file)";\n',
        '         + "Stockless contributors; based on Stockfish and Reckless";\n',
    )

    replace_once(makefile, "\tEXE = stockfish.exe\n", "\tEXE = stockless.exe\n")
    replace_once(makefile, "\tEXE = stockfish.js\n", "\tEXE = stockless.js\n")
    replace_once(makefile, "\tEXE = stockfish\n", "\tEXE = stockless\n")

    marker = out / "STOCKLESS_MATERIALIZED.txt"
    marker.write_text(
        f"Stockless: {STOCKLESS_VERSION}\n"
        f"Stockfish: {STOCKFISH_SHA}\n"
        f"Reckless reference: {RECKLESS_SHA}\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    materialize(args.out.resolve())
    print(args.out.resolve())


if __name__ == "__main__":
    main()
