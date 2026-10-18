# Stockless v0.8.4 compiler experiment: GCC PGO vs Clang PGO

**Status: exploratory speed measurement only. No Elo gain or stable build is claimed.**

In modern Stockless v0.8.2, fixed-source PGO versus non-PGO measured higher median NPS (6.40% in one run and 9.27% in another), with exactly matched depth-limited node counts. However the isolated 200-game PGO/non-PGO match scored just 48.50% for PGO, which cannot prove a playing-strength improvement.

This independent experiment compares **two compilers** using the same modern Stockless SFNNv18 evaluation, identical Stockless source code, official Stockfish commit `effdc3fd3f6de6e75fe1374a51a7a7eed66f880b`, the same `ARCH=x86-64-avx2` target and identical profile-build procedure.

- Arm A: GCC, PGO
- Arm B: Clang/LLVM, PGO

The original pinned Stockfish and Reckless submodules in Git remain unchanged. Both binaries are built only for the GitHub runner and are **not released**. The benchmark performs ten interleaved comparisons with `depth=12`, and will fail if the two compilers do not produce exactly the same fixed-depth search-node count.

**Outcome interpretation:**

- If the candidate Clang PGO build has higher median NPS on this runner, it is a speed candidate, not yet an Elo winner.
- If slower, retain GCC PGO; do not tune results retrospectively.
- CPU models and compiler versions must be attached to the report, and any claim must be reproduced on the target CPU.
- A match against GCC PGO using the same engine settings and independent paired openings is required before promoting Clang as a strength improvement.
- Neither optimized host-specific binary is a universal Windows/Linux/Android release.

The dedicated workflow is [`v084-compiler-pgo.yml`](../.github/workflows/v084-compiler-pgo.yml).