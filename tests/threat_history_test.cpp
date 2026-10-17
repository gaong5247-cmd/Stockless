// Standalone invariants for the Stockless experimental quiet history.
// Run after materialization:
//   c++ -std=c++17 -O2 -Ibuild/stockless-src/src tests/threat_history_test.cpp -o /tmp/threat_history_test
//   /tmp/threat_history_test

#include <cassert>

#include "stockless_core/threat_history.h"

using namespace Stockfish;

int main() {
    Stockless::ThreatQuietHistory history;
    const Move e2e4(SQ_E2, SQ_E4);
    const Move e2e3(SQ_E2, SQ_E3);
    const Bitboard fromAttacked = square_bb(SQ_E2);
    const Bitboard toAttacked   = square_bb(SQ_E4);

    assert(history.get(0, WHITE, e2e4) == 0);
    history.update(fromAttacked, WHITE, e2e4, 1000);

    // The same move has separate threat buckets, but shares a factorizer.
    assert(history.get(fromAttacked, WHITE, e2e4) > history.get(0, WHITE, e2e4));
    assert(history.get(toAttacked, WHITE, e2e4) == history.get(0, WHITE, e2e4));

    // No other move or side should inherit the update.
    assert(history.get(fromAttacked, WHITE, e2e3) == 0);
    assert(history.get(fromAttacked, BLACK, e2e4) == 0);

    for (int i = 0; i < 100; ++i)
        history.update(fromAttacked, WHITE, e2e4, 50000);
    const int upper = history.get(fromAttacked, WHITE, e2e4);
    assert(upper > 0);
    assert(upper <= Stockless::ThreatQuietHistory::FactorizerLimit
                      + Stockless::ThreatQuietHistory::BucketLimit);

    history.age();
    assert(history.get(fromAttacked, WHITE, e2e4) < upper);

    for (int i = 0; i < 100; ++i)
        history.update(fromAttacked, WHITE, e2e4, -50000);
    const int lower = history.get(fromAttacked, WHITE, e2e4);
    assert(lower < 0);
    assert(lower >= -(Stockless::ThreatQuietHistory::FactorizerLimit
                       + Stockless::ThreatQuietHistory::BucketLimit));

    history.clear();
    assert(history.get(fromAttacked, WHITE, e2e4) == 0);
    assert(history.get(0, WHITE, e2e4) == 0);
    return 0;
}
