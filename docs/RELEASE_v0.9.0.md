# Stockless v0.9.0 — lean search and corrected threat ownership

This release is eligible for publication only after its exact source passes the
independent paired-match gate against Stockless v0.8.9. The completed results
are appended automatically below, with a downloadable JSON audit report.

## Changes

- Remove the unsuccessful, default-disabled ThreatHistory experiment, including
  its per-worker storage, hot-path option checks, two UCI options, and obsolete
  tuning/promotion scripts. Earlier released versions and research records remain
  available. Existing GUI configurations should remove `StocklessThreatHistory`
  and `StocklessHistoryWeight`; they are no longer supported options.
- Prepare invariant policy arithmetic once per search node. Keep depth, TT-PV
  state, window and child-cutoff counts live because they can change between moves.
- Correct pin ownership: `Position::pinners(c)` contains sliders belonging to
  color c. Previously pins created and suffered were reversed in the attack and
  king-danger signals. Four asymmetric real-position regressions cover both colors.
- Make mobile Overdrive consistently inactive, including its reduction cap.
- Replace automatic version-based publication with complete-game, fault-free,
  paired-color statistical evidence and verified multi-platform packages.

## Packages and defaults

Windows x86-64, Linux x86-64, Linux ARM64, Android ARM64 and Android ARMv7 each
have their own ZIP. x86-64 and ARM64 universal binaries select supported CPU
instructions at runtime. These are native UCI executables, not Android APKs.
The NNUE is embedded; source identity, manifests, licenses and checksums accompany
every package. Use a chess GUI that imports native UCI engines.

Defaults: Hybrid ON; Aggression 145; Threats ON; Overdrive OFF. Mobile defaults ON
on Android and OFF on desktop. The upstream Stockfish and NNUE pins are unchanged.

The released universal binaries use ordinary optimized builds. Separate local PGO
benchmarks are research evidence only; their speedup is not attributed to these
packages. Match evidence below applies to Linux AVX2, one search thread, Hash
32 MiB and the specified short Fischer controls. It does not establish a universal
Elo rating, mobile performance gain, or superiority over official Stockfish 19.

## 한국어

위협 분석의 핀 방향 오류와 탐색 깊이 캐시 오류를 수정하고, 성능이 입증되지 않았던
ThreatHistory 실험 코드를 제거했습니다. 공개 여부는 v0.8.9 상대 독립 대국 5,120판의
완주·오류 여부와 두 시간제한별 쌍 단위 95% 신뢰구간으로 결정합니다. 예비 512판은
최종 확인 통계에 합치지 않습니다. 실제 결과는 아래 표와 첨부 보고서에서 확인하세요.
