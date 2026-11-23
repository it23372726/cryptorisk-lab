# Frozen 2026 retrospective replication: executed findings

**Research question:** Does adaptive GBM or Gaussian GARCH improve 30-day Bitcoin terminal-loss forecasts?

**No hindsight tuning:** All core parameters and evaluation dates fixed in PRE_REGISTERED_PROTOCOL.md. The fitted GARCH uses 2022–2024 only; 2025 and prior-to-origin 2026 update conditional states but never re-fit coefficients.

**Sample:** 274 overlapping 30-day forecast origins, 2026-01-01 through 2026-10-01, outcomes to 2026-10-31.
**Observed events:** 10%: 62; 20%: 38; 35%: 0.

## Terminal-loss forecast Brier scores (lower is better)

| Model | ≥10% (primary) | ≥20% | ≥35% |
|---|---:|---:|---:|
| Gbm | 0.175239 | 0.125551 | 0.000004 |
| Historical | 0.176230 | 0.126242 | 0.000022 |
| Garch | 0.176664 | 0.126132 | 0.000017 |
| Markov | 0.178221 | 0.127488 | 0.000004 |
| Ewma | 0.215885 | 0.139127 | 0.000160 |
| Adaptive Gbm | 0.218919 | 0.140701 | 0.000077 |

## Prespecified primary comparisons (10% event)

| Candidate vs original constant GBM | Difference in Brier (negative = better) | 95% block-bootstrap CI | Holm adjusted p | Claim |
|---|---:|---|---:|---|
| Adaptive Gbm | +0.043680 | [-0.005052, +0.102579] | 0.2359 | No statistically established improvement |
| Garch | +0.001425 | [-0.001689, +0.005196] | 0.4339 | No statistically established improvement |

## Interpretation and limitations

- Lower Brier scores are **descriptive** unless supported by dependence-aware uncertainty and Holm correction.
- Both GARCH and rolling GBM can dynamically change probability without necessarily predicting future loss events better.
- These 274 daily forecasts overlap over 30 days. The effective sample size is much smaller than 274.
- The test period already occurred before this report. This is a separately frozen **retrospective** replication, not prospective forecasts recorded in advance.
- EWMA is a previously inspected exploratory benchmark, not a new out-of-sample model-selection result.
- No >=35% loss events or few tail events would weaken any tail-risk conclusion.
- The Monte Carlo estimators have finite simulation uncertainty, especially for rare events.

## Files and reproduction

- PRE_REGISTERED_PROTOCOL.md: frozen research and statistical hypotheses.
- run_research.py: deterministic code and reproducible audit tests.
- results/archive_sha256_manifest.json: official archive URLs, UTC periods and SHA-256 digests.
- results/forecast_ledger_2026.csv: every forecast, prior-only state and observed 30-day outcome.
- results/metrics_2026.json: scores, bootstrap uncertainty and exact GARCH parameter estimates.
- results/forecast_probability_timeline.png and results/primary_brier_comparison.png: research figures.

Run: \`python research/phase3_2026/run_research.py --run\` with \`arch==7.2.0\` and existing scientific requirements.
