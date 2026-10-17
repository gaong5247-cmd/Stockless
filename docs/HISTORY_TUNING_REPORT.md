# Stockless v0.7 — Tournament and Default Settings

**Source:** [GitHub Actions #39021916374](https://github.com/gaong5247-cmd/Stockless/actions/runs/39021916374) on October 17, 2026, 2,640 completed games.

| History mode | Opponent | Games | W/D/L | Score |
|---|---|---:|---|---:|
| ON weight 50 | OFF | 160 | 62/38/60 | 50.63% |
| ON weight 100 | OFF | 160 | 60/33/67 | 47.81% |
| ON weight 150 | OFF | 160 | 56/34/70 | 45.63% |
| ON weight 200 | OFF | 160 | 70/36/54 | 55.00% |
| **ON weight 200, independent confirmation** | **OFF** | **800** | **226/306/268** | **47.38%** |
| OFF | pinned Stockfish | 600 | 192/203/205 | 48.92% |
| ON weight 200 | pinned Stockfish | 600 | 182/213/205 | 48.08% |

ON 200 led the brief selection run, but its independent confirmation scored only 47.38% (−18.26 relative Elo, approximate 95% CI −37.27 to +0.65). **No demonstrated gain.** The longer-time-control test was correctly skipped. No automatic promotion occurred.

```text
id name Stockless v0.7
StocklessHybrid       true
StocklessAggression   145
StocklessThreats      true
StocklessOverdrive    false
StocklessThreatHistory false
StocklessHistoryWeight 100
```

StocklessMobile defaults to true on Android and false on desktop. Weight has no effect while ThreatHistory is OFF. This is the evidence-supported current default, not a universal optimum or official Fishtest rating.

---

## 한국어

2026년 10월 17일 2,640판 결과를 다시 확인함. 160판에서 ON 200이 55%였지만, 800판 독립 확인 대국에서는 **226승 306무 268패, 승점 47.38%**로 역전됨. Stockfish 상대 600판은 OFF가 48.92%, ON 200이 48.08%.

따라서 기본값은 **Hybrid ON / Aggression 145 / Threats ON / Overdrive OFF / ThreatHistory OFF**로 확정함. HistoryWeight 100은 History OFF 상태에서 영향을 주지 않음.

UCI 엔진 이름은 **`Stockless v0.7`**로 표시함. 엔진 버전 변경이 새로운 Elo 상승을 뜻하지는 않음.
