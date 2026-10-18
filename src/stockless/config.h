#pragma once

#include <algorithm>
#include <atomic>

namespace Stockfish::Stockless {

inline constexpr const char* Version = "v0.8.1-dev.20261018.1";

#if defined(__ANDROID__)
inline constexpr bool DefaultMobileProfile = true;
#else
inline constexpr bool DefaultMobileProfile = false;
#endif

// v0.7 keeps the established hybrid path on by default, but Selective Overdrive is
// opt-in until match testing proves it. Android stays conservative as well.
inline constexpr bool DefaultOverdrive = false;

// New threat-conditioned history stays opt-in until fixed-time SPRT tests.
inline constexpr bool DefaultThreatHistory = false;
inline constexpr int  DefaultThreatHistoryWeight = 100;

// Established aggression preset. Keep the UCI default and runtime
// storage tied to one constant so GUI/UCI startup cannot silently diverge.
inline constexpr int DefaultHybridAggression = 145;

// Zero keeps the byte-for-byte v0.7 search policy; 1-3 are unproven A/B candidates.
inline constexpr int DefaultSearchProfile = 0;

inline std::atomic_bool HybridEnabled{true};
inline std::atomic_bool ThreatsEnabled{true};
inline std::atomic_bool OverdriveEnabled{DefaultOverdrive};
inline std::atomic_bool MobileProfile{DefaultMobileProfile};
inline std::atomic_int  HybridAggression{DefaultHybridAggression};
inline std::atomic_int  SearchProfile{DefaultSearchProfile};
inline std::atomic_bool ThreatHistoryEnabled{DefaultThreatHistory};
inline std::atomic_int  ThreatHistoryWeight{DefaultThreatHistoryWeight};

inline void set_hybrid_enabled(bool value) noexcept {
    HybridEnabled.store(value, std::memory_order_relaxed);
}
inline bool hybrid_enabled() noexcept {
    return HybridEnabled.load(std::memory_order_relaxed);
}

inline void set_threats_enabled(bool value) noexcept {
    ThreatsEnabled.store(value, std::memory_order_relaxed);
}
inline bool threats_enabled() noexcept {
    return ThreatsEnabled.load(std::memory_order_relaxed);
}

inline void set_overdrive_enabled(bool value) noexcept {
    OverdriveEnabled.store(value, std::memory_order_relaxed);
}
inline bool overdrive_enabled() noexcept {
    return OverdriveEnabled.load(std::memory_order_relaxed);
}
inline constexpr bool default_overdrive() noexcept {
    return DefaultOverdrive;
}

inline void set_mobile_profile(bool value) noexcept {
    MobileProfile.store(value, std::memory_order_relaxed);
}
inline bool mobile_profile() noexcept {
    return MobileProfile.load(std::memory_order_relaxed);
}
inline constexpr bool default_mobile_profile() noexcept {
    return DefaultMobileProfile;
}

inline void set_hybrid_aggression(int value) noexcept {
    HybridAggression.store(std::clamp(value, 0, 200), std::memory_order_relaxed);
}
inline int hybrid_aggression() noexcept {
    return HybridAggression.load(std::memory_order_relaxed);
}
inline constexpr int default_hybrid_aggression() noexcept {
    return DefaultHybridAggression;
}

inline void set_threat_history_enabled(bool value) noexcept {
    ThreatHistoryEnabled.store(value, std::memory_order_relaxed);
}
inline bool threat_history_enabled() noexcept {
    return hybrid_enabled() && ThreatHistoryEnabled.load(std::memory_order_relaxed);
}
inline constexpr bool default_threat_history() noexcept {
    return DefaultThreatHistory;
}

inline void set_threat_history_weight(int value) noexcept {
    ThreatHistoryWeight.store(std::clamp(value, 0, 200), std::memory_order_relaxed);
}
inline int threat_history_weight() noexcept {
    return ThreatHistoryWeight.load(std::memory_order_relaxed);
}
inline constexpr int default_threat_history_weight() noexcept {
    return DefaultThreatHistoryWeight;
}

inline void set_search_profile(int value) noexcept {
    SearchProfile.store(std::clamp(value, 0, 3), std::memory_order_relaxed);
}
inline int search_profile() noexcept {
    return SearchProfile.load(std::memory_order_relaxed);
}
inline constexpr int default_search_profile() noexcept {
    return DefaultSearchProfile;
}

// UCI option state is stable for a search. Snapshot its atomics once per
// node, rather than reloading them for every legal move. Never mutate this
// snapshot during search; UCI setoption must be applied between searches.
struct SearchSettings {
    bool hybrid;
    bool threats;
    bool overdrive;
    bool mobile;
    int aggression;
    int profile = 0;
};

inline SearchSettings search_settings() noexcept {
    const bool hybrid = hybrid_enabled();
    if (!hybrid)
        return {false, false, false, false, 0, 0};

    return {true, threats_enabled(), overdrive_enabled(), mobile_profile(),
            hybrid_aggression(), search_profile()};
}

} // namespace Stockfish::Stockless
