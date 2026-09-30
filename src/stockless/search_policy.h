#pragma once

#include <algorithm>

#include "config.h"
#include "threat_signal.h"

namespace Stockfish::Stockless {

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

    // Negative means less reduction / deeper LMR search.
    int lmrAdjustment = 0;

    // v0.4 Overdrive: temporarily relax Stockfish pruning in tactical nodes.
    int pruningDepthBoost = 0;
    int quietMoveAllowance = 0;
    int reSearchDepthBonus = 0;
};

inline SearchPolicy make_search_policy(const SearchInputs& in) noexcept {
    SearchPolicy out{};

    if (!hybrid_enabled())
        return out;

    int pressure = in.threat.attackPressure;
    int danger = in.threat.kingDanger;
    int volatility = in.threat.tacticalVolatility;

    pressure += in.givesCheck ? 92 : 0;
    pressure += in.capture ? 34 : 0;
    pressure += in.ttPv ? 20 : 0;
    pressure += in.pvNode ? 18 : 0;

    danger += in.inCheck ? 112 : 0;

    // Reckless-style correction-history sensitivity.
    volatility += (3 * in.correctionSignal) / 5;

    if (!in.improving)
        volatility += 18;

    if (in.nextCutoffCount > 2)
        volatility += 24;

    // Do not waste nodes on late quiets unless the board itself is tactically hot.
    if (!in.capture && !in.givesCheck && in.moveCount > 8
        && in.threat.tacticalVolatility < 128)
        pressure -= 44;

    out.pressure   = std::clamp(pressure, 0, 256);
    out.danger     = std::clamp(danger, 0, 256);
    out.volatility = std::clamp(volatility, 0, 256);

    const int aggression = hybrid_aggression();
    const int tactical =
      std::clamp((3 * out.pressure + 2 * out.danger + 2 * out.volatility) / 7, 0, 256);

    // v0.4 allows substantially more depth on desktop, while mobile remains conservative.
    const int cap = mobile_profile() ? 384 : 768;
    int buyback = tactical * aggression * cap / (256 * 100);

    if (in.givesCheck)
        buyback += 96;

    if (in.capture && out.pressure >= 160)
        buyback += 64;

    // Preserve Stockfish's defensive cut-node shape when the node is not forcing.
    if (in.cutNode && !in.ttPv && !in.capture && !in.givesCheck && tactical < 144)
        buyback = std::max(0, buyback - 128);

    if (in.window <= 32 && (in.pvNode || in.ttPv))
        buyback += 48;

    out.lmrAdjustment = -std::min(cap, buyback);

    if (overdrive_enabled() && !mobile_profile())
    {
        // Boost the effective pruning depth. Larger lmrDepth means fewer
        // futility/SEE prunes in Stockfish's Step 15.
        out.pruningDepthBoost = tactical >= 144 ? 1 : 0;
        if (tactical >= 216 && (in.givesCheck || in.capture || out.danger >= 192))
            out.pruningDepthBoost = 2;

        // Give tactical quiet moves a few more slots before skip_quiet_moves().
        if (!in.capture && !in.givesCheck)
            out.quietMoveAllowance = tactical >= 176 ? 2 : tactical >= 128 ? 1 : 0;

        // If an LMR probe already fails high, forcing/high-volatility moves
        // deserve one extra full-depth verification ply.
        if ((in.givesCheck || in.capture || in.pvNode) && tactical >= 192)
            out.reSearchDepthBonus = 1;
    }

    return out;
}

} // namespace Stockfish::Stockless
