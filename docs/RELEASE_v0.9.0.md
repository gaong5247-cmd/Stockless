# Stockless v0.9.0 — AVX2 PGO and lean search

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

| Package | Intended use | Strength-evidence scope |
|---|---|---|
| `linux-x86_64-avx2-pgo` | Linux x86-64 with AVX2 | The exact binary used in the successful confirmation; published byte-for-byte |
| `windows-x86_64-avx2-pgo` | Windows 64-bit with AVX2 | Separately compiled PGO companion; UCI, nodes and bestmoves checked |
| Windows/Linux x86-64 universal | CPU instruction-set dispatch and compatibility | Ordinary, non-PGO builds; no independent Elo gain established |
| Linux ARM64 / Android ARM64 / Android ARMv7 | ARM compatibility | Ordinary, non-PGO builds; no independent Elo gain established |

AVX2 PGO binaries require AVX2 support. All seven ZIPs have source identities,
licenses, manifests and checksums. The NNUE is embedded. Android packages contain
native UCI executables for a compatible chess GUI, not APKs.

Defaults: Hybrid ON; Aggression 145; Threats ON; Overdrive OFF. Mobile defaults ON
on Android and OFF on desktop. The upstream Stockfish and NNUE pins are unchanged.

### Scope of the measured improvement

The appended match evidence compares **the exact Linux AVX2 PGO candidate** with
**v0.8.9 rebuilt using ordinary optimization, the same compiler and AVX2 ISA**.
It does not compare against the old downloadable universal executable. It measures
the complete source-plus-build combination and cannot isolate source cleanup's
Elo contribution. The Windows PGO companion and five normal compatibility builds
have no independent match-proven Elo increase. No superiority over official
Stockfish 19 or platform-independent rating is claimed.

A preceding ordinary-build screen completed 72W/354D/86L in 512 games (48.633%;
pair-level 95% Elo interval −24.92 to +5.88) and was **not promoted**. Its holdouts were
skipped. This PGO candidate uses disjoint, previously unused openings. The earlier
result is preserved in [Actions 40151375797](https://github.com/gaong5247-cmd/Stockless/actions/runs/40151375797).

### PGO build integrity

The build explicitly separates profile generation, training, cleanup and forced
profile-use recompilation. It rejects an executable containing profiling
instrumentation. A local mixed-object build was detected during preparation and
excluded from performance claims; the exact cause of its incomplete cleanup was
not established. The verified clean build measured a modest +1.77% median NPS
against the same corrected ordinary source in three local repetitions, with
identical nodes/bestmoves. These timing measurements are not the strength evidence;
the independent Actions matches below are the publication gate.

## 한국어

위협 분석의 핀 방향 오류와 탐색 깊이 캐시 오류를 수정하고, 성능이 입증되지 않았던
ThreatHistory 실험 코드를 제거했습니다. Linux AVX2 PGO 강화판의 공개 여부는 v0.8.9 일반 빌드 상대 독립 대국 5,120판의
완주·오류 여부와 두 시간제한별 쌍 단위 95% 신뢰구간으로 결정합니다. 예비 512판은
최종 확인 통계에 합치지 않습니다. 실제 결과는 아래 표와 첨부 보고서에서 확인하세요.

측정된 기력 결과는 실제 대국에 사용된 Linux AVX2 PGO 파일에 한정합니다. Windows PGO는 별도 빌드이며, Universal·Android 파일은 호환용 일반 빌드입니다. 이 파일들에 같은 Elo 상승을 적용하지 않습니다.
