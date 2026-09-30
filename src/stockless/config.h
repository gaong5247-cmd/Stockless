#pragma once

#include <atomic>
#include <algorithm>

namespace Stockfish::Stockless {

inline std::atomic_bool HybridEnabled{false};
inline std::atomic_int HybridAggression{100};

inline void set_hybrid_enabled(bool value) noexcept {
    HybridEnabled.store(value, std::memory_order_relaxed);
}

inline bool hybrid_enabled() noexcept {
    return HybridEnabled.load(std::memory_order_relaxed);
}

inline void set_hybrid_aggression(int value) noexcept {
    HybridAggression.store(std::clamp(value, 0, 200), std::memory_order_relaxed);
}

inline int hybrid_aggression() noexcept {
    return HybridAggression.load(std::memory_order_relaxed);
}

} // namespace Stockfish::Stockless
