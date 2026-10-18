# Stockless v0.7.2-dev.20261018.2 — Threat Signal Fastpath PRE-RELEASE

**Release channel: DEV / Pre-release. Stable Stockless v0.7.1 is not modified.**

## Change from v0.7.2-dev.20261018.1

One isolated source change in `src/stockless/threat_signal.h`:
- Reuse one occupied-square bitboard while collecting non-pawn attack maps.
- Combine bishops and queens into one diagonal slider pass.
- Combine rooks and queens into one orthogonal slider pass.
- Enumerate knight attacks directly from occupancy-independent lookup tables.
- Preserve pawn attacks and omit king attacks exactly as in dev.1.

The intention is a faster but search-semantics-equivalent map. It makes no
new LMR, pruning, NNUE, threat-history or aggression changes. Hybrid ON,
Aggression 145, Threats ON, Overdrive OFF and ThreatHistory OFF stay default.

**No guaranteed speed or Elo gain is claimed.** The publication workflow
builds dev.1 and this candidate with the same x86-64 AVX2 toolchain, performs
six interleaved depth-11 benchmark comparisons and **fails the release if
the total searched node counts differ**. NPS is reported but not asserted
because a few CI measurements have noise. Before upgrading stable, confirm
the observed NPS on several CPUs and longer-time-control games.

## Platform downloads

Five independent ZIP packages with versioned UCI binaries:

- Windows x86-64 Universal, CPU instruction-set auto-dispatch
- Linux x86-64 Universal, CPU instruction-set auto-dispatch
- Linux ARM64 Universal, ARMv8/DotProd dispatch
- Android ARM64 Universal, ARMv8/DotProd dispatch
- Android ARMv7 NEON fallback

Android builds are native external UCI executables, **not APK files**.
Packages contain notices, source commit, and SHA-256 binary hashes.
The release contains `SHA256SUMS.txt` for ZIP verification.
These Universal packages are not PGO trained; earlier PGO speed results do not
apply to them directly.

UCI handshake must print:
```text
id name Stockless v0.7.2-dev.20261018.2
```

The release tag is `Stockless_v0.7.2-dev.20261018.2` and is immutable once published.

## 한국어

**v0.7.2-dev.20261018.2** 은 기존 v0.7.1 정식판을 건드리지 않는 개발용 프리릴리스임.
Threat Signal에서 나이트 공격 계산과 비숍/퀸·룩/퀸 공격 루프를
통합하고 점유 비트보드를 재사용하는 최적화를 실험함.

이 패치는 공격성이나 LMR 등의 탐색 휴리스틱을 바꾸지 않도록 작성됐음.
기존 dev.1과 동일한 노드 수를 검색하는지 별도 검사하고, NPS도 비교함.
NPS와 Elo 상승은 검증 결과 없이 단정하지 않음.
