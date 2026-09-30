#pragma once

#include <algorithm>
#include <cstdlib>

#include "config.h"

namespace Stockfish::Stockless {

// SearchPolicy is intentionally independent from Position/Move so the hybrid layer
// stays cheap, deterministic and easy to A/B test.
struct SearchInputs {
    int  depth;
    int  moveCount;
    int  window;
    int  staticEval;
    int  alpha;
    int  beta;
    bool improving;
    bool capture;
    bool givesCheck;
    bool inCheck;
    bool ttPv;
};

struct SearchPolicy {
    int pressure = 0;       // 0..256: tactical opportunity / forcing nature
    int danger = 0;         // 0..256: instability / defensive urgency
    int lmrAdjustment = 0;  // Stockfish reduction units; negative = search deeper
};

// Phase-1 controller:
// - OFF by default, therefore baseline behavior is unchanged.
// - Uses only facts Stockfish has already computed.
// - Never changes the static evaluation.
// - Initially adjusts LMR only; pruning integration comes after independent tests.
inline SearchPolicy make_search_policy(const SearchInputs& in) noexcept {
    SearchPolicy out{};

    if (!hybrid_enabled())
        return out;

    int pressure = 0;
    pressure += in.givesCheck ? 112 : 0;
    pressure += in.capture ? 48 : 0;
    pressure += in.ttPv ? 20 : 0;
    pressure += in.window <= 32 ? 12 : 0;
    pressure += in.depth >= 8 ? 12 : 0;

    int danger = 0;
    danger += in.inCheck ? 128 : 0;

    // Failing-low-ish static positions deserve a little more defensive care.
    if (!in.inCheck && in.staticEval < in.alpha)
        danger += std::min(64, (in.alpha - in.staticEval) / 4);

    // Late quiet moves are exactly where normal LMR is most useful, so do not
    // erase the backbone. Stockless only buys depth back when forcing signals
    // are strong enough.
    if (!in.capture && !in.givesCheck && in.moveCount > 8)
        pressure -= 28;

    if (in.improving)
        pressure += 8;

    out.pressure = std::clamp(pressure, 0, 256);
    out.danger   = std::clamp(danger, 0, 256);

    const int aggression = hybrid_aggression();
    const int tactical = (out.pressure * 3 + out.danger * 2) / 5;

    // 1024 Stockfish reduction units are roughly one ply. Keep phase 1 capped
    // at 3/8 ply so the experimental controller cannot bulldoze tuned LMR.
    out.lmrAdjustment = -std::min(384, tactical * aggression * 384 / (256 * 100));

    return out;
}

} // namespace Stockfish::Stockless
