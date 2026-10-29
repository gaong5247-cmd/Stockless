#!/usr/bin/env python3
"""Opt-in training probe for Stockless's pinned Stockfish source.

Run AFTER tools/materialize.py, BEFORE compiling. The stock NNUE architecture,
quantized layers, inference output, and on-disk file format remain unchanged.
The added UCI debug command exposes the exact final-layer inputs for training.
"""
from pathlib import Path
import argparse


def replace_once(path, anchor, replacement):
    source = path.read_text(encoding="utf-8")
    if source.count(anchor) != 1:
        raise RuntimeError(f"{path}: expected one exact anchor; found {source.count(anchor)}")
    path.write_text(source.replace(anchor, replacement, 1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=Path("build/stockless-src/src"))
    args = ap.parse_args()
    src = args.source
    if not (src / "nnue/nnue_architecture.h").exists():
        raise SystemExit("First run python tools/materialize.py")
    arch = (src / "nnue/nnue_architecture.h").read_text(encoding="utf-8")
    if "using PSQFeatureSet    = Features::HalfKAv2_hm;" not in arch or "constexpr IndexType LayerStacks = 8;" not in arch:
        raise SystemExit("UNSUPPORTED architecture: pinned HalfKAv2_hm / 8 buckets required")
    replace_once(
        src / "nnue/network.h",
        "    NnueEvalTrace trace_evaluate(const Position&    pos,",
        "    std::string stockless_training_features(const Position&, AccumulatorStack&, AccumulatorCaches&) const;\n\n"
        "    NnueEvalTrace trace_evaluate(const Position&    pos,",
    )
    impl = r'''
// Training-only side-channel: same upstream feature transformer / hidden layers.
// Does not replace or change NetworkArchitecture::propagate().
std::string Network::stockless_training_features(
    const Position& pos, AccumulatorStack& stack, AccumulatorCaches& cache) const {
    alignas(CacheLineSize) TransformedFeatureType transformed[FeatureTransformer::BufferSize];
    NNZInfo<L1> nz;
    const int bucket = (pos.count<ALL_PIECES>() - 1) / 4;
    const int psqt = featureTransformer.transform(pos, stack, cache, transformed, bucket, nz);
    const auto& n = network[bucket];

    alignas(CacheLineSize) decltype(n.fc_0)::OutputBuffer a0{};
    alignas(CacheLineSize) decltype(n.fc_1)::OutputBuffer a1{};
    alignas(CacheLineSize) decltype(n.fc_2)::OutputBuffer a2{};
    alignas(CacheLineSize) u8 joined[128]{};
    n.fc_0.propagate(transformed, a0, nz);
#if defined(USE_PAIR_ACTIVATIONS)
    n.ac_sqr_0.propagate_pair(a0, joined, joined + 32);
#else
    n.ac_sqr_0.propagate(a0, joined);
    n.ac_0.propagate(a0, joined + 32);
#endif
    n.fc_1.propagate(joined, a1);
#if defined(USE_PAIR_ACTIVATIONS)
    n.ac_sqr_1.propagate_pair(a1, joined + 64, joined + 96);
#else
    n.ac_sqr_1.propagate(a1, joined + 64);
    n.ac_1.propagate(a1, joined + 96);
#endif
    n.fc_2.propagate(joined, a2);
    const int skip = a0[30] - a0[31];
    const int positional = static_cast<int>(
        (static_cast<i64>(a2[0] + skip) * (600 * OutputScale)) /
        (static_cast<i64>(HiddenOneVal) * (1U << WeightScaleBits) * 2));
    const int raw = psqt / OutputScale + positional / OutputScale;
    std::ostringstream out;
    out << "stockless_features " << bucket << ' ' << psqt << ' '
        << skip << ' ' << raw << ' ';
    for (int i = 0; i < 128; ++i) {
        if (i) out << ',';
        out << int(joined[i]);
    }
    return out.str();
}

'''
    netcpp = src / "nnue/network.cpp"
    replace_once(netcpp, '#include <optional>\n', '#include <optional>\n#include <sstream>\n')
    replace_once(netcpp, 'void Network::verify(', impl + 'void Network::verify(')
    replace_once(
        src / "engine.h",
        '    void trace_eval() const;\n',
        '    void trace_eval() const;\n    void stockless_training_features() const;\n',
    )
    engine_impl = r'''
void Engine::stockless_training_features() const {
    StateListPtr trace_states(new std::deque<StateInfo>(1));
    Position p;
    p.set(pos.fen(), options["UCI_Chess960"], &trace_states->back());
    verify_network();
    auto stack = std::make_unique<Eval::NNUE::AccumulatorStack>();
    auto cache = std::make_unique<Eval::NNUE::AccumulatorCaches>(*network);
    sync_cout << network->stockless_training_features(p, *stack, *cache) << sync_endl;
}

'''
    replace_once(src / "engine.cpp", 'void Engine::trace_eval() const {', engine_impl + 'void Engine::trace_eval() const {')
    replace_once(
        src / "uci.cpp",
        '        else if (token == "eval")\n            engine.trace_eval();',
        '        else if (token == "eval")\n            engine.trace_eval();\n'
        '        else if (token == "stockless_features")\n            engine.stockless_training_features();',
    )
    print("Training probe installed; compile this materialized source with your normal Makefile.")


if __name__ == "__main__":
    main()
