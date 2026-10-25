# Final independent longer-time-control replication

**Protocol ID: `20261025-long-replication-99`**

**Status: predeclared plan, with no replication result claimed.** The original
experiment remains not approved and Latest remains Stockless v0.8.9. This protocol
defines one final, fixed-size replication; it does not retrospectively change the
original gate or describe a run as started before it is launched.

## Reason and preserved original decision

The original [Actions run 40153018357](https://github.com/gaong5247-cmd/Stockless/actions/runs/40153018357)
completed all its planned games with valid evidence:

| Original stage | Games | W / D / L | Relative Elo | Pair 95% Elo interval | Original decision |
|---|---:|---|---:|---|---|
| Short confirmation, 2+0.02 | 4096 | 373 / 3434 / 289 | +7.13 | [+3.20, +11.06] | Passed |
| Longer confirmation, 5+0.05 | 1024 | 51 / 932 / 41 | +3.39 | [−2.40, +9.19] | Inconclusive; did not pass |

Both stages were required, so the original release gate returned **not approved**.
Its report and all games remain unchanged. The positive but imprecise longer-time
estimate motivates this separately declared replication after reviewing the
original result. That timing is disclosed: this was not part of the original
predeclared experiment.

The full original results, including both the PGO and earlier ordinary-build
screens, remain in [VALIDATION_20261025.md](VALIDATION_20261025.md). No result is
removed, relabeled as a pass, or pooled into the new longer-time-control estimate.

## Freeze the exact executables

Reuse the original `validation-build` artifact from run **40153018357**. Do not
rebuild, retrain the PGO profile, tune an option, or select a different executable.

| Identity | Candidate | Baseline |
|---|---|---|
| Engine source commit | `1f1a4870fb02cc6cd04d52e2e082ef72aed0ff46` | `d2e165a6ab70a9a00e1d52ba2a0f4f678ffef22f` |
| Build | Linux x86-64 AVX2, verified PGO | Linux x86-64 AVX2, ordinary optimization |
| Binary SHA-256 | `8ad4d99da4c9976f4cfc77d59f948541be04bca3c756b2d12dca6505d6e906fc` | `20b9637fa30b90a63b76ebc0bd9ffec601d32b26161a6b86e032e4bf01aa7ba8` |

The workflow/protocol revision is separate from the engine revision. Record both
in the final audit report. Every shard must verify both binary hashes before
playing; packaging the approved Linux candidate must preserve the same bytes.

## Fixed workload and settings

| Item | Predeclared value |
|---|---|
| Games | **8192**, comprising **4096 color-swapped opening pairs** |
| Time control | **5+0.05** for both engines |
| Shards | **16**, each **512 games / 256 pairs** |
| Parallel games | **2 per runner** |
| Search threads | **1 per engine** |
| Hash | **32 MiB per engine** |
| Retained UCI settings | Hybrid ON, Aggression 145, Threats ON, Overdrive OFF, Mobile OFF |
| Baseline-only retired option | ThreatHistory OFF |
| Other arena settings | Same as the original longer confirmation: CuteChess 1.5.1, Move Overhead 10 ms, wait 10 ms |
| Draw adjudication | Move 40, count 8, score 8 cp |
| Resignation | Count 3, score 650 cp |
| Recovery | Disabled |
| Screening or tuning | **None** |

Complete the fixed sample before evaluating success. Do not stop early for a
favorable partial estimate, inspect alternative parameter settings, or replace a
losing shard. Technical failures or incomplete evidence do not count as games
and cannot produce approval.

## Fresh opening allocation

Use the same frozen, deduplicated legal-position list from official Stockfish
`8moves_v3`, books revision `a804a97e709f40aa75a00f9d19e84915b7a3a45c`, sorted and
shuffled once with seed **20261025**. Offsets are zero-based and the ranges below
are inclusive.

| Allocation | Opening offsets | Distinct positions |
|---|---|---:|
| Original PGO screen | 2816–3071 | 256 |
| Original short confirmation | 3072–5119 | 2048 |
| Original longer confirmation | 5120–5631 | 512 |
| **Final longer replication** | **5632–9727** | **4096** |

For shard `s` in 0–15, use offsets `5632 + 256*s` through
`5632 + 256*(s+1) - 1`. Play each position twice with colors swapped. Do not
reshuffle, draw a different range, or reuse earlier positions after seeing results.
Verify uniqueness and non-overlap against every earlier allocation in this
validation series, including the earlier ordinary-build screen. Record the source
book hash, generated list hash, shard ranges and starting FENs.

## Analysis and final publication rule

Analyze the **new 8192 games alone** as 4096 paired observations. A pair's
observation is the candidate's mean score across its two colors, taking values
0, 0.25, 0.5, 0.75 or 1. Report W/D/L, pair counts, pentanomial outcomes, mean
score, relative Elo and a **two-sided 99% approximate normal interval based on
pair-level variance**. Use the 99% normal critical value, approximately 2.575829,
and transform score endpoints to Elo. These are fixed-sample intervals, not SPRT.

Approval requires all of the following:

1. All 8192 planned games pass legality, completeness, pairing, unique-opening,
   source/binary identity and engine/connection/time-fault checks.
2. The new longer-replication **99% lower Elo bound is strictly above zero**
   (equivalently, its lower score bound exceeds 50%).
3. The unchanged original **4096-game short confirmation** remains valid and
   passes its original **95% lower Elo bound >0 and point Elo >=+5** requirements.
4. All release package, manifest, identity and checksum checks pass.

The old 1024-game longer confirmation and both screens are excluded from the new
estimate and its confidence interval. The original gate remains false; any final
approval is a **new decision under this separately identified protocol**, with the
original failed decision included alongside it. Do not combine different time
controls into one claimed improvement.

**This is the final attempt.** After this protocol, do not add games, change a
confidence level, rerun until favorable, introduce another candidate, or make
another release attempt in this validation series, regardless of the outcome.
If any required condition is not met, Latest stays v0.8.9.

## Multiple testing and uncertainty

The original longer test used a two-sided 95% interval with a positive-lower-bound
criterion, corresponding to a nominal one-sided 2.5% false-positive level.
This final test uses the analogous two-sided 99% criterion, nominally 0.5% on
one side. A union bound across these **two longer-time-control opportunities** is
therefore approximately **2.5% + 0.5% = 3%**, subject to the normal approximation
and validity assumptions. This is not a global 99% guarantee, nor a correction
covering every historical Stockless experiment or selection decision. Reusing the
already completed short test does not make it a fresh independent replication.

Using the old longer test's observed pair variance only as a planning estimate,
8192 games would give an approximate **99% margin of ±2.69 Elo** near a small
effect. If the true gain were +3.39 Elo and that variance persisted, power would
be about **75%**. The true effect and variance are uncertain; these are workload
estimates, not a prediction of success or promised precision.

## Publication provenance and claim scope

Before final approval, Latest remains v0.8.9. If every condition passes, target
the v0.9.0 release tag at **engine commit `1f1a4870fb02cc6cd04d52e2e082ef72aed0ff46`**,
not the newer workflow/protocol commit. Publish the exact candidate Linux binary
above, and include both the original and final reports, run URLs, source commits,
binary hashes and the protocol ID. Never overwrite an existing tag or release.

Any measured gain describes this exact Linux AVX2 PGO binary against the ordinary
AVX2 v0.8.9 rebuild under the stated settings. It does not isolate a pin-fix,
cleanup or PGO contribution, prove a gain for Windows or ARM/Android companion
builds, establish a platform-independent Elo rating, or demonstrate a Stockfish 19
win.

## 한국어 요약

최초 검증은 짧은 시간제한에서 통과했지만, 긴 시간제한 1024판의 신뢰구간이 0을
포함해 공개 승인에 실패했습니다. 그 결과와 판정은 그대로 보존합니다. 이번 문서는
그 결과를 본 뒤 별도로 정한 **마지막 독립 재검증 계획**이며, 아직 새 결과를 주장하지 않습니다.

같은 두 실행 파일을 그대로 사용해 겹치지 않는 시작 포지션 4096개에서 색을 바꿔
총 8192판을 5+0.05로 진행합니다. 새 예비전·설정 변경·중간 성공 판정은 없습니다.
새 대국만 계산한 **양측 99% 쌍 단위 구간의 Elo 하한이 0보다 높고**, 기존 단기
4096판의 통과 조건도 유지돼야 별도 최종 승인을 할 수 있습니다. 이전 장기 1024판은
새 통계에 합치지 않습니다. 결과와 무관하게 이 검증 뒤 추가 시도는 하지 않습니다.

99%는 새 장기 표본의 구간 수준이며, 전체 절차가 99% 확실하다는 뜻은 아닙니다.
두 장기 검증의 명목 단측 오류 수준 합계는 정규근사의 전제 아래 약 3%입니다.
공개 조건을 충족하기 전까지 Latest는 v0.8.9입니다.
