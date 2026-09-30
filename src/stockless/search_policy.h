#pragma once

#include <algorithm>

#include "config.h"
#include "threat_signal.h"

namespace Stockfish::Stockless {

// v0.2 owns reduction adaptation. v0.3 supplies threat signals.
// The boundary stays explicit so either layer can be benchmarked separately.
struct SearchInputs {
    int depth;
    int moveCount;
    int window;
    int staticEval;
    int alpha;
    int beta;
    int correctionSignal;
    int nextCutoffCount;

    bool improving;
    bool capture;
    bool givesCheck;
    bool inCheck;
    bool ttPv;
    bool pvNode;
    bool cutNode;

    ThreatSignal threat;
};

struct SearchPolicy {
    int pressure = 0;
    int danger = 0;
    int volatility = 0;
    int lmrAdjustment = 0;
};

inline SearchPolicy make_search_policy(const SearchInputs& in) noexcept {
    SearchPolicy out{};

    if (!hybrid_enabled())
        return out;

    int pressure = in.threat.attackPressure;
    int danger = in.threat.kingDanger;
    int volatility = in.threat.tacticalVolatility;

    // Small forcing-context adjustments on top of Stockfish's already-tuned LMR.
    pressure += in.givesCheck ? 72 : 0;
    pressure += in.capture ? 28 : 0;
    pressure += in.ttPv ? 18 : 0;
    pressure += in.pvNode ? 14 : 0;

    danger += in.inCheck ? 96 : 0;

    // Reckless 0.10-dev gives correction history a strong role in reduction.
    // Stockless compresses that idea into a bounded volatility signal.
    volatility += in.correctionSignal / 2;

    if (!in.improving)
        volatility += 16;

    if (in.nextCutoffCount > 2)
        volatility += 20;

    if (!in.capture && !in.givesCheck && in.moveCount > 8)
        pressure -= 36;

    out.pressure   = std::clamp(pressure, 0, 256);
    out.danger     = std::clamp(danger, 0, 256);
    out.volatility = std::clamp(volatility, 0, 256);

    const int aggression = hybrid_aggression();
    const int tactical = (3 * out.pressure + 2 * out.danger + 2 * out.volatility) / 7;

    // 1024 reduction units are roughly one ply.
    // Mobile deliberately buys less depth to limit node growth and heat.
    const int cap = mobile_profile() ? 320 : 512;
    int buyback = tactical * aggression * cap / (256 * 100);

    // Preserve Stockfish's defensive cut-node behavior unless the position is
    // genuinely forcing/tactically unstable.
    if (in.cutNode && !in.ttPv && !in.capture && !in.givesCheck && tactical < 128)
        buyback = std::max(0, buyback - 96);

    if (in.window <= 32 && (in.pvNode || in.ttPv))
        buyback += 32;

    out.lmrAdjustment = -std::min(cap, buyback);
    return out;
}

} // namespace Stockfish::Stockless
