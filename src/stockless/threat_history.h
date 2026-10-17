#pragma once

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdlib>

#include "../bitboard.h"
#include "../types.h"

namespace Stockfish::Stockless {

// Experimental, per-Worker quiet history inspired by Reckless 0.10-dev.
// Each from/to move has a common component plus one of four buckets:
//   [from attacked by the opponent][to attacked by the opponent].
//
// This is intentionally separate from Stockfish's tuned mainHistory, and
// does not require a second NNUE. Only the owning search worker may write it.
class ThreatQuietHistory {
   public:
    static constexpr int FactorizerLimit = 1852;
    static constexpr int BucketLimit     = 6324;

    int get(Bitboard enemyAttacks, Color side, Move move) const noexcept {
        const Entry& entry = entries[index(side, move)];
        return int(entry.factorizer)
             + int(entry.buckets[bool(enemyAttacks & move.from_sq())]
                                 [bool(enemyAttacks & move.to_sq())]);
    }

    void update(Bitboard enemyAttacks, Color side, Move move, int bonus) noexcept {
        Entry& entry = entries[index(side, move)];
        const bool fromAttacked = bool(enemyAttacks & move.from_sq());
        const bool toAttacked   = bool(enemyAttacks & move.to_sq());

        apply_bonus(entry.factorizer, bonus, FactorizerLimit);
        apply_bonus(entry.buckets[fromAttacked][toAttacked], bonus, BucketLimit);
    }

    void age() noexcept {
        for (Entry& entry : entries)
        {
            entry.factorizer = std::int16_t(int(entry.factorizer) * 3 / 4);
            for (auto& row : entry.buckets)
                for (std::int16_t& bucket : row)
                    bucket = std::int16_t(int(bucket) * 3 / 4);
        }
    }

    void clear() noexcept { entries.fill(Entry{}); }

   private:
    struct Entry {
        std::int16_t factorizer = 0;
        std::int16_t buckets[2][2] = {};
    };

    static constexpr std::size_t index(Color side, Move move) noexcept {
        return (std::size_t(side) * SQUARE_NB + std::size_t(move.from_sq())) * SQUARE_NB
             + std::size_t(move.to_sq());
    }

    static void apply_bonus(std::int16_t& entry, int bonus, int limit) noexcept {
        const int b = std::clamp(bonus, -limit, limit);
        const int v = int(entry);
        entry = std::int16_t(std::clamp(v + b - v * std::abs(b) / limit, -limit, limit));
    }

    std::array<Entry, COLOR_NB * SQUARE_NB * SQUARE_NB> entries{};
};

}  // namespace Stockfish::Stockless
