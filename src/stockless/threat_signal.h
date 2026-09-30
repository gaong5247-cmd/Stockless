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

inline Bitboard attacks_for(const Position& pos, Color c) noexcept {
    return pos.attacks_by<PAWN>(c) | pos.attacks_by<KNIGHT>(c) | pos.attacks_by<BISHOP>(c)
         | pos.attacks_by<ROOK>(c) | pos.attacks_by<QUEEN>(c);
}

inline ThreatSignal compute_threat_signal(const Position& pos,
                                          int             depth,
                                          bool            importantNode) noexcept {
    ThreatSignal out{};

    if (!hybrid_enabled() || !threats_enabled())
        return out;

    // Full attack maps are useful but not free. Android gets the stricter gate
    // to preserve NPS/battery life. Deep/important nodes still receive it.
    const int minDepth = mobile_profile() ? 7 : 5;
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

    // pinners(c) are enemy sliders pinning pieces to color c's king.
    const int pinsWeCreate = popcount(pos.pinners(them));
    const int pinsWeSuffer = popcount(pos.pinners(us));

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
