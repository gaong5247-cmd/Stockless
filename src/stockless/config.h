#pragma once

#include <algorithm>
#include <atomic>

namespace Stockfish::Stockless {

inline constexpr const char* Version = "0.3-dev";

#if defined(__ANDROID__)
inline constexpr bool DefaultMobileProfile = true;
#else
inline constexpr bool DefaultMobileProfile = false;
#endif

inline std::atomic_bool HybridEnabled{true};
inline std::atomic_bool ThreatsEnabled{true};
inline std::atomic_bool MobileProfile{DefaultMobileProfile};
inline std::atomic_int  HybridAggression{100};

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

} // namespace Stockfish::Stockless
