# Frozen add-on: 2025 Adaptive GBM and GARCH exploratory evaluation

**Scope: complete the five-model historical website, without changing the original 2025 experiment.**

This method was specified on 2026-11-24 after the original 2025 outcomes had already been examined. The 2025 candidate comparisons are therefore **post-hoc exploratory descriptions**, not independently pre-registered tests, not prospective forecasts, and not fresh out-of-sample superiority evidence. The previously frozen 2026 holdout remains the separate replication and is unchanged.

## Data and samples

Reuse the published/verified original 2025 daily UTC BTCUSDT OHLC series in \`docs/btc-historical.json\`, with 2024-12-01 through 2025-12-31 continuous candles. Reuse **exactly the same 335** dated forecast origins 2025-01-01 through 2025-12-01, 30-day terminal prices, historical events and original 2025 GBM/Markov/EWMA probabilities from the executed notebook's immutable \`docs/v2-validation-data.json\`. No different sample dates, thresholds or event definitions.

The original **2022–2024** calibration, fixed drift \`mu=0.0006149477738712015\`, and 2026 research extension's parameters, chosen before this 2025 calculation, are reused. No refitting to 2025 returns. Observed 2025 returns update **past-only forecasting states**, never estimated model coefficients.

## Candidates, calculations and frozen random stream

1. Adaptive GBM: sigma is the **sample SD (ddof=1) of the latest 30 actual daily close-to-close log returns available through each forecast origin**. Use the original frozen calibration-period GBM mu. The daily SD stays fixed within each forward 30-day conditional forecast. Calculate 10%,20%,35% terminal-loss probabilities **analytically** with normal CDF: \`Phi((log(1-q)-30*mu)/(sigma_rolling30*sqrt(30)))\`.
2. Gaussian GARCH(1,1): use the 2026 study's **exact, once-fitted 2022–2024** frozen parameters in squared percentage-return units: omega \`1.7429241072532673\`, alpha \`0.1689729613867537\`, beta \`0.6255015699659665\`, mean \`0.0006149477738712015\`. At the close of 2024-12-31 its fixed next-day conditional variance is \`5.547208876802669\` (percent-return squared). After observing each next actual 2025 day's return \`r_t\`, update the **next-day** origin state using \`h_next = omega + alpha*(100*(r_t-mu))**2 + beta*h\`. At any 2025 origin, forecast day+1 onward with **20,000 independent simulated normal-shock paths**, future states updated using simulated shocks only. No future observed return enters the simulation.
3. Seeds: deterministic 2025-tagged stream \`20261124 + 202500000 + origin_index*1009 + 211\`. This distinguishes 2025 trial streams from the 2026 research's independently specified stream. Paths per forecast: 20,000. Horizon: 30 days. Thresholds: 10%, 20%, 35%. No parameter search or seed selection on outcomes.

## Evaluation and interpretation

- Score the two candidates against exactly the **same observed 2025 binary terminal-loss events** used by the original notebook; do **not** modify any original 2025 probability, Brier score, sample or year.
- Archive all 335 origins, model forecasts, pre-origin states and 2025 evaluation Brier scores in a **separate additive** 2025 extension JSON. The website may merge the original and exploratory data **in memory for display**, while keeping source files unchanged.
- For transparency, add paired circular 30-origin-block bootstrap percentile intervals (3,000 seeded replications, fixed seed 20261124) for the **descriptive** Brier differences to original GBM and Markov. These intervals do not transform the post-hoc comparison into a valid confirmatory claim.
- Original 2025 result: descriptive Markov/GBM comparison remains as published. New 2025 candidates are marked **exploratory**, including graph legends, forecast bars, score rows, range fans and interpretation.
- If a new model appears to outperform in 2025, do **not** claim superiority. The previously assessed separate 2026 holdout is still the relevant test for generalization and showed **no statistically established advantage** of the new candidates over GBM.
- Website scenario sliders remain entirely independent from archived 2025 forecasts and results.

## Integrity checks

- All selected real BTC prices/dates exactly match original 335 dated notebook records, and all observed event counts remain 62/8/0.
- Fixed training-period parameters match published 2026 metrics; rolling sigma and GARCH state use only data available through their origin.
- GARCH initial variance and first 2025 transition verified against the independent 2026 research equations. Monotone, finite probabilities on 10/20/35.
- Reconstruct all Brier scores from the saved per-date ledger; check origin row count, no duplicates, probabilities in [0,1], and original research data unchanged.
- Browser tests check all five 2025 models across timeline, date selection, event controls, replay, score summaries, file:// operation and 2026 regression.
- Do not cherry-pick "winning" thresholds or hide losses. The intended contribution is **comparability and transparent negative/positive findings**, not model selection.

## References and provenance

- Original executed notebook: \`notebook/cryptorisk-lab.ipynb\`
- Original 2025 frozen evidence: \`docs/v2-validation-data.json\`
- Frozen 2026 protocol and Gaussian GARCH fit: \`research/phase3_2026/PRE_REGISTERED_PROTOCOL.md\`, \`research/phase3_2026/results/metrics_2026.json\`
- Binance spot BTC/USDT UTC archives and verified monthly hash manifest: https://github.com/binance/binance-public-data
- Bollerslev (1986), *Generalized Autoregressive Conditional Heteroskedasticity*, https://doi.org/10.1016/0304-4076(86)90063-1
- Gneiting & Raftery (2007), *Strictly Proper Scoring Rules, Prediction, and Estimation*, https://doi.org/10.1198/016214506000001437

AI-assisted implementation and scientific writing are disclosed; scientific findings derive exclusively from executed code and the independently archived research data.
