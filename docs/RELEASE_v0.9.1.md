# Stockless v0.9.1 — build reliability and release validation

v0.9.1 is a maintenance release. It fixes build failures that could be hidden,
incorrect package branding paths, and incomplete regression checks. Its UCI
identity is `Stockless v0.9.1`.

The runtime search, evaluation, NNUE pin and UCI defaults remain those of
v0.9.0. This release does not claim a new Elo gain or reuse v0.9.0's match
statistics as evidence for newly compiled executables.

## Fixes

### Windows builds stop on the first failed preparation step

The PowerShell helper previously checked the compiler's exit code but not
`git submodule update` or `python tools/materialize.py`. A failed preparation
step could therefore leave an old generated source tree available to compile
and still end with a misleading success message.

Each external command is now checked immediately. Normal builds explicitly
select MinGW, a successful build must produce the expected EXE, and the helper
restores the caller's working directory after either success or failure.
The separate Windows download workflow also reads the current version instead
of expecting v0.7.1, and searches with both its AVX2 and portable binaries.

### Source generation protects original files and verifies pinned inputs

`materialize.py --out` previously recursively removed any existing output
path. The helper now rejects the repository itself, its parents, source
directories, output symlinks, Git repositories, and unrelated nonempty
directories before deletion. The default `build/stockless-src` remains valid.
Outside the repository, a new/empty directory or a previously generated tree
with a valid Stockless marker is supported.

Submodule verification now checks modified tracked files as well as HEAD.
Staged and unstaged changes cannot silently be copied into a build labelled
with a clean upstream commit. Ignored NNUE downloads and untracked local build
outputs remain usable. If an interrupted materialization leaves a nonempty
directory without a valid marker, choose a fresh output path or explicitly
remove that generated directory before retrying.

### GUI branding paths work after extracting the ZIP

`engine-branding.json` references `assets/stockless-logo.svg`; earlier packages
placed the logo only at the ZIP root. Packages now include the referenced
path while retaining the root copy for compatibility. Verification checks
both logo/icon references, manifest version, UCI identity, binary checksums,
source commit and Unix executable permissions.

### Regression tests reject missing search results and bounded waits expire

The old profile comparison could accept two outputs containing only matching
aggregate node counts and no `bestmove` lines. The new parser requires the
complete pinned benchmark, validates position ordering and terminal positions,
checks each search result, and reconciles per-position nodes with the total.
Comparisons use complete per-position fingerprints, including bestmoves,
scores and principal variations, instead of trusting aggregate counts alone.

The UCI smoke test uses an absolute monotonic deadline, so an endless stream
of `info` lines cannot keep it alive indefinitely. Shutdown has a bounded
wait and can terminate an engine that does not respond to `quit`.
Basic CI now runs the Python regression suite and Windows native-command
failure tests as well as real Windows UCI searches.

## Publication gates

The maintenance workflow is separate from the archived v0.9.0 strength
experiment. Before building release packages it requires:

1. The frozen v0.9.0 tag/commit, unchanged Stockfish/Reckless pins and clean
   tracked inputs.
2. Identical overlay and generated engine sources, with only the UCI version
   string normalized. Changes to search, defaults, generated build flags or
   the PGO procedure are rejected by this maintenance path.
3. Python and C++ regressions, UCI multi-search/thread tests, and complete
   benchmark equivalence against a same-compiler/ISA v0.9.0 rebuild under all
   eight supported test profiles.
4. Seven platform packages with the exact candidate source identity and
   verified contents. Linux/Windows PGO companions are checked against
   same-source AVX2 references.
5. A new tag and release; existing published tags/releases are never replaced.

Attached `maintenance-report.json`, `search-equivalence.txt`, `uci-smoke.txt`
and `SHA256SUMS.txt` record the publication checks. The linked Actions run
contains compiler, test and platform-build logs. These establish regression
and packaging checks, not a playing-strength estimate or a universal proof
of equivalence for every possible position.

## Downloads

| Package suffix | Use |
| --- | --- |
| `windows-x86_64-universal` | Windows 64-bit with automatic CPU instruction selection |
| `windows-x86_64-avx2-pgo` | Windows 64-bit with AVX2; profile-guided build |
| `linux-x86_64-universal` | Linux x86-64 with automatic CPU instruction selection |
| `linux-x86_64-avx2-pgo` | Linux x86-64 with AVX2; profile-guided build |
| `linux-arm64-universal` | Linux ARM64, NEON/DotProd dispatch |
| `android-arm64-universal` | Android 8+ ARM64, external UCI engine |
| `android-armeabi-v7a` | Android 8+ ARMv7 NEON, external UCI engine |

NNUE is embedded. Android downloads are native UCI executables for compatible
chess GUIs, not APKs. Android builds receive ELF/ABI checks; this release does
not assert testing on a physical Android device. PGO describes the compilation
method and does not by itself establish a speed or strength increase.

Defaults: Hybrid **ON**, Aggression **145**, Threats **ON**, Overdrive **OFF**.
Mobile is **ON on Android** and **OFF on desktop**.

## 한국어

v0.9.1은 빌드·배포·검증 안정성 개선판입니다.

- Windows에서 서브모듈 준비나 소스 생성이 실패하면 즉시 중단합니다. 오래된
  생성 소스로 빌드하고 성공으로 표시할 수 있었던 문제를 수정했습니다.
- 잘못된 `--out` 지정으로 원본 저장소를 삭제하지 못하도록 소스 생성 경로를
  확인하며, 고정된 서브모듈의 추적 소스가 수정된 경우에도 중단합니다.
- 압축을 푼 뒤 GUI가 설정 파일에 지정된 로고를 찾을 수 있도록 패키지 경로를
  바로잡고, 잘못된 로고 경로나 버전이 포함된 패키지를 검사에서 거부합니다.
- 최선 수가 없는 불완전한 벤치마크를 통과시키던 검증 허점을 고쳤습니다.
  포지션별 결과를 비교하며, UCI가 응답을 끝내지 않을 때의 대기시간도 제한합니다.
- Windows 별도 다운로드 빌드의 v0.7.1 고정 표기를 없애고 현재 버전을 사용합니다.

탐색 수식·평가·NNUE·기본 옵션은 v0.9.0과 같습니다. 공개 전 생성된 엔진 소스의
동일성과 8가지 옵션 조합의 탐색 결과를 검사합니다. 새 대국 실험에 따른 Elo
상승을 주장하지 않으며, v0.9.0의 기존 대국 보고서는 해당 릴리스에 그대로 보존합니다.
