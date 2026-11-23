# CryptoRisk Lab v5 — Five-horizon historical validation

## Purpose

The original research tested 30-day terminal loss ≥10% for GBM versus observed-regime Markov (with EWMA and two other added benchmarks). The website also supported 7–90-day **hypothetical** scenario simulation, but until v5 its historical predictions were only evaluated at 30 days.

v5 fills that methodological gap with **five verified historical horizons** (7, 14, **30**, 60, 90 days) for 2025 and 2026 while preserving the original 30-day research results exactly.

## Original science is immutable

**H=30 remains an archived result, not a new re-simulation.**

- 2025: 335 original forecast origins and its executed-notebook GBM, Markov and EWMA probabilities are untouched. The already audited post-hoc Adaptive GBM/GARCH additions are also preserved.
- 2026: 274 original forecast origins, its five fixed-model probabilities, actual BTC prices, Brier scoring, and Holm-adjusted primary inference remain unchanged.
- No original notebook cells, original forecast CSV files or existing frozen 2025/2026 score JSON are overwritten. The new \`docs/v5-evidence-horizons.js\` references original H=30 website data rather than duplicating or mutating it.

**Other horizons are additional exploratory retrospective research**, developed after viewing earlier 2025 and 2026 results. No new confirmatory statistical claims are made, even if a different model has the lowest observed Brier score at a particular horizon.

## Consistent methodology, variable sample sizes

Each origin is defined at the observed BTCUSDT daily UTC close on that date. For each H, the event is whether the close **exactly H calendar days afterward** is at least 10%, 20%, or 35% below the initial price. An interim touch or intraday candle low does not count as a terminal loss unless the H-day close is below the threshold.

Only dates with complete H-day outcomes are included. Models are compared using exactly the same origins for a given year/H:

| H (days) | 2025 evaluated dates | 2026 evaluated dates |
|---:|---:|---:|
| 7 | 358 | 297 |
| 14 | 351 | 290 |
| **30, original** | **335** | **274** |
| 60 | 305 | 244 |
| 90 | 275 | 214 |

The 2025 window uses actual prices to 2025-12-31; the 2026 window uses observed closing prices through 2026-10-31 only. The website never extrapolates observed data. For every test horizon, the entire H-day BTC closing-price path can be replayed on the chart. The observed path is concealed until revealed by the user, and hidden future closes do not influence the chart's vertical scale.

## What each forecast represents

All model parameters were fitted using 2022–2024 only. For **new horizons**, forecasts are computed as follows:

1. **GBM**: fixed calibrated mean/volatility, analytical Gaussian log-return terminal-loss probability over H days.
2. **Original Markov**: same 2022–2024 regime-conditioned returns and transition matrix; derive the initial state from the original exact training-only 14-day rolling-volatility median. State-by-state Monte Carlo (200,000 paths) is run for the selected H; initial regimes use only observed returns through the forecast origin.
3. **EWMA**: lambda=0.90; filter the current variance using observations through each origin, then simulate future variance and returns from synthetic innovations only, 20,000 paths per origin for new horizons.
4. **Adaptive GBM**: fixed mean, current sample volatility of the most recent 30 *observed* daily log returns, held fixed through H, and analytical Gaussian terminal loss probability.
5. **Gaussian GARCH(1,1)**: the same frozen 2022–2024 GARCH fit and causal origin-specific variance filter, future variances calculated from simulated shocks only, 20,000 paths per origin for new horizons.
6. **Training-only frequency baseline**: empirical H-day terminal loss frequency from 2022–2024 calibration outcomes, calculated without test-year data. At H=30, use the original published probability instead of re-estimating this baseline.

A common simulation trajectory is used across H=7,14,60,90 at each origin for EWMA/GARCH, avoiding unrelated path-family differences when investigating how forecast duration affects risk.

## Statistical interpretation

For each year, H and threshold, the Brier score is the average squared difference between the predicted probability and the observed binary loss indicator. Lower is better *within the same year, horizon, and event threshold*.

New horizons include descriptive paired circular H-day moving-block bootstrap intervals for candidate-minus-GBM score differences, using 3,000 preselected replicates. Rolling H-day outcomes overlap up to **H−1 days**, so observed forecast dates are **not independent events**, particularly at H=90. Approximate intervals, a minimum observed Brier score, or a rapidly moving probability curve cannot by themselves establish model superiority.

**Do not compare raw Brier scores across horizons as if the underlying event frequencies were identical**. A 7-day ≥10% loss event and a 90-day ≥10% loss event are distinct and have different base rates. The original 30-day 2026 Holm-adjusted test remains the only prespecified primary test, with all other newly added horizon results explicitly exploratory.

## Website behavior

The existing 2025/2026 year selector now has an independent segmented **historical horizon** control immediately beneath it: 7d, 14d, 30d (Original), 60d, 90d. Every change updates:
- Completed origin count, eligible last date, forecast target date and H-day observed outcome;
- Five archived model probability curves, actual events and individual forecast bars;
- H-specific risk scores and descriptive uncertainty notes;
- Exact H-day observed closing-price replay, play/pause, scrubber and price axis.

The Simulation Lab above allows any integer horizon from 7 through 90. When its horizon matches a scientifically evaluated H, the historical selector follows that H. Clicking a historical H also updates the simulator's horizon and invalidates old simulated results. At custom horizons such as 18 days, a conspicuous note explains that **no historical score is available for exactly that duration** and the historical view explicitly remains on its last audited duration. No misleading use of 30-day results for non-30-day simulation values.

## Verification and sources

1. \`research/phase5_horizons/generate.py\` downloads and SHA-256-verifies the actual 36 calibration-month Binance public daily price archives against the prior research manifest, reproduces the exact original median regime threshold and confirms all **609 original 30-day** states.
2. It deterministically computes each new forecast using original fitting parameters and origin-date-only historical information, then stores all dated predictions, events and Brier scores.
3. \`research/phase5_horizons/verify_horizons.py\` reconstructs each recorded event and per-model Brier score from CSV files, verifies all year/H origin and outcome dates, and proves original H=30 data and scores have been copied without alteration.
4. \`scripts/verify_browser.py\` checks 10 year/H combinations, score parity and actual H-day replay, direct scenario-horizon synchronization and custom duration warnings, along with the original five-model scenario, offline website and mobile layout.
5. Other unchanged research, notebook, historical-data and simulation stress tests continue in GitHub Actions.

Research references:
- Original 2022–2024 notebook: \`notebook/cryptorisk-lab.ipynb\`
- Fixed 2026 30-day research: \`research/phase3_2026/\`
- Post-hoc 2025 additional models: \`research/phase4_2025/\`
- Five-horizon research protocol: \`research/phase5_horizons/EXPLORATORY_PROTOCOL.md\`
- Official Binance spot BTCUSDT daily data: https://github.com/binance/binance-public-data
- Bollerslev (1986), Gaussian GARCH: https://doi.org/10.1016/0304-4076(86)90063-1
- Gneiting and Raftery (2007), proper scoring: https://doi.org/10.1198/016214506000001437

**AI assistance:** ChatGPT helped write the code, tests and explanations. All quantitative results are independently reconstructed from archived market data, model source code and executable scientific verification, not chosen by the assistant.
