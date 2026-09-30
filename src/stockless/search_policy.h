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
    int lmrAdjustment = 0;
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

    pressure += in.givesCheck ? 84 : 0;
    pressure += in.capture ? 30 : 0;
    pressure += in.ttPv ? 18 : 0;
    pressure += in.pvNode ? 14 : 0;

    danger += in.inCheck ? 108 : 0;
    volatility += (3 * in.correctionSignal) / 5;

    if (!in.improving)
        volatility += 16;
    if (in.nextCutoffCount > 2)
        volatility += 20;

    if (!in.capture && !in.givesCheck && in.moveCount > 8
        && in.threat.tacticalVolatility < 144)
        pressure -= 48;

    out.pressure   = std::clamp(pressure, 0, 256);
    out.danger     = std::clamp(danger, 0, 256);
    out.volatility = std::clamp(volatility, 0, 256);

    const int aggression = hybrid_aggression();
    const int tactical =
      std::clamp((3 * out.pressure + 2 * out.danger + 2 * out.volatility) / 7, 0, 256);

    // Base hybrid: strong enough to matter, but still much cheaper than the
    // broad v0.4 Overdrive experiment.
    const int cap = mobile_profile() ? 320 : 640;
    int buyback = tactical * aggression * cap / (256 * 100);

    if (in.cutNode && !in.ttPv && !in.capture && !in.givesCheck && tactical < 152)
        buyback = std::max(0, buyback - 128);

    if (in.window <= 32 && (in.pvNode || in.ttPv))
        buyback += 40;

    // v0.5 Selective Overdrive:
    // never loosen quiet pruning globally. Only verified forcing geometry gets
    // the expensive treatment.
    if (overdrive_enabled() && !mobile_profile())
    {
        const bool forcingCheck = in.givesCheck && out.pressure >= 176;
        const bool kingEmergency = out.danger >= 224;
        const bool forcingCapture = in.capture && out.pressure >= 216 && tactical >= 192;

        if (forcingCheck)
            buyback += 160;
        else if (forcingCapture || kingEmergency)
            buyback += 96;

        if ((forcingCheck || forcingCapture || kingEmergency) && tactical >= 192)
            out.pruningDepthBoost = 1;

        if (forcingCheck && tactical >= 232 && in.depth >= 6)
            out.pruningDepthBoost = 2;

        // No general late-quiet expansion: v0.4 testing showed it wastes nodes.
        out.quietMoveAllowance = 0;

        if (forcingCheck && tactical >= 208)
            out.reSearchDepthBonus = 1;
        else if (forcingCapture && tactical >= 232 && in.pvNode)
            out.reSearchDepthBonus = 1;
    }

    out.lmrAdjustment = -std::min(cap + (overdrive_enabled() ? 192 : 0), buyback);
    return out;
}

} // namespace Stockfish::Stockless
