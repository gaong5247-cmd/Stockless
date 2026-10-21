// Regression harness for the hot-path option snapshot refactor.
// Compile against the materialized Stockless source tree.
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iostream>

#include "stockless_core/search_policy.h"

using namespace Stockfish::Stockless;

// Independent frozen v0.7 formula. Changes to policy must not silently
// change playing decisions when moving atomic reads outside the move loop.
SearchPolicy reference_policy(const SearchInputs& in, const SearchSettings& settings) {
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

    if (!in.improving) volatility += 16;
    if (in.nextCutoffCount > 2) volatility += 20;
    if (!in.capture && !in.givesCheck && in.moveCount > 8
        && in.threat.tacticalVolatility < 144)
        pressure -= 48;

    out.pressure = std::clamp(pressure, 0, 256);
    out.danger = std::clamp(danger, 0, 256);
    out.volatility = std::clamp(volatility, 0, 256);

    const int tactical =
      std::clamp((3 * out.pressure + 2 * out.danger + 2 * out.volatility) / 7, 0, 256);
    const int cap = settings.mobile ? 320 : 640;
    int buyback = tactical * settings.aggression * cap / (256 * 100);
    if (in.cutNode && !in.ttPv && !in.capture && !in.givesCheck && tactical < 152)
        buyback = std::max(0, buyback - 128);
    if (in.window <= 32 && (in.pvNode || in.ttPv))
        buyback += 40;

    if (settings.overdrive && !settings.mobile) {
        const bool forcingCheck = in.givesCheck && out.pressure >= 176;
        const bool kingEmergency = out.danger >= 224;
        const bool forcingCapture = in.capture && out.pressure >= 216 && tactical >= 192;
        if (forcingCheck) buyback += 160;
        else if (forcingCapture || kingEmergency) buyback += 96;
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
    return out;
}

void same(const SearchPolicy& a, const SearchPolicy& b) {
    assert(a.pressure == b.pressure);
    assert(a.danger == b.danger);
    assert(a.volatility == b.volatility);
    assert(a.lmrAdjustment == b.lmrAdjustment);
    assert(a.pruningDepthBoost == b.pruningDepthBoost);
    assert(a.reSearchDepthBonus == b.reSearchDepthBonus);
}

int main() {
    // Check the actual UCI atomic storage->snapshot bridge first.
    set_hybrid_enabled(false);
    assert(!search_settings().hybrid);
    set_hybrid_enabled(true);
    set_threats_enabled(false);
    set_overdrive_enabled(true);
    set_mobile_profile(true);
    set_hybrid_aggression(145);
    const SearchSettings stored = search_settings();
    assert(stored.hybrid && !stored.threats && stored.overdrive
           && stored.mobile && stored.aggression == 145);

    // Deterministically cover both optional modes, mobile mode, depth,
    // checks/captures, tactical signal values and alpha-beta windows.
    std::uint32_t seed = 0x53746f63u;
    auto next = [&]() {
        seed = seed * 1664525u + 1013904223u;
        return seed;
    };
    for (int i = 0; i < 100000; ++i) {
        SearchSettings settings{bool((next() >> 17) & 1), bool((next() >> 17) & 1),
                                bool((next() >> 17) & 1), bool((next() >> 17) & 1),
                                int(next() % 201)};
        SearchInputs in{
            int(next() % 42) + 1, int(next() % 64) + 1,
            int(next() % 300), int(next() % 257), int(next() % 8),
            bool((next() >> 17) & 1), bool((next() >> 17) & 1), bool((next() >> 17) & 1),
            bool((next() >> 17) & 1), bool((next() >> 17) & 1), bool((next() >> 17) & 1),
            bool((next() >> 17) & 1),
            {int(next() % 257), int(next() % 257), int(next() % 257)}
        };
        const auto actual = make_search_policy(in, settings);
        same(actual, reference_policy(in, settings));

        // A single prepared node is reused for multiple *different* moves.
        // alpha/window, next-ply cutoff count and ss->ttPv may mutate after one
        // of those moves is searched: do not cache them in the node.
        const auto prepared = prepare_search_policy(
            {in.depth, in.correctionSignal, in.improving, in.inCheck,
             in.pvNode, in.cutNode, in.threat}, settings);
        const auto preparedMove = [&](const SearchInputs& m) {
            return make_prepared_move_policy(
                prepared, m.moveCount, m.window, m.nextCutoffCount,
                m.ttPv, m.capture, m.givesCheck);
        };
        same(preparedMove(in), reference_policy(in, settings));

        SearchInputs secondMove = in;
        secondMove.moveCount = (in.moveCount % 64) + 1;
        secondMove.window = (in.window + 157) % 300;
        secondMove.nextCutoffCount = (in.nextCutoffCount + 5) % 8;
        secondMove.capture = !in.capture;
        secondMove.givesCheck = !in.givesCheck;
        // Regression: singular verification may mutate ttPv in the same
        // Stack between two move policy evaluations.
        secondMove.ttPv = !in.ttPv;
        same(preparedMove(secondMove), reference_policy(secondMove, settings));

        assert(actual.lmrAdjustment <= 0);
        assert(actual.pruningDepthBoost >= 0 && actual.pruningDepthBoost <= 2);
        assert(actual.reSearchDepthBonus >= 0 && actual.reSearchDepthBonus <= 1);
    }
    std::cout << "Search policy: 200000 prepared-move and 100000 single-call checks passed\n";
}
