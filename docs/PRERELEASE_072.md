# Stockless v0.7.2-dev.20261018.1 — Development Pre-release

**This is a public DEV / Pre-release, not a stable upgrade to Stockless v0.7.1.**

- UCI name: `id name Stockless v0.7.2-dev.20261018.1`
- GitHub release tag: `Stockless_v0.7.2-dev.20261018.1`
- Source branch: `prerelease/v0.7.2-dev` (the stable `main` branch is left at v0.7.1)
- Release type: **Pre-release** (`gh release create --prerelease`).
- Build provenance: the immutable Git commit SHA is recorded per binary in its `manifest.json`.
- Default settings: Hybrid ON, Aggression 145, Threats ON, Overdrive OFF, ThreatHistory OFF.
- Search architecture: unchanged from stable v0.7.1; this preview exercises prerelease/version and universal distribution pipelines. No newly measured Elo or NPS gain is claimed.

## Preview downloads

The automated workflow publishes five platform-specific archives only after all jobs succeed:

| Archive suffix | OS/CPU | Description |
| --- | --- | --- |
| `windows-x86_64-universal.zip` | Windows x64 | Single .exe with ISA autodispatch |
| `linux-x86_64-universal.zip` | Linux x64 | CPU ISA autodispatch |
| `linux-arm64-universal.zip` | Linux ARM64 | ARMv8 / DotProd autodispatch |
| `android-arm64-universal.zip` | Android 8+ ARM64 | Native UCI executable, NOT an APK |
| `android-armeabi-v7a.zip` | Android 8+ 32-bit ARM | Native UCI NEON binary |

Every ZIP contains the executable, `LICENSE`, `NOTICE.md`, `UPSTREAM.md`,
`engine-branding.json`, an install README and `manifest.json` with the
source commit and binary SHA-256. `SHA256SUMS.txt` verifies release ZIPs.

## Validation and publishing

The dedicated `.github/workflows/prerelease-v072.yml` runs on the dev branch:
1. Build x86-64 Universal on Linux/Windows; build ARM64 Universal on Linux/Android; ARMv7 Android.
2. Validate UCI exact version and run a real desktop bench. Linux also runs the threat-history and frozen search-policy regression tests.
3. Validate Android ELF ABI and packaging.
4. Verify exactly five ZIPs, all UCI/branding versions and source commit SHA.
5. Create tag `Stockless_v0.7.2-dev.20261018.1` on the successful branch commit and
   publish as a GitHub **Pre-release**. Existing releases are not overwritten.

If one job fails, publishing is skipped. Any next dev iteration should use a
new suffix (for example `v0.7.2-dev.20261018.2`) rather than silently replacing
a published prerelease.

## 한국어

이번은 **정식판 v0.7.1이 아닌 개발용 미리보기 배포**입니다.
엔진 UCI 이름과 파일명 모두 `v0.7.2-dev.20261018.1`이며, GitHub의 **Pre-release**
표시가 붙습니다. 정식판은 수정하지 않습니다.

Windows, Linux, Android용 유니버설/호환성 바이너리를 포함합니다.
Android 파일은 APK가 아닌 외부 UCI 엔진입니다. 이번 버전은 배포체계와
버전 식별 검증이 목적이며 새로운 Elo 향상은 주장하지 않습니다.
