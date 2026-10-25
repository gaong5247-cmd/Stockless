// Regression for pin ownership in the real, pinned Stockfish Position API.
// Build against a materialized source tree; no NNUE weights are required.
#include <cstdlib>
#include <iostream>
#include <string>

#include "stockless_core/threat_signal.h"

using namespace Stockfish;
using namespace Stockfish::Stockless;

namespace {

void require(bool condition, const std::string& message) {
    if (!condition)
    {
        std::cerr << message << '\n';
        std::exit(EXIT_FAILURE);
    }
}

void check_pin(const std::string& fen, Color pinnerSide, Square pinnerSquare,
               bool sideToMoveCreatesPin) {
    Position pos;
    StateInfo state{};
    const auto error = pos.set(fen, false, &state);
    require(!error, "Invalid regression FEN: " + fen);

    // Establish ownership from board geometry before checking derived scores:
    // the rook belongs to pinnerSide and pins the enemy knight to its king.
    require(pos.pinners(pinnerSide) == square_bb(pinnerSquare),
            "Position::pinners must be indexed by the attacking slider's color");
    require(pos.pinners(~pinnerSide) == 0, "Unexpected reverse pin");

    const SearchSettings settings{true, true, false, false, 145};
    const auto signal = compute_threat_signal(pos, 5, false, settings);

    // The rook attacks the knight on a square adjacent to the enemy king.
    // The knight attacks no enemy piece or enemy king-zone square.
    // Creating a pin contributes 24 attack points; suffering it adds 28 danger.
    require(signal.attackPressure == (sideToMoveCreatesPin ? 72 : 0),
            "Pin assigned to the wrong attack-pressure side: " + fen);
    require(signal.kingDanger == (sideToMoveCreatesPin ? 0 : 82),
            "Pin assigned to the wrong king-danger side: " + fen);
    require(signal.tacticalVolatility == 46,
            "Pin ownership must not change total tactical contacts: " + fen);
}

}  // namespace

int main() {
    Attacks::init();
    Position::init();

    check_pin("4k3/4n3/8/8/8/8/8/K3R3 w - - 0 1", WHITE, SQ_E1, true);
    check_pin("4k3/4n3/8/8/8/8/8/K3R3 b - - 0 1", WHITE, SQ_E1, false);
    check_pin("k3r3/8/8/8/8/8/4N3/4K3 b - - 0 1", BLACK, SQ_E8, true);
    check_pin("k3r3/8/8/8/8/8/4N3/4K3 w - - 0 1", BLACK, SQ_E8, false);

    std::cout << "Threat pin ownership: four color/perspective regressions passed\n";
}
