# Stockless v0.7.1 — Universal release

**October 18, 2026 · UCI engine identifier: `Stockless v0.7.1`**

This release packages the optimized Stockless search path (settings snapshot, less
redundant hot-loop work and the unchanged established v0.7 search policy) as
CPU-dispatched **native chess engines** for Windows, Linux, and Android.

## Downloads

| Release asset | Platform | What "universal" means |
| --- | --- | --- |
| `Stockless-v0.7.1-windows-x86_64-universal.zip` | Windows 64-bit x86 PCs | One EXE automatically chooses x86-64, SSE4.1, AVX2, BMI2, AVX-VNNI and suitable AVX-512 implementations |
| `Stockless-v0.7.1-linux-x86_64-universal.zip` | Linux 64-bit x86 PCs | Same x86 CPU dispatch, native Linux executable |
| `Stockless-v0.7.1-linux-arm64-universal.zip` | Linux 64-bit ARM | ARMv8 / ARMv8 DotProd dispatch |
| `Stockless-v0.7.1-android-arm64-universal.zip` | Android 8+, 64-bit ARM | ARMv8 / ARMv8 DotProd dispatch; **UCI binary**, not APK |
| `Stockless-v0.7.1-android-armeabi-v7a.zip` | Android 8+, 32-bit ARM | ARMv7 NEON compatibility build; not a CPU-dispatched multi-slice universal binary |

Windows, Linux, and Android require *different executable formats*. "Universal"
means CPU instruction-set selection **within the indicated OS and CPU family**,
not a single executable that runs across all operating systems. A Windows ARM64
or Android x86 build is not included.

## Install

Extract the matching ZIP. It contains the engine executable, `README.txt`,
`manifest.json` with the source commit and executable SHA-256, AGPL license,
attributions, logo, and upstream revision information. `SHA256SUMS.txt` at
the release root lets you check all ZIPs independently.

- **Windows:** register `stockless-v0.7.1-windows-x86_64-universal.exe` as a UCI engine in your chess GUI.
- **Linux:** run `chmod +x stockless-v0.7.1-linux-x86_64-universal` (or ARM64 name) if the archive tool did not preserve executable permissions, then register it as a UCI engine.
- **Android:** extract `stockless-v0.7.1-android-arm64-universal` and import it into a GUI supporting external native UCI engines, for example DroidFish. Use `armeabi-v7a` only for 32-bit ARM devices. Android apps may restrict launching external executables, so use a GUI that explicitly supports this import.

Test the desktop binaries with `uci` and `isready`; you should see exactly
`id name Stockless v0.7.1` and then `uciok` and `readyok`.

Stockfish's NNUE networks are **embedded in the built executable** by the
pinned source build, so the default engine does not need a separate NNUE file.

## Search defaults and measurement caveat

| UCI option | Default |
| --- | --- |
| `StocklessHybrid` | true |
| `StocklessAggression` | 145 |
| `StocklessThreats` | true |
| `StocklessOverdrive` | false |
| `StocklessThreatHistory` | false |
| `StocklessMobile` | true on Android, false elsewhere |

The search was previously benchmarked; the preliminary v0.7 microbench
showed +0.68% median NPS for the refactor and +6.50% for a **separate PGO build**
on one x86 CI runner (depth 10, four repeats). These Universal release binaries
are **not PGO trained**: universal PGO requires profiling ISA slices including
instructions unavailable on ordinary CI CPUs (Stockfish uses Intel SDE for that).
Do not interpret the earlier PGO figure as a speed result for these packages.
Nor does the version number itself indicate Elo gains. See
[`docs/OPTIMIZATION_20261018.md`](https://github.com/gaong5247-cmd/Stockless/blob/main/docs/OPTIMIZATION_20261018.md).

Every public release is gated on the Windows/Linux UCI handshake plus search
bench, Android ELF ABI checks, and ZIP manifest/hashing checks.

## 한국어

**Stockless v0.7.1**은 v0.7의 개선된 탐색 코드를 유지하면서
Windows·Linux·Android의 UCI 엔진을 각각 배포하는 버전입니다.

- Windows/Linux x86-64 Universal: 실행 중 CPU 기능을 감지하여 적합한 SIMD 경로를 자동 선택합니다.
- Linux ARM64/Android ARM64 Universal: ARMv8과 DotProd 구현을 CPU 기능에 따라 선택합니다.
- Android 32비트는 ARMv7 NEON 호환 바이너리를 따로 제공합니다.
- 안드로이드 파일은 APK가 아니라 **외부 UCI 엔진 바이너리**입니다. DroidFish 등 지원 GUI에 가져와야 합니다.
- 압축파일 안에는 라이선스·저작자 표시·SHA-256 manifest와 사용설명서가 있습니다.
- NNUE 기본 네트워크는 실행 파일에 내장됩니다. UCI 응답은 `id name Stockless v0.7.1`입니다.
- Hybrid ON, Aggression 145, ThreatHistory OFF, Overdrive OFF를 유지합니다.

**주의:** Universal 배포 바이너리는 이번에 PGO를 적용하지 않았습니다.
이전에 관측한 PGO +6.50%는 별도의 빌드 측정값이므로 Universal 성능으로
홍보해서는 안 됩니다. 공식 Elo 상승을 입증한 결과도 아직 없습니다.

License: AGPL-3.0; Stockfish GPL-3.0-or-later, Reckless AGPL-3.0.
See bundled `LICENSE`, `NOTICE.md`, `UPSTREAM.md`.
