# Stockless v0.9.0 — AVX2 PGO and lean search

**Original experiment: not approved. Final publication is conditional on the
separately predeclared longer-time-control replication.**

The original validation left Latest at Stockless v0.8.9. The
[final replication protocol](LONG_REPLICATION_20261025.md),
`20261025-long-replication-99`, defines one further fixed sample using the same
engine binaries. The original failed decision remains part of the record.
Any final approval must identify this separate protocol, preserve both reports,
and append its actual results below; predeclaring it does not establish success.

## Changes

- Remove the unsuccessful, default-disabled ThreatHistory experiment, including
  its per-worker storage, hot-path option checks, two UCI options, and obsolete
  tuning/promotion scripts. Earlier released versions and research records remain
  available. Existing GUI configurations should remove `StocklessThreatHistory`
  and `StocklessHistoryWeight`; they are no longer supported options.
- Prepare invariant policy arithmetic once per search node. Keep depth, TT-PV
  state, window and child-cutoff counts live because they can change between moves.
  The stale-depth cache was found in the inherited experimental prepared-policy
  candidate; it was not present in the published v0.8.9 source.
- Correct pin ownership: `Position::pinners(c)` contains sliders belonging to
  color c. Previously pins created and suffered were reversed in the attack and
  king-danger signals. Four asymmetric real-position regressions cover both colors.
- Make mobile Overdrive consistently inactive, including its reduction cap.
- Replace automatic version-based publication with complete-game, fault-free,
  paired-color statistical evidence and verified multi-platform packages.

## Packages and defaults

| Package | Intended use | Strength-evidence scope |
|---|---|---|
| `linux-x86_64-avx2-pgo` | Linux x86-64 with AVX2 | The exact tested binary; publication preserves its bytes and requires final protocol approval |
| `windows-x86_64-avx2-pgo` | Windows 64-bit with AVX2 | Separately compiled PGO companion; UCI, nodes and bestmoves checked |
| Windows/Linux x86-64 universal | CPU instruction-set dispatch and compatibility | Ordinary, non-PGO builds; no independent Elo gain established |
| Linux ARM64 / Android ARM64 / Android ARMv7 | ARM compatibility | Ordinary, non-PGO builds; no independent Elo gain established |

AVX2 PGO binaries require AVX2 support. All seven ZIPs have source identities,
licenses, manifests and checksums. The NNUE is embedded. Android packages contain
native UCI executables for a compatible chess GUI, not APKs.

Defaults: Hybrid ON; Aggression 145; Threats ON; Overdrive OFF. Mobile defaults ON
on Android and OFF on desktop. The upstream Stockfish and NNUE pins are unchanged.

### Scope of the match evidence

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

The original PGO [Actions run 40153018357](https://github.com/gaong5247-cmd/Stockless/actions/runs/40153018357)
passed its 4096-game short confirmation at +7.13 Elo (pair 95% interval
[+3.20, +11.06]), but its 1024-game longer confirmation was inconclusive at
+3.39 Elo ([−2.40, +9.19]). Its release gate therefore remains **not approved**.

The final protocol predeclares **8192 new games at 5+0.05**, using the exact
candidate and baseline artifacts from that run. It requires the new sample's
**two-sided 99% paired lower Elo bound >0** plus the unchanged original short
confirmation's **95% lower bound >0 and point Elo >=+5**. The original longer
sample is not pooled with the new sample. There is no further attempt after this
protocol. The new 99% interval is not a global 99% guarantee: the two longer-time
testing opportunities have an approximate nominal one-sided union bound of 3%,
subject to the stated normal-approximation assumptions.

If approved, the release tag targets engine source
`1f1a4870fb02cc6cd04d52e2e082ef72aed0ff46`; the newer validation workflow/protocol
revision is recorded separately. The exact binary identities and publication
conditions are fixed in the linked protocol.

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

v0.8.9의 핀 방향 오류와 모바일 Overdrive 제한 오류를 수정하고, 성능이 입증되지 않았던
ThreatHistory 실험 코드를 제거했습니다. 탐색 정책 계산을 노드 단위로 정리하면서 도입한
기존 실험 코드의 깊이 캐시 오류도 바로잡았습니다. 이 캐시 오류는 공개된 v0.8.9에는 없었습니다.

최초 검증은 단기 4096판을 통과했지만 장기 1024판의 구간이 0을 포함해 공개 승인에
실패했고, 그 결정은 Latest를 v0.8.9로 유지했습니다. 최초 결과와 실패 판정은 그대로
보존하며, 별도 최종 계획의 성공 여부와 구분합니다.

최종 공개 조건은 같은 두 실행 파일로 새로운 포지션에서 진행하는 5+0.05 대국
8192판의 **양측 99% 쌍 단위 구간 Elo 하한 >0**, 그리고 기존 단기 4096판의
**95% 하한 >0 및 점추정 Elo >=+5**입니다. 이전 장기 1024판과 예비전은 새 통계에
합치지 않습니다. 이는 별도로 사전 선언한 마지막 계획이며, 실행이나 성공을 미리
주장하지 않습니다. 결과와 무관하게 그 뒤 추가 시도는 하지 않습니다. 새로운 99%
구간이 전체 절차의 99% 확실성을 뜻하는 것도 아닙니다. 실제 최종 판정이 있으면
최초 보고서와 함께 아래 결과 및 첨부 보고서에 명시합니다.

측정된 기력 결과는 실제 대국에 사용된 Linux AVX2 PGO 파일에 한정합니다. Windows PGO는 별도 빌드이며, Universal·Android 파일은 호환용 일반 빌드입니다. 이 파일들에 같은 Elo 상승을 적용하지 않습니다.
