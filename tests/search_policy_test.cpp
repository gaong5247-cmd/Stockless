// Regression harness for the hot-path option snapshot refactor.
// Compile against the materialized Stockless source tree.
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iostream>

#include "stockless_core/search_policy.h"

using namespace Stockfish::Stockless;

static_assert(sizeof(SearchPolicy) == 3 * sizeof(int), "compact policy must hold exactly the three search outputs");

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

    const int boundedPressure = std::clamp(pressure, 0, 256);
    const int boundedDanger = std::clamp(danger, 0, 256);
    const int boundedVolatility = std::clamp(volatility, 0, 256);

    const int tactical =
      std::clamp((3 * boundedPressure + 2 * boundedDanger + 2 * boundedVolatility) / 7, 0, 256);
    const int cap = settings.mobile ? 320 : 640;
    int buyback = tactical * settings.aggression * cap / (256 * 100);
    if (in.cutNode && !in.ttPv && !in.capture && !in.givesCheck && tactical < 152)
        buyback = std::max(0, buyback - 128);
    if (in.window <= 32 && (in.pvNode || in.ttPv))
        buyback += 40;

    if (settings.overdrive && !settings.mobile) {
        const bool forcingCheck = in.givesCheck && boundedPressure >= 176;
        const bool kingEmergency = boundedDanger >= 224;
        const bool forcingCapture = in.capture && boundedPressure >= 216 && tactical >= 192;
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
        assert(actual.lmrAdjustment <= 0);
        assert(actual.pruningDepthBoost >= 0 && actual.pruningDepthBoost <= 2);
        assert(actual.reSearchDepthBonus >= 0 && actual.reSearchDepthBonus <= 1);
    }
    std::cout << "Search policy snapshots: 100000 reference checks passed\n";
}
