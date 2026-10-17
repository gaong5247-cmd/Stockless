# Stockless v0.7 — History Tournament and Promotion

**English** / [한국어](#한국어)

This pipeline measures Reckless-inspired Threat-Conditioned Quiet History against the unchanged Stockless baseline. It does not equate exploratory results with proven Elo gains.

## Experimental design (English)

The same compiled Stockless executable plays with **ThreatHistory OFF** and **ThreatHistory ON at weights 50, 100, 150 and 200**. Every comparison uses Threads=1, Hash=32 MiB, Aggression=145, Threats ON, Overdrive OFF and Mobile OFF.

1. **Screening:** ON weights 50/100/150/200 each play 160 paired, color-swapped games against OFF at TC 0.2+0.002. The top score is a candidate only.
2. **Independent confirmation:** The candidate plays 800 games against OFF at TC 0.4+0.004 on a different opening set.
3. **Against Stockfish:** The candidate and original OFF baseline each play 600 games against the same pinned Stockfish build at TC 0.4+0.004, using identical openings and random seed.
4. **Longer-TC holdout:** If the independent confirmation has a 95% lower score confidence bound above 50%, the candidate plays 400 games against OFF at TC 1+0.01 on a fourth, disjoint opening set.
5. **Automatic default:** Only when **both** independent confirmation matches demonstrate an advantage and the Stockfish non-regression check passes, update the default on the **experimental branch** to the winning weight. Nothing is automatically merged into main.

The Stockfish guard requires the candidate-minus-OFF Stockfish score 95% CI lower bound to be greater than -0.025 (no evidence of a deterioration larger than 2.5 percentage points). The promotion script independently re-verifies minimum game counts, confidence limits and selected weight.

### Opening book

The workflow downloads the publicly released **CC0** book *6mvs_+90_+99.epd.zip* from the [official Stockfish books repository](https://github.com/official-stockfish/books), checks all positions with python-chess and splits its 2,933 distinct positions using seed 20261017:

| Set | Distinct opening positions | Role |
| --- | ---: | --- |
| screen | 600 | Compare ON weights to OFF |
| confirm | 700 | Confirmation vs OFF |
| stockfish | 800 | Both variants vs the same Stockfish build |
| long | 700 | Longer-TC confirmation vs OFF |

Each data subset is disjoint. A source SHA256 and opening manifest are saved for reproduction.

### Scripts

- [history_tournament.py](../tools/history_tournament.py) runs all pairings, selects the candidate, evaluates the statistical conditions and writes results.
- [history_stats.py](../tools/history_stats.py) strictly validates PGNs, results and opponents, and calculates score/Elo with approximate confidence intervals.
- [split_history_book.py](../tools/split_history_book.py) prepares the disjoint opening sets.
- [apply_history_default.py](../tools/apply_history_default.py) refuses to change defaults unless the promotion decision passes its independent rechecks.
- [history-tune.yml](../.github/workflows/history-tune.yml) builds the engines, runs matches and publishes PGN/log/JSON/Markdown evidence as an Actions artifact.

Edit [HISTORY_TUNE_REQUEST](../arena/HISTORY_TUNE_REQUEST) from profile=smoke to profile=full and commit to launch the complete workflow. Smoke mode uses only 8 games per screened weight, 12 confirmation games and 12 games per Stockfish comparison. **Smoke results can never trigger promotion.**

**Statistics limitation:** CIs are approximate game-level fixed-sample estimates and do not account for all paired-opening correlations. The testing is not official Stockfish Fishtest STC/LTC SPRT. Independent, longer tests remain advisable before a public strength claim. See [official Fishtest methodology](https://official-stockfish.github.io/docs/fishtest-wiki/Creating-my-first-test.html).

---

## 한국어

Stockless 0.7의 **History OFF와 ON 가중치 50·100·150·200을 자동 대국으로 비교**하고, 최적 후보를 별도 데이터로 재검증한 뒤 Stockfish와 붙이는 자동 튜닝 파이프라인입니다.

**기본 엔진은 동일한 실행 파일**을 사용하며 UCI 옵션만 바꿉니다. 공격성 145, 위협 신호 ON, Overdrive OFF, 스레드 1개, 해시 32MiB로 통일합니다.

### 대국 및 기본값 선정 절차

1. **탐색:** 네 가중치가 각각 160판씩 History OFF와 대결합니다. 여기서 높은 승점을 얻더라도 최종 결론은 아닙니다.
2. **별도 확인:** 우승 후보가 다른 오프닝 집합에서 History OFF와 800판 대결합니다.
3. **Stockfish 대국:** 우승 후보와 기존 OFF 설정이 같은 Stockfish 고정 커밋을 상대로 600판씩 대결합니다.
4. **긴 시간제어 확인:** 후보가 확인 대국에서 통계적으로 우세하면 또 다른 오프닝 집합에서 400판을 추가 진행합니다.
5. **기본값 변경:** 확인 대국 두 종류에서 모두 우세하고 Stockfish 상대 성능에 중대한 퇴보가 확인되지 않을 때만 **실험 브랜치의 기본값을 History ON + 우승 가중치로 자동 변경**합니다. 결과가 불충분하면 OFF로 유지합니다.

### 신뢰성 확보

Stockfish 공식 CC0 오프닝 북의 2,933개 포지션 중 **서로 겹치지 않는 600/700/800/700개**를 사용합니다. 색상을 교환한 페어 대국, 정확한 완료 대국 수 검사, 잘못된 PGN/엔진 오류 거부, 승무패·승점·상대 Elo·근사 95% 신뢰구간을 적용합니다.

**Actions 결과물:** PGN 전체, 경기 로그, 결정 JSON, 요약 Markdown, 오프닝 북 SHA256.

실행하려면 [arena/HISTORY_TUNE_REQUEST](../arena/HISTORY_TUNE_REQUEST)의 profile 값을 smoke에서 full로 변경해 커밋하세요. 초기 smoke 테스트는 기능 점검용이며 **기본값을 변경하지 않습니다**.

주의: 이는 자체 대국 결과입니다. Stockfish 공식 Fishtest 결과가 아니며 짧은 시간제어의 상대 Elo만으로 세계적인 절대 레이팅을 주장할 수 없습니다. 또한 기본값 변경은 **실험 브랜치에만 적용**되고 main은 PR 병합 전까지 그대로입니다.
