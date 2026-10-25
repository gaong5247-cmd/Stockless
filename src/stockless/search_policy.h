#pragma once

#include <algorithm>

#include "config.h"
#include "threat_signal.h"

namespace Stockfish::Stockless {

// Stable per-node inputs. Do not cache depth, window, nextCutoffCount or ttPv:
// depth, alpha and the next ply's cutoff count may change between moves;
// a singular search can reuse the same Stack and overwrite ss->ttPv.
struct SearchNodeInputs {
    int correctionSignal;

    bool improving;
    bool inCheck;
    bool pvNode;
    bool cutNode;

    ThreatSignal threat;
};

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

// Prepare only properties that cannot change during this node's move loop.
// The original full policy recomputed these constants for every move that
// survived Stockfish's Step 15 pruning.
struct PreparedSearchPolicy {
    int pressureBase = 0;
    int danger = 0;
    int volatilityBase = 0;
    int threatVolatility = 0;
    int aggression = 0;
    int cap = 0;
    int maxBuyback = 0;

    bool hybrid = false;
    bool pvNode = false;
    bool cutNode = false;
    bool desktopOverdrive = false;
};

inline PreparedSearchPolicy prepare_search_policy(const SearchNodeInputs& in,
                                                   const SearchSettings& settings) noexcept {
    PreparedSearchPolicy out{};

    if (!settings.hybrid)
        return out;

    out.hybrid = true;
    out.pressureBase = in.threat.attackPressure + (in.pvNode ? 14 : 0);
    out.danger = std::clamp(in.threat.kingDanger + (in.inCheck ? 108 : 0), 0, 256);
    out.volatilityBase = in.threat.tacticalVolatility + (3 * in.correctionSignal) / 5;
    if (!in.improving)
        out.volatilityBase += 16;

    out.threatVolatility = in.threat.tacticalVolatility;
    out.aggression = settings.aggression;
    out.cap = settings.mobile ? 320 : 640;
    // Overdrive is a desktop-only feature. Its extra buyback allowance must
    // not bypass the mobile cap when a GUI leaves Overdrive enabled.
    out.desktopOverdrive = settings.overdrive && !settings.mobile;
    out.maxBuyback = out.cap + (out.desktopOverdrive ? 192 : 0);
    out.pvNode = in.pvNode;
    out.cutNode = in.cutNode;
    return out;
}

// Values that can change after a searched move are deliberately passed here.
// Do NOT cache depth, (beta-alpha), (ss+1)->cutoffCnt, or ss->ttPv per node:
// Stockfish reduces depth after alpha improvements; same-ply singular
// verification can also change depth and overwrite ttPv.
inline SearchPolicy make_prepared_move_policy(const PreparedSearchPolicy& base,
                                              int depth,
                                              int moveCount,
                                              int window,
                                              int nextCutoffCount,
                                              bool ttPv,
                                              bool capture,
                                              bool givesCheck) noexcept {
    SearchPolicy out{};

    if (!base.hybrid)
        return out;

    int pressure = base.pressureBase;
    pressure += givesCheck ? 84 : 0;
    pressure += capture ? 30 : 0;
    pressure += ttPv ? 18 : 0;

    if (!capture && !givesCheck && moveCount > 8 && base.threatVolatility < 144)
        pressure -= 48;

    out.pressure = std::clamp(pressure, 0, 256);
    out.danger = base.danger;
    out.volatility = std::clamp(base.volatilityBase + (nextCutoffCount > 2 ? 20 : 0), 0, 256);

    const int tactical =
      std::clamp((3 * out.pressure + 2 * out.danger + 2 * out.volatility) / 7, 0, 256);

    int buyback = tactical * base.aggression * base.cap / (256 * 100);

    if (base.cutNode && !ttPv && !capture && !givesCheck && tactical < 152)
        buyback = std::max(0, buyback - 128);

    if (window <= 32 && (base.pvNode || ttPv))
        buyback += 40;

    if (base.desktopOverdrive)
    {
        const bool forcingCheck = givesCheck && out.pressure >= 176;
        const bool kingEmergency = out.danger >= 224;
        const bool forcingCapture = capture && out.pressure >= 216 && tactical >= 192;

        if (forcingCheck)
            buyback += 160;
        else if (forcingCapture || kingEmergency)
            buyback += 96;

        if ((forcingCheck || forcingCapture || kingEmergency) && tactical >= 192)
            out.pruningDepthBoost = 1;

        if (forcingCheck && tactical >= 232 && depth >= 6)
            out.pruningDepthBoost = 2;

        if (forcingCheck && tactical >= 208)
            out.reSearchDepthBonus = 1;
        else if (forcingCapture && tactical >= 232 && base.pvNode)
            out.reSearchDepthBonus = 1;
    }

    out.lmrAdjustment = -std::min(base.maxBuyback, buyback);
    return out;
}

// Retain a single-call API for tests and other clients; both paths now
// share one formula instead of carrying a second copy of the policy.
inline SearchPolicy make_search_policy(const SearchInputs& in,
                                       const SearchSettings& settings) noexcept {
    const auto prepared = prepare_search_policy(
      {in.correctionSignal, in.improving, in.inCheck,
       in.pvNode, in.cutNode, in.threat},
      settings);
    return make_prepared_move_policy(prepared, in.depth, in.moveCount, in.window,
                                     in.nextCutoffCount, in.ttPv, in.capture, in.givesCheck);
}

} // namespace Stockfish::Stockless
