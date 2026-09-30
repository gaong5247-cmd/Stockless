# Stockless tuning results

All Elo numbers below are **relative within the stated match setup**, not universal engine ratings.

Common STC setup unless noted:
- Cute Chess 1.5.1
- 1 thread / Hash 32 MB / MoveOverhead 1 ms
- paired color-swapped openings
- TC 0.2+0.002
- Stockfish pinned at `0a215d6c9e48856ef630013b8ab8312941a59057`

## v0.3

### Stockfish vs Stockless — 1200 games
- W/D/L: 356 / 446 / 398
- score: 48.25%
- Elo: -12.2
- 95% CI: -27.8 to +3.4

### Reckless 0.10-dev vs Stockless — 1000 games
Fairer TC: 1+0.01.
- W/D/L: 229 / 630 / 141
- score: 54.40%
- Elo: +30.65
- 95% CI: +17.59 to +43.72

The earlier 0.2+0.002 Reckless match is not used as a strength estimate because Reckless searched many moves at depth 1 under that extreme TC.

## v0.4 broad Overdrive

### Aggression sweep — 600 games each

| Aggression | Score | Elo |
|---:|---:|---:|
| 96 | 50.00% | +0.0 |
| 112 | 47.00% | -20.9 |
| 128 | 48.67% | -9.3 |
| 144 | 51.42% | +9.85 |

### Aggression 144 confirmation — 4000 games
- W/D/L: 1423 / 1175 / 1402
- score: 50.262%
- Elo: +1.82
- 95% CI: -7.22 to +10.87

Conclusion: broad Overdrive is approximately Stockfish-level at its best tested point, but there is no statistically significant positive Elo yet.

### Broad Overdrive decomposition — 500 games each

| Candidate | Score | Elo |
|---|---:|---:|
| baseline100, OD off | 50.90% | +6.3 |
| OD100 | 46.90% | -21.6 |
| OD112 | 47.80% | -15.3 |
| OD125 | 47.60% | -16.7 |
| OD150 | 48.40% | -11.1 |
| LMR125, threats off | 48.70% | -9.0 |

Broad pruning relaxation was therefore removed in v0.5.

## v0.5 Selective Overdrive

Selective Overdrive only relaxes pruning / buys extra depth in forcing checks, severe king danger and high-pressure captures.

### Coarse sweep — 600 games each

| Candidate | Score | Elo |
|---|---:|---:|
| base100 | 48.25% | -12.2 |
| selective100 | 46.17% | -26.7 |
| selective125 | 47.92% | -14.5 |
| selective150 | 50.50% | +3.5 |
| selective175 | 47.42% | -18.0 |

### Fine sweep — 600 games each

| Aggression | Score | Elo |
|---:|---:|---:|
| 140 | 47.42% | -18.0 |
| **145** | **52.17%** | **+15.1** |
| 150 | 47.33% | -18.6 |
| 155 | 49.58% | -2.9 |
| 160 | 45.92% | -28.4 |

The 145 result is promising but still a 600-game sample. A 5000-game confirmation was launched before promoting it to the stable default.

## Branch policy

- `main`: conservative/default v0.5 profile while tuning is unresolved.
- `experimental/v0.5-selective145`: Aggression 145 + Selective Overdrive enabled by default.

Only promote a candidate to main after a larger confirmation match supports the gain.
