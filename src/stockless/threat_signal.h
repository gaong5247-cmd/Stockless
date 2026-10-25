#pragma once

#include <algorithm>

#include "../attacks.h"
#include "../bitboard.h"
#include "../position.h"
#include "../types.h"
#include "config.h"

namespace Stockfish::Stockless {

// v0.3 bridge toward Reckless-style threat features.
// This is intentionally not a second NNUE. It extracts three bounded signals
// from Stockfish's board state and lets the search policy decide how much
// additional depth is worth spending.
struct ThreatSignal {
    int attackPressure = 0;
    int kingDanger = 0;
    int tacticalVolatility = 0;
};

// Exact attack-map fastpath: load occupied squares once, then group the
// slider attack loops. Queens participate in *both* bishop and rook rays,
// matching Position::attacks_by<QUEEN>() without an extra queen dispatch.
// Knights are occupancy independent. No king attacks were present in v0.7.
inline Bitboard attacks_for(const Position& pos, Color c) noexcept {
    Bitboard attacks = pos.attacks_by<PAWN>(c);
    const Bitboard occupied = pos.pieces();

    Bitboard knights = pos.pieces(c, KNIGHT);
    while (knights)
        attacks |= Attacks::attacks_bb(KNIGHT, pop_lsb(knights));

    Bitboard diagonals = pos.pieces(c, BISHOP, QUEEN);
    while (diagonals)
        attacks |= Attacks::attacks_bb(BISHOP, pop_lsb(diagonals), occupied);

    Bitboard orthogonals = pos.pieces(c, ROOK, QUEEN);
    while (orthogonals)
        attacks |= Attacks::attacks_bb(ROOK, pop_lsb(orthogonals), occupied);

    return attacks;
}

inline ThreatSignal compute_threat_signal(const Position&      pos,
                                          int                  depth,
                                          bool                 importantNode,
                                          const SearchSettings& settings) noexcept {
    ThreatSignal out{};

    if (!settings.hybrid || !settings.threats)
        return out;

    // Full attack maps are useful but not free. Android gets the stricter gate
    // to preserve NPS/battery life. Deep/important nodes still receive it.
    const int minDepth = settings.mobile ? 7 : 5;
    if (depth < minDepth && !importantNode)
        return out;

    const Color us   = pos.side_to_move();
    const Color them = ~us;

    const Bitboard ourAttacks   = attacks_for(pos, us);
    const Bitboard theirAttacks = attacks_for(pos, them);

    const Square ourKing   = pos.square<KING>(us);
    const Square theirKing = pos.square<KING>(them);

    const Bitboard ourKingZone   = Attacks::attacks_bb(KING, ourKing) | ourKing;
    const Bitboard theirKingZone = Attacks::attacks_bb(KING, theirKing) | theirKing;

    const int kingContactForUs   = popcount(ourAttacks & theirKingZone);
    const int kingContactAgainst = popcount(theirAttacks & ourKingZone);

    const int attackedEnemy = popcount(ourAttacks & pos.pieces(them));
    const int attackedUs    = popcount(theirAttacks & pos.pieces(us));

    // pinners(c) contains sliders of color c pinning pieces to the enemy
    // king (Position::update_slider_blockers stores them under ~kingColor).
    const int pinsWeCreate = popcount(pos.pinners(us));
    const int pinsWeSuffer = popcount(pos.pinners(them));

    out.attackPressure =
      std::clamp(36 * kingContactForUs + 12 * attackedEnemy + 24 * pinsWeCreate, 0, 256);

    out.kingDanger =
      std::clamp(42 * kingContactAgainst + 12 * attackedUs + 28 * pinsWeSuffer, 0, 256);

    const int mutualContacts = attackedEnemy + attackedUs;
    out.tacticalVolatility =
      std::clamp(14 * mutualContacts + 20 * (pinsWeCreate + pinsWeSuffer)
                   + 12 * (kingContactForUs + kingContactAgainst),
                 0, 256);

    return out;
}

} // namespace Stockfish::Stockless
