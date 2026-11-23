# Stockless v0.8.9 — Lower-aggression strength screen

**Experimental only. No changes to engine C++, NNUE, build flags or stable UCI defaults.**

## Motivation

The same-binary hybrid ablation in PR #25 found that full hybrid with Aggression 145 searched roughly twice as many depth-12 nodes as hybrid OFF. Its short paired matches did not show a statistically confirmed advantage. This does **not** prove that high aggression weakens Stockless; however, it motivates testing whether less LMR buyback could improve *fixed-time* strength by permitting deeper/more targeted exploration.

## Controlled configurations

The workflow builds a **single** pinned Stockless v0.8.9 binary with `ARCH=x86-64-avx2`, then compares Aggression **64**, **96**, and **112** against the frozen default **145**.

Every engine uses Hybrid ON, Threats ON, Overdrive OFF, ThreatHistory OFF, Mobile OFF, Threads 1, Hash 32MiB and MoveOverhead 1ms. Settings are otherwise identical. Each candidate gets **256 color-swapped games**, TC **0.5+0.005**, from the pinned official Stockfish `8moves_v3` CC0 PGN at book SHA `a804a97e709f40aa75a00f9d19e84915b7a3a45c`.

Match PGNs, logs and win/draw/loss summaries are archived in Actions. Short samples are for candidate elimination/screening only, not proof of Elo gain. The experiment **does not** automatically select or promote a UCI default.

## Promotion process

1. Confirm all 768 games complete and review each 256-game paired result and any forfeit/timeout issues.
2. Screen out profiles with clear deteriorations. A leading profile is only a hypothesis; multiple-comparison and runner biases exist.
3. Test any promising profile against 145 with fresh, disjoint openings and longer time control, thousands of color-swapped games or sequential SPRT/pentanomial analysis.
4. Independently check against official SF19 and verify that improvements hold on Windows/Android CPUs before changing any defaults.
5. Do not delete threat scans, alter NNUE, or change the stable engine based on a single small screen.

Workflow: [v089-aggression-budget-screen.yml](../.github/workflows/v089-aggression-budget-screen.yml).
