# Stockless 0.7 research track — Threat-Conditioned Quiet History

> **Experimental A-stage implementation. Not a claimed Elo gain.** This branch begins the 0.7 research plan without replacing Stockfish's tuned search stack.

## Design / English

The pinned Reckless revision (`7300f044812d80397960e3a27a4f085e9487419a`) has a quiet-history entry with a common factorizer and a 2×2 bucket indexed by whether the **source** and **destination** squares are threatened. Its search updates the winning quiet move and unsuccessful quiet attempts; its move picker uses the resulting history score.

Stockless ports that idea as a **separate per-Worker table**, not a wholesale replacement of Stockfish history:

- `src/stockless/threat_history.h`: bounded signed 16-bit factorizer and 2×2 threat-conditioned buckets for every side and from/to pair. Thread-local ownership through `Search::Worker` (not global shared mutable state), aging between searches and reset upon Worker clear.
- `tools/materialize.py`: patches Stockfish's `search.h`, `search.cpp`, `movepick.h`, `movepick.cpp`, and UCI options while preserving pinned sources.
- **Training:** best quiet moves gain modest history bonuses; previously tried unsuccessful quiet moves receive penalties. Reuses the existing Stockfish update point and amplitude schedule.
- **Ordering:** adds a scaled score to Stockfish's existing quiet-move sorting. Opponent attack maps are computed **once per generated quiet list**; captures, ProbCut and quiescence scoring are unchanged.
- **Control:** `StocklessThreatHistory` is **false by default**, with `StocklessHistoryWeight` range 0–200 (default 100). Setting `StocklessHybrid=false` disables the experimental effect as well. `StocklessOverdrive=false` is recommended for isolated tests.

The factorizer is shared between contexts for the same move; separate context buckets encode threatened-from and threatened-to (00, 01, 10, 11). The values are **search heuristics**, not predictions from a new NNUE network.

## Build and evaluate

```bash
git clone --recurse-submodules -b experimental/v0.7-threat-history https://github.com/gaong5247-cmd/Stockless.git
cd Stockless
python tools/materialize.py
make -C build/stockless-src/src -j2 build ARCH=x86-64-avx2
c++ -std=c++17 -O2 -Ibuild/stockless-src/src tests/threat_history_test.cpp -o /tmp/threat_history_test
/tmp/threat_history_test

# Generate paired legal openings (requires python-chess).
python -m pip install python-chess
python tools/make_openings.py tests/opening_lines.txt tests/openings.epd

# Same executable, same baseline options, randomized paired openings.
bash scripts/run-history-ab.sh 600 0.2+0.002 2

# For a more credible confirmation, run a longer fixed-TC test or SPRT
# using the same engine configuration and a new opening seed.
```

UCI experiment:

```text
setoption name StocklessHybrid value true
setoption name StocklessThreatHistory value true
setoption name StocklessHistoryWeight value 100
setoption name StocklessOverdrive value false
```

**Validation sequence:** materialization + Linux/Windows/Android builds; unit test (bucket separation, bounded updates, aging, reset); UCI + real search smoke; same-binary paired ON/OFF games; independent longer time-control confirmation. Track node counts and NPS to distinguish Elo from overhead. Do not promote this option without meaningful repeatable gains and confidence bounds.

**Next independent candidates:** threat-conditioned LMR, then recapture-aware qsearch. Do not combine them in the first A/B run, so regressions remain attributable.

**Upstream:** [Reckless quiet history](https://github.com/codedeliveryservice/Reckless/blob/7300f044812d80397960e3a27a4f085e9487419a/src/history.rs), [Reckless move ordering](https://github.com/codedeliveryservice/Reckless/blob/7300f044812d80397960e3a27a4f085e9487419a/src/movepick.rs), [Stockfish baseline](https://github.com/official-stockfish/Stockfish/tree/0a215d6c9e48856ef630013b8ab8312941a59057).

---

## 한국어

이 브랜치는 Stockless 0.7 연구의 **A단계 실험 구현**입니다. **Elo 상승이 입증된 정식 버전은 아닙니다.**

Reckless 0.10-dev 고정 커밋의 Quiet History는 수의 출발 칸과 도착 칸이 상대 공격을 받는지에 따라 4가지 버킷을 구분합니다. 기본 공통 점수도 별도로 유지합니다.

Stockless에서는 이를 Stockfish의 기존 History를 교체하지 않고 **독립적인 Worker별 테이블**로 추가했습니다.

- `threat_history.h`: 색상·출발 칸·도착 칸·위협 4상태로 점수를 저장합니다. 포화 업데이트로 오버플로를 방지하고, 새 대국에서 초기화하고 검색 사이에 점수를 감쇠합니다.
- `materialize.py`: 고정된 Stockfish 소스의 탐색·MovePicker·UCI에 필요한 부분만 주입합니다.
- **학습 방식:** 성공한 조용한 수에는 보너스를, 먼저 탐색했지만 실패한 조용한 수에는 페널티를 부여합니다.
- **착수 순서:** 기존 Stockfish 점수에 위협별 보조 History를 더합니다. 상대 공격 비트보드는 조용한 수 목록당 한 번 계산합니다.
- **기본값:** `StocklessThreatHistory=false`. `StocklessHistoryWeight=100`은 기능을 활성화했을 때의 기본 강도이며 0~200으로 조절할 수 있습니다.

ON/OFF는 **동일한 실행 파일**로 비교할 수 있습니다. 위의 `run-history-ab.sh`는 색상을 교환하는 오프닝 쌍을 사용합니다.

단, 소규모 승률 상승만 보고 'Stockfish보다 강해졌다'고 발표하면 안 됩니다. 빌드·단위 테스트·UCI 대국 확인 후 수천 판 이상 또는 SPRT로 재검증해야 합니다. 이후 별도 실험으로 History 기반 LMR, 재캡처 중심 QS를 순차적으로 검토하는 편이 안전합니다.
