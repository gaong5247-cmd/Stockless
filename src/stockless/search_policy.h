#pragma once

#include <algorithm>

#include "config.h"
#include "threat_signal.h"

namespace Stockfish::Stockless {

struct SearchInputs {
    int depth;
    int moveCount;
    int window;
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
    int reSearchDepthBonus = 0;
};

inline SearchPolicy make_search_policy(const SearchInputs& in,
                                       const SearchSettings& settings) noexcept {
    SearchPolicy out{};

    if (!settings.hybrid)
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

    const int aggression = settings.aggression;
    const int tactical =
      std::clamp((3 * out.pressure + 2 * out.danger + 2 * out.volatility) / 7, 0, 256);

    // Base hybrid: strong enough to matter, but still much cheaper than the
    // broad v0.4 Overdrive experiment.
    const int cap = settings.mobile ? 320 : 640;
    int buyback = tactical * aggression * cap / (256 * 100);

    if (in.cutNode && !in.ttPv && !in.capture && !in.givesCheck && tactical < 152)
        buyback = std::max(0, buyback - 128);

    if (in.window <= 32 && (in.pvNode || in.ttPv))
        buyback += 40;

    // v0.5 Selective Overdrive:
    // never loosen quiet pruning globally. Only verified forcing geometry gets
    // the expensive treatment.
    if (settings.overdrive && !settings.mobile)
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

        if (forcingCheck && tactical >= 208)
            out.reSearchDepthBonus = 1;
        else if (forcingCapture && tactical >= 232 && in.pvNode)
            out.reSearchDepthBonus = 1;
    }

    out.lmrAdjustment = -std::min(cap + (settings.overdrive ? 192 : 0), buyback);

    // v0.8 experimental modes: rebalance, rather than replace, pinned Stockfish's
    // native late-move reductions. The legacy mode (0) is precisely v0.7.
    // No extra pruning-depth or re-search extensions are introduced here.
    if (settings.profile != 0)
    {
        const bool quiet = !in.capture && !in.givesCheck;
        const bool principal = in.pvNode || in.ttPv;
        const bool urgent = in.inCheck || out.danger >= 192;
        int budget = -out.lmrAdjustment;

        if (settings.profile == 1)
        {
            // Economy: spend fewer nodes on late non-forcing, non-PV moves.
            if (quiet && !principal && !urgent)
            {
                budget = in.moveCount >= 9 ? budget / 3 : budget * 2 / 3;
                if (in.cutNode)
                    budget = budget * 3 / 4;
            }
            if (in.givesCheck && in.depth >= 6)
                budget += 128;
        }
        else if (settings.profile == 2)
        {
            // Defense: prioritize king emergencies and threatened material,
            // while giving back budget when threats have subsided.
            if (urgent && in.depth >= 5)
                budget += principal ? 128 : 96;
            else if (quiet && !principal && in.moveCount >= 6)
                budget /= 2;

            if (in.capture && out.pressure >= 160 && in.depth >= 5)
                budget += 80;
        }
        else if (settings.profile == 3)
        {
            // Mixed profile: aggressive late-quiet economy, but retain
            // scrutiny for checks, forcing captures and emergency defense.
            if (quiet && !principal && out.danger < 176)
            {
                budget = in.moveCount >= 10 ? budget * 2 / 5 : budget * 3 / 4;
                if (in.cutNode)
                    budget = std::min(budget, 192);
            }
            if (in.givesCheck && in.depth >= 6)
                budget += 120;
            else if (in.capture && out.pressure >= 192 && in.depth >= 6)
                budget += 96;
            if (in.inCheck && in.depth >= 5)
                budget += 72;
        }
        out.lmrAdjustment =
          -std::clamp(budget, 0, cap + (settings.overdrive ? 192 : 0));
    }
    return out;
}

} // namespace Stockfish::Stockless
