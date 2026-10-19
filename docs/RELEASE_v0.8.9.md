# Stockless v0.8.9 — Universal UCI release

**October 20, 2026 | UCI name: `Stockless v0.8.9` | Latest stable release**

Stockless combines the pinned Stockfish search and NNUE framework with Stockless's threat-aware hybrid search policy. This release integrates the conservative, node-equivalent search-policy refactor and corrects the test arena's accidental default-option overrides. It is **not** a new Stockfish 19 binary or a claim of proven superiority over Stockfish 19.

## Download the correct engine

| Release file | Operating system | CPU support |
| --- | --- | --- |
| `Stockless-v0.8.9-windows-x86_64-universal.zip` | Windows 64-bit | x86-64 with automatic supported ISA dispatch |
| `Stockless-v0.8.9-linux-x86_64-universal.zip` | Linux x86-64 | x86-64 with automatic supported ISA dispatch |
| `Stockless-v0.8.9-linux-arm64-universal.zip` | Linux ARM64 | ARMv8 / DotProd automatic dispatch |
| `Stockless-v0.8.9-android-arm64-universal.zip` | Android 8+, 64-bit ARM | ARMv8 / DotProd automatic dispatch |
| `Stockless-v0.8.9-android-armeabi-v7a.zip` | Android 8+, 32-bit ARM | ARMv7 NEON |
| `SHA256SUMS.txt` | All platforms | ZIP file integrity checksums |

**These are native UCI executables, not APKs.** Windows, Linux and Android do not share one executable. Extract the ZIP and register/import the bundled binary through a chess GUI compatible with native UCI engines. Windows users should select the included EXE. Android users must choose a GUI capable of importing external native engines such as DroidFish.

Each ZIP contains license and third-party notices, a README, branding, the exact source commit, a SHA-256 checksum for the binary, and a JSON manifest. The default Stockfish NNUE networks are embedded by the pinned source build; they do not require a separately supplied weight file.

## What's changed

1. **UCI identity and package consistency:** the engine handshake, branding manifest, package names, metadata and release tag all use `v0.8.9`.
2. **Search-policy fast path:** retain the existing per-node threat signal but move default Stockless policy arithmetic until *after* Stockfish's native shallow pruning, avoiding some calculations for moves the search already discards. Existing LMR decisions remain unchanged on the tested depth-12 bench positions, which searched **1,078,618 nodes** in both the reference and candidate.
3. **Overdrive compatibility:** keep the earlier policy timing with optional desktop Overdrive, which may affect pruning decisions.
4. **Correct match defaults:** fix a duplicated test-script assignment that inadvertently launched Stockless with Aggression 112 and Overdrive ON. Correct defaults are Aggression **145** / Overdrive **OFF**.
5. **Release/CI repairs:** correct obsolete UCI identity checks and outdated v0.7.1 filenames in the multi-platform release workflow; verify Windows/Linux handshakes, ARM ABI, manifest entries, source commit, and hashes before publishing.

## Testing and strength caveat

Under x86-64 AVX2, 1 search thread, Hash 32 MiB, 0.5+0.005 time control and the official Stockfish `8moves_v3` color-swapped opening suite:

| Opponent | Games | W/D/L | Candidate score | Relative Elo, 95% interval |
| --- | ---: | --- | ---: | --- |
| Prior Stockless base | 512 | 105 / 318 / 89 | 51.562% | +10.86 (-7.66 to +29.38) |
| Official Stockfish 19 | 256 | 35 / 182 / 39 | 49.219% | -5.43 (-28.31 to +17.45) |

A separate repetition gave 51.172% versus the prior Stockless base and 46.484% versus Stockfish 19. **All confidence intervals include a no-difference result.** These short matches do *not* establish a statistically confirmed Elo improvement or a Stockfish 19 win.

Several identical depth-limited CI throughput repeats varied from about -0.61% to +2.57%. **No reproducible NPS gain has been established.** The release does not include a claimed PGO strength improvement or the separate, experimental PR #22 lazy-threat-map patch.

Research: [PR #21](https://github.com/gaong5247-cmd/Stockless/pull/21) and [documented results](https://github.com/gaong5247-cmd/Stockless/blob/main/docs/FASTPATH_STAGING_20261019.md).

## UCI defaults

```text
id name Stockless v0.8.9
option name StocklessHybrid type check default true
option name StocklessAggression type spin default 145 min 0 max 200
option name StocklessThreats type check default true
option name StocklessOverdrive type check default false
option name StocklessThreatHistory type check default false
```

The output contains additional normal Stockfish UCI options. `StocklessMobile` defaults to true on Android and false elsewhere.

## 한국어 안내

**Stockless v0.8.9**는 탐색 구조를 보수적으로 정리하고, 잘못된 대국 스크립트 기본 설정을 바로잡은 새로운 UCI 엔진 릴리스입니다. Windows / Linux / Android용으로 각각 빌드합니다.

- **UCI 이름:** `Stockless v0.8.9`
- **기본값:** Hybrid ON, Aggression 145, Threats ON, Overdrive OFF, ThreatHistory OFF
- **안드로이드:** APK가 아니라 외부 UCI 실행 파일이며, 이를 지원하는 체스 GUI가 필요함
- **공식 Stockfish 19 대국:** 256판 49.219% (추가 반복은 46.484%). 아직 통계적으로 Stockfish를 이긴 것으로 볼 수 없음
- **PGO:** 이번 Universal 릴리스에 별도의 PGO 강화 성능을 주장하지 않음

**License:** AGPL-3.0 for Stockless integration; preserve bundled license and upstream Stockfish (GPL-3.0-or-later) / Reckless (AGPL-3.0) notices.
