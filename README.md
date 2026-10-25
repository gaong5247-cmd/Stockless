# Stockless — Hybrid Chess Engine

<p align="center"><img src="assets/stockless-logo.svg" width="360" alt="Stockless logo"></p>

**English** | [한국어](#한국어)

> Stockless combines Stockfish's established C++ engine infrastructure with a separately developed, threat-aware search policy informed by selected Reckless research. It is **not** a 50/50 source-code merge or a simple average of two NNUE networks.

**Repository:** https://github.com/gaong5247-cmd/Stockless

**Live engine testing / Arena:** [OpenFishtest Arena](https://gaong5247-cmd.github.io/OpenFishtest/#arena) — view match results and standings (maintained as a separate testing project).

**Latest stable release:** [Stockless v0.9.0](https://github.com/gaong5247-cmd/Stockless/releases/tag/Stockless_v0.9.0), published on 2026-10-25 after the final match gate and package checks passed. The release includes the tested Linux AVX2 PGO binary, companion builds and both validation reports. **Previous stable release:** [v0.8.9](https://github.com/gaong5247-cmd/Stockless/releases/tag/Stockless_v0.8.9). **Earlier research archives:** [v0.8–v0.8.7](https://github.com/gaong5247-cmd/Stockless/releases); [v0.8.8-rc1](https://github.com/gaong5247-cmd/Stockless/releases/tag/Stockless_v0.8.8-rc1) remains a separate opt-in research pre-release. Release numbering alone does not establish a verified playing-strength gain.

**v0.9.0 — verified and published:** this release removes the unsuccessful ThreatHistory subsystem, prepares invariant search-policy arithmetic once per node, fixes pin ownership, keeps changing search depth live, and disables desktop Overdrive completely in mobile mode. Engine `1f1a4870fb02cc6cd04d52e2e082ef72aed0ff46` passed its final paired-match gate in [Actions run 40156434508](https://github.com/gaong5247-cmd/Stockless/actions/runs/40156434508). Platform builds, package checks and publication completed; **v0.9.0 is now Latest**. See the [release notes](docs/RELEASE_v0.9.0.md). Its UCI identity is `Stockless v0.9.0`; Overdrive remains OFF by default.

**Measured improvement:** the final 8,192 fresh games at 5+0.05 finished **435W / 7,399D / 358L**, scoring **50.470%**, or **+3.27 Elo with a two-sided pair 99% interval of +0.58 to +5.95**. The original 4,096-game short confirmation at 2+0.02 remains a separate, reused result: 373W / 3,434D / 289L, +7.13 Elo (pair 95% interval +3.20 to +11.06). These are modest gains for the exact Linux AVX2 PGO binary against v0.8.9 rebuilt with ordinary optimization, the same compiler and the same AVX2 target. They do not establish the same gain for companion builds or compare against the old downloadable universal executable. The [final protocol and results](docs/LONG_REPLICATION_20261025.md) and [published JSON evidence](https://github.com/gaong5247-cmd/Stockless/releases/download/Stockless_v0.9.0/validation-report.json) preserve the source and binary identities. The new interval is not a global 99% guarantee; no further attempt follows this protocol.

**Earlier results remain visible:** the ordinary-build screen scored 48.633% and stopped. The PGO screen scored 52.441%; its original 1,024-game longer confirmation was inconclusive at +3.39 Elo (pair 95% interval −2.40 to +9.19), so the original gate remains **not approved**. The later replication is a separate decision and excludes those older longer games from its estimate. [All stages and their original decisions](docs/VALIDATION_20261025.md) are preserved. This validation series played **14,336 actual games** in total; the reused short confirmation is counted once.

**Previous universal release v0.8.9:** [archived installation, UCI defaults and verification results](docs/RELEASE_v0.8.9.md). The older [v0.7.1 release guide](docs/UNIVERSAL_RELEASE.md) remains archived.

**Archived optimization proposal (2026-10-18):** [per-node policy snapshots, CPU-native PGO builds and bench gating](docs/OPTIMIZATION_20261018.md). This predates the completed validation above; no isolated Elo contribution is established for any one source or compiler change.

**Historical research (stable-tag archive):** [v0.7 threat-conditioned history](https://github.com/gaong5247-cmd/Stockless/blob/Stockless_v0.8.9/docs/EXPERIMENT_07.md) is retained as an audit record; the implementation is absent from this lean branch.

**Historical tournament:** [v0.7 history tournament report](https://github.com/gaong5247-cmd/Stockless/blob/Stockless_v0.8.9/docs/HISTORY_TUNING_REPORT.md) documented a failed 800-game independent holdout. The old ON/OFF tuner and promotion workflow have been removed in this lean experiment.

## Architecture

| Layer | Implementation / responsibility |
| --- | --- |
| Board, legal move generation, UCI, threading/NUMA, transposition table, Syzygy | Stockfish |
| Iterative deepening, root search, aspiration windows, primary NNUE evaluation | Stockfish |
| Research references for reductions, correction history, threat features | Reckless 0.10-dev |
| Threat extraction, hybrid depth decisions, selective overdrive, mobile tuning | Stockless |

Stockless pins upstream source revisions as Git submodules rather than merging the C++ and Rust projects line by line. See [upstream revisions](docs/UPSTREAM.md) and [architecture](docs/ARCHITECTURE.md).

### Search pipeline

```text
UCI GUI / command line
        |
Stockfish position, move generation, search and NNUE
        |
Stockless threat signals (selected nodes)
        |-- AttackPressure
        |-- KingDanger
        |-- TacticalVolatility
        |
Stockless hybrid search policy
        |-- LMR adjustment
        |-- Selective pruning-depth boost
        |-- Optional re-search depth bonus
        |
Stockfish search continues and returns bestmove
```

### Threat analysis

`src/stockless/threat_signal.h` uses Stockfish attack maps, king-zone contacts, attacked pieces and pins to compute three bounded signals (0–256):

- **Attack pressure:** contacts near the opposing king, attacks on opposing pieces and pins created.
- **King danger:** threats around our king, attacks on our pieces and pins suffered.
- **Tactical volatility:** mutual piece attacks, pins and king-zone contacts.

These are inexpensive **hand-engineered search signals, not outputs from a second full NNUE**. To limit overhead, ordinary shallow nodes may skip computation: the threshold is depth 5 on desktop and depth 7 in the mobile profile, while important nodes are eligible earlier.

### Hybrid depth policy

`src/stockless/search_policy.h` combines threat signals with search context: checks, captures, PV/TT-PV status, cut nodes, improvement, correction signal and cutoff history. The resulting tactical score influences how much late-move reduction (LMR) is bought back. Strong tactical situations may therefore receive deeper investigation; quiet cut nodes remain more conservative.

**Selective Overdrive** is optional and off by default. It targets forcing checks, severe king danger and high-pressure captures, rather than globally relaxing quiet-move pruning. Mobile mode applies a lower-cost policy. Turning off `StocklessHybrid` disables Stockless policy adjustments for comparison with the underlying Stockfish search.

### NNUE design

Stockfish supplies the **primary evaluation score**. Reckless's threat accumulator and feature design are research references. The current implementation does **not** run two complete NNUE evaluators on every node or claim to have merged their weights. A shared-feature, multi-head Stockless network is a longer-term design goal, not a shipped feature.

## Build

```bash
git clone --recurse-submodules https://github.com/gaong5247-cmd/Stockless.git
cd Stockless
python tools/materialize.py
make -C build/stockless-src/src -j build ARCH=x86-64-avx2
```

On Windows, use `./scripts/build-windows.ps1` in PowerShell. The materialization script checks pinned upstream commits, copies the Stockfish tree, injects Stockless headers and search/UCI changes, and produces buildable sources under `build/stockless-src/`. It fails if expected patch anchors or upstream revisions do not match. Choose an architecture supported by your CPU and toolchain.

The command above makes an ordinary build. For a local GCC PGO build on an AVX2-capable host, run this after materialization:

```bash
bash scripts/build-pgo.sh build/stockless-src/src x86-64-avx2 gcc 4
```

The helper trains a local profile, forces profile-use recompilation and rejects remaining instrumentation. A custom build is not the exact tested artifact and does not inherit its measured Elo result.

## UCI options

| Option | Default | Meaning |
| --- | --- | --- |
| `StocklessHybrid` | true | Enable hybrid search adjustments |
| `StocklessAggression` | 145 | Hybrid aggression, range 0–200 |
| `StocklessThreats` | true | Enable board-derived threat signals |
| `StocklessOverdrive` | false | Opt-in selective tactical extensions |
| `StocklessMobile` | true on Android; false elsewhere | Lower-cost search profile |

Example:

```text
uci
setoption name StocklessAggression value 145
setoption name StocklessOverdrive value false
isready
position startpos
go depth 12
```

## Tests and evidence

The repository includes GitHub Actions build and arena workflows, Cute Chess scripts and [tuning notes](docs/TUNING_RESULTS.md). Reported Elo values are **relative to each specific opponent, time control and test configuration**, not universal ratings.

Examples documented in the repository:
- v0.3 vs Stockfish: 1,200 games, 48.25% score, approximately −12.2 relative Elo (95% CI −27.8 to +3.4).
- v0.3 vs Reckless 0.10-dev: 1,000 games at 1+0.01, 54.40% score, approximately +30.65 relative Elo.
- v0.4 aggression 144 confirmation: 4,000 games, 50.262% score, approximately +1.82 relative Elo (95% CI −7.22 to +10.87).
- v0.5 selective-overdrive aggression 145 fine sweep: 600 games, 52.17% score, approximately +15.1 relative Elo; a larger confirmation was described as pending.

**These results do not establish a statistically confirmed advantage over Stockfish.** Review the exact settings and confidence intervals before interpreting them. A release announcement or external blog listing is not independent strength validation.

## Project layout

```text
src/stockless/config.h          UCI-linked runtime settings
src/stockless/threat_signal.h   Board-based threat features
src/stockless/search_policy.h  Hybrid search decisions
tools/materialize.py            Reproducible source overlay
upstream/stockfish/             Pinned Stockfish submodule
upstream/reckless/              Pinned Reckless research submodule
scripts/                       Build and match helpers
.github/workflows/              CI, builds, tuning and arenas
docs/                           Architecture, upstream, tuning, Android
assets/stockless-logo.svg       Project branding
```

## Contributors

- Project maintainer: [@gaong5247-cmd](https://github.com/gaong5247-cmd)
- Contributor: [@eueong04-create](https://github.com/eueong04-create)

See the maintained [CONTRIBUTORS.md](CONTRIBUTORS.md) for project acknowledgements.

## Licensing and attribution

See [LICENSE](LICENSE), [NOTICE.md](NOTICE.md) and [UPSTREAM.md](docs/UPSTREAM.md). Stockfish is GPL-3.0-or-later; Reckless is AGPL-3.0; Stockless integration is distributed under AGPL-3.0. Preserve upstream notices and comply with applicable source-distribution obligations.

---

# 한국어

> Stockless는 Stockfish의 안정적인 C++ 엔진 기반 위에 Reckless의 연구 아이디어를 참고한 **독립적인 전술 인식형 탐색 정책**을 추가한 하이브리드 체스 엔진입니다. 두 엔진의 코드를 단순히 반반 합치거나 NNUE 가중치를 평균 낸 구조가 아닙니다.

**실시간 엔진 대국 / 아레나:** [OpenFishtest Arena 바로가기](https://gaong5247-cmd.github.io/OpenFishtest/#arena) — 엔진 대국 결과와 순위를 확인할 수 있는 별도 테스트 프로젝트입니다.

**최신 정식 릴리스: [Stockless v0.9.0](https://github.com/gaong5247-cmd/Stockless/releases/tag/Stockless_v0.9.0).** 최종 대국과 패키지 검증을 통과해 2026-10-25에 Latest로 공개했습니다. 실제 시험한 Linux AVX2 PGO 파일, 다른 플랫폼용 빌드, 최초·최종 검증 보고서를 함께 제공합니다. [v0.8.9](https://github.com/gaong5247-cmd/Stockless/releases/tag/Stockless_v0.8.9)는 이전 안정판으로 보존합니다. v0.8~v0.8.7은 연구 기록용이며, [v0.8.8-rc1](https://github.com/gaong5247-cmd/Stockless/releases/tag/Stockless_v0.8.8-rc1)은 별도 프리릴리스입니다. 공개된 v0.9.0의 UCI 이름은 `Stockless v0.9.0`입니다. 버전 번호 자체가 기력 향상을 뜻하지 않으며, 정식 Stockfish 19를 능가한다는 통계적 증거는 아직 없습니다.

**v0.9.0 — 대국 검증과 공개 완료:** 이번 릴리스는 성능이 입증되지 않은 ThreatHistory 구현을 제거하고, 탐색 정책의 공통 계산을 노드 단위로 정리하며, 핀 방향과 모바일 Overdrive 제한을 바로잡습니다. 도입한 기존 실험 코드의 깊이 캐시 오류도 수정했으며, 이 캐시 오류는 공개된 v0.8.9에는 없었습니다. 엔진 `1f1a4870fb02cc6cd04d52e2e082ef72aed0ff46`는 [최종 Actions 대국](https://github.com/gaong5247-cmd/Stockless/actions/runs/40156434508)의 사전 기준을 통과했습니다. 다중 플랫폼 빌드·패키지 검증·게시까지 완료해 **v0.9.0이 Latest가 됐습니다.** [릴리스 안내](docs/RELEASE_v0.9.0.md)에 상세 변경 사항을 정리했습니다. Overdrive 기본값은 OFF입니다.

**실제로 측정한 개선:** 새로운 포지션에서 진행한 5+0.05 대국 **8,192판은 435승 / 7,399무 / 358패**, 승점 **50.470%**, **+3.27 Elo(양측 99% 쌍 단위 구간 +0.58~+5.95)**였습니다. 기존 2+0.02의 단기 확인 4,096판은 373승 / 3,434무 / 289패, +7.13 Elo(95% 구간 +3.20~+11.06)로, 결과를 그대로 재사용하며 장기 통계와 합치지 않습니다. 실제 시험한 Linux AVX2 PGO 파일과 같은 컴파일러·AVX2 대상으로 일반 최적화하여 다시 빌드한 v0.8.9 사이에서 확인한 소폭 개선입니다. 기존 다운로드용 Universal 파일과 비교한 수치가 아니며 다른 플랫폼에 같은 상승폭을 적용하지 않습니다. [최종 계획·결과](docs/LONG_REPLICATION_20261025.md)와 [공개된 JSON 증거](https://github.com/gaong5247-cmd/Stockless/releases/download/Stockless_v0.9.0/validation-report.json)에 소스와 파일의 동일성을 기록했습니다. 전체 절차의 99% 확실성을 뜻하지 않으며 이 검증 뒤 추가 시도는 없습니다.

**앞선 결과도 보존합니다:** 일반 빌드의 예비전은 승점 48.633%로 중단했습니다. PGO 예비전은 52.441%였지만 최초 장기 1,024판은 +3.39 Elo(95% 구간 −2.40~+9.19)로 불확실해, 최초 게이트는 계속 **미승인**입니다. 최종 재검증은 별도 판정이며 이전 장기 표본을 새 통계에 합치지 않습니다. [모든 대국과 최초 판정](docs/VALIDATION_20261025.md)을 남겼습니다. 이번 검증에서 실제 진행한 대국은 총 **14,336판**이며, 재사용한 단기 4,096판은 한 번만 셌습니다.

**이전 최적화 제안(2026-10-18):** [탐색 노드당 설정 스냅샷, CPU별 PGO 빌드, 벤치마크 기준](docs/OPTIMIZATION_20261018.md). 위 최종 검증보다 앞선 기록이며, 개별 소스 변경이나 컴파일 방식 하나의 Elo 기여도를 분리해 입증한 것은 아닙니다.

**이전 Universal 배포 v0.8.9:** [당시 Windows·Linux·Android 설치, UCI 설정 및 대국 결과](docs/RELEASE_v0.8.9.md)를 보존합니다. v0.8.9는 History OFF였으며, v0.9.0에서는 History 구현 자체를 제거했습니다. 이전 [v0.7.1 안내](docs/UNIVERSAL_RELEASE.md)도 보존합니다.

**이전 연구 기록(안정판 태그 보관):** [v0.7 위협별 Quiet History 설계·옵션·A/B 대국 가이드](https://github.com/gaong5247-cmd/Stockless/blob/Stockless_v0.8.9/docs/EXPERIMENT_07.md). 과거 실험의 기록이며, 현재 브랜치에서는 구현과 `StocklessThreatHistory`·`StocklessHistoryWeight` UCI 옵션을 제거했습니다. 기존 GUI 설정에서도 이 두 옵션을 제거하세요.

**이전 튜닝·대국 기록:** [당시 ON/OFF·가중치 튜닝 절차](https://github.com/gaong5247-cmd/Stockless/blob/Stockless_v0.8.9/docs/TUNING_PIPELINE_07.md)와 [v0.7 실제 대국 보고서](https://github.com/gaong5247-cmd/Stockless/blob/Stockless_v0.8.9/docs/HISTORY_TUNING_REPORT.md)를 보존합니다. 800판 독립 확인 대국에서 개선을 입증하지 못했으며, 해당 튜너와 기본값 자동 변경 워크플로는 현재 브랜치에서 제거했습니다.

## 구성 요소

| 계층 | 담당 |
| --- | --- |
| 체스판 표현, 합법 수 생성, UCI, 스레드/NUMA, TT, Syzygy | Stockfish |
| 반복 심화, 루트 탐색, aspiration window, 기본 NNUE 평가 | Stockfish |
| LMR, correction history, 위협 특성 연구 참고 | Reckless 0.10-dev |
| 위협 신호, 하이브리드 깊이 조절, 선택적 Overdrive, 모바일 프로필 | Stockless |

Stockless는 Stockfish와 Reckless를 Git 서브모듈의 고정 커밋으로 관리합니다. Reckless의 Rust 소스를 C++ 소스와 무작정 섞는 방식이 아니라, 필요한 개념을 선별적으로 적용하는 구조입니다.

## 핵심 동작

**1. 위협 신호 계산:** `threat_signal.h`는 Stockfish의 공격 비트보드와 킹 주변 공격, 공격받는 기물, 핀 정보를 사용하여 세 가지 신호를 계산합니다.

- **AttackPressure(공격 압박):** 상대 킹 주변 공격, 상대 기물 공격, 우리가 만든 핀
- **KingDanger(킹 위험도):** 우리 킹 주변 위협, 우리 기물에 대한 공격, 당한 핀
- **TacticalVolatility(전술적 변동성):** 상호 공격과 핀, 양측 킹 주변 접촉

각 값은 0~256 범위로 제한됩니다. 이 신호는 **두 번째 NNUE 추론 결과가 아니라 체스판 정보에서 계산한 경량 지표**입니다. 연산 비용을 줄이기 위해 일반 노드는 데스크톱에서 깊이 5, 모바일에서 깊이 7 미만일 경우 계산을 건너뛸 수 있습니다. 중요한 노드는 예외입니다.

**2. 하이브리드 탐색 정책:** `search_policy.h`는 위협 신호에 체크, 캡처, PV 노드, cut node, correction signal 등 탐색 정보를 결합합니다. 전술적으로 중요한 수에서는 LMR에 의한 탐색 깊이 감소를 완화하고, 일반적인 조용한 수에서는 비용을 보수적으로 관리합니다.

**3. Selective Overdrive:** 기본값은 **OFF**입니다. 활성화하면 강제적인 체크, 심각한 킹 위험, 압박이 높은 캡처 등 일부 상황에서만 추가 탐색을 허용합니다. 모든 수를 무조건 깊게 탐색하는 방식이 아닙니다.

**4. NNUE 평가:** 현재 평가 점수는 Stockfish의 기본 NNUE 경로가 담당합니다. Reckless의 threat accumulator는 연구 참고 대상이며, **두 NNUE를 매 노드마다 동시에 실행하거나 가중치를 병합한 구현은 아닙니다.** 공통 특성을 사용하는 다중 출력 NNUE는 향후 연구 목표입니다.

## 빌드 방법

```bash
git clone --recurse-submodules https://github.com/gaong5247-cmd/Stockless.git
cd Stockless
python tools/materialize.py
make -C build/stockless-src/src -j build ARCH=x86-64-avx2
```

Windows에서는 PowerShell에서 `./scripts/build-windows.ps1`을 사용할 수 있습니다. `materialize.py`는 상위 프로젝트 커밋을 검증하고 Stockfish 소스에 Stockless의 탐색 코드 및 UCI 옵션을 적용합니다. CPU와 빌드 환경에 맞는 아키텍처를 선택하세요.

위 명령은 일반 빌드를 만듭니다. AVX2를 지원하는 컴퓨터에서 GCC로 로컬 PGO 빌드를 만들려면 소스 생성 후 다음을 실행하세요.

```bash
bash scripts/build-pgo.sh build/stockless-src/src x86-64-avx2 gcc 4
```

이 도구는 로컬 프로파일을 학습하고, 프로파일 사용 단계의 전체 재컴파일 및 계측 코드 제거를 확인합니다. 직접 빌드한 파일은 실제 대국에 사용한 파일과 같다고 보장되지 않으므로 위 Elo 수치를 그대로 적용하지 않습니다.

## UCI 설정

| 옵션 | 기본값 | 기능 |
| --- | --- | --- |
| `StocklessHybrid` | true | 하이브리드 탐색 활성화 |
| `StocklessAggression` | 145 | 공격성 설정(0~200) |
| `StocklessThreats` | true | 위협 신호 사용 |
| `StocklessOverdrive` | false | 선택적 전술 탐색 강화 |
| `StocklessMobile` | Android에서 true | 저비용 모바일 탐색 |

`StocklessHybrid=false`를 설정하면 Stockless 탐색 조정을 비활성화해 Stockfish 기반 탐색과 비교할 수 있습니다.

## 테스트 결과를 읽는 방법

저장소에는 Cute Chess 경기 스크립트, GitHub Actions 자동 빌드 및 튜닝 워크플로가 있습니다. 자세한 수치는 [TUNING_RESULTS.md](docs/TUNING_RESULTS.md)를 참고하세요.

- v0.3 vs Stockfish: 1,200판, 승점 48.25%, 상대 Elo 약 −12.2
- v0.3 vs Reckless 0.10-dev: 1,000판, 승점 54.40%, 상대 Elo 약 +30.65
- v0.4 공격성 144 확인: 4,000판, 승점 50.262%, 상대 Elo 약 +1.82
- v0.5 Selective Overdrive 공격성 145 탐색: 600판, 승점 52.17%, 상대 Elo 약 +15.1

**이 수치는 특정 대국 조건에서의 상대 성능이며 공식 절대 레이팅이 아닙니다.** 특히 Stockfish보다 강하다는 통계적으로 확정된 결론은 아직 제시되지 않았습니다. 600판 튜닝 결과는 더 큰 표본으로 재검증해야 합니다.

## 소스 구조

```text
src/stockless/config.h          런타임 설정
src/stockless/threat_signal.h   위협 신호 계산
src/stockless/search_policy.h  하이브리드 탐색 정책
tools/materialize.py            소스 통합 및 패치
upstream/stockfish/             Stockfish 서브모듈
upstream/reckless/              Reckless 연구용 서브모듈
scripts/                       빌드 및 대국 스크립트
.github/workflows/              CI / 자동 빌드 / 테스트
docs/                           설계, 테스트, Android 문서
assets/stockless-logo.svg       로고
```

## 기여자

- 프로젝트 관리자: [@gaong5247-cmd](https://github.com/gaong5247-cmd)
- 기여자: [@eueong04-create](https://github.com/eueong04-create)

전체 명단은 [CONTRIBUTORS.md](CONTRIBUTORS.md)를 참고하세요.

## 라이선스

[LICENSE](LICENSE), [NOTICE.md](NOTICE.md), [UPSTREAM.md](docs/UPSTREAM.md)를 참고하세요. Stockfish는 GPL-3.0-or-later, Reckless는 AGPL-3.0이며 Stockless 통합 코드는 AGPL-3.0으로 배포됩니다. 원본 저작권 표시와 소스 공개 의무를 준수해야 합니다.
