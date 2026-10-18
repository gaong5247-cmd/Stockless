# Stockless v0.8.6: CPU-native versus portable AVX2 PGO

**Research branch only: no core engine/source removal, new NNUE training, default UCI change or public release.**

Stockless v0.8.2's optional official Stockfish SFNNv18/K32Q2 source `effdc3fd3f6de6e75fe1374a51a7a7eed66f880b` with GCC PGO, aggression 145, ThreatHistory OFF showed **54.6875%** against frozen Stockless v0.7 in a separate 800-game holdout. Estimated Elo +32.67. This was short of the strictly >55% target. v0.8.3 aggression tuning and v0.8.5 low-weight ThreatHistory also failed to beat the 55% independent-holdout gate, and Clang PGO ran about 0.93% slower than GCC PGO on an AMD EPYC 7763 CI CPU.

## Hypothesis

Profile-guided builds targeting exactly the local runner architecture (`ARCH=native`) may be faster than a generic `ARCH=x86-64-avx2` PGO build without changing a single search decision. **This is not guaranteed**; native could choose an ISA that is slower on this AMD host.

## Test controls

- Two independently profiled GCC builds from the same materialized modern Stockless source and the same Stockfish NNUE files
- Pinned original Stockfish and Reckless gitlinks in the repository remain unchanged
- Same runner, 1-thread fixed-depth benchmark, 16 MiB hash, 10 interleaved repetitions at depth 12
- Require **identical node counts**; any mismatch aborts interpretation as pure speed optimization
- Record CPU identity, compiler version, native architecture decision, median NPS, SHA provenance
- Do not distribute the native binary, since a binary compiled for the CI CPU is not universal

If native produces a convincing, repeatable NPS improvement, it becomes a *candidate* for separate equal-clock paired-match confirmation (200-game smoke, >=800 independent games), not an automatic strength boost or new stable release.

The GitHub workflow is `.github/workflows/v086-native-pgo.yml`; download its `Stockless-v086-Native-ISA-Bench` artifact for evidence.