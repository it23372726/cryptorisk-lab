# Frozen protocol: adaptive-volatility BTC downside-risk extension

**Design locked before accessing any 2026 observed prices for this experiment.** The original 97-cell notebook, frozen 2025 evaluation, website and approved GBM-versus-Markov question remain unchanged.

## Research question

Does adapting volatility through rolling 30-day realized volatility (adaptive GBM) or Gaussian GARCH(1,1) improve **30-day terminal loss ≥10% probability forecasts** relative to the original constant-GBM and the original two-state Markov model?

**We do not assume the new models win.**

## Research chronology and status

- This extension was defined on 2026-11-24, after viewing the original 2025 results and before any 2026 price imports for this extension.
- **2026 is a newly separated retrospective holdout, not a prospective blind experiment:** calendar 2026 has already happened through October, even though its observations are not used to pick the following settings.
- To avoid incomplete months and changing results, freeze observed prices at **2026-10-31 UTC** and forecast origins at **2026-01-01 through 2026-10-01 UTC, inclusive**. Every origin has the actual price exactly **30 calendar days later**, so there will be **274** overlapping forecast windows. Do not extend through November or December after observing scores.
- No switching thresholds, tuning parameters, adding models, or changing forecast horizons after reading 2026 outcomes. Future refinements are separately labeled exploratory.

## Frozen, genuinely comparable methods

All models forecast 30-day log returns, predict loss events at ≥10%, ≥20%, ≥35% relative to the **origin closing price** (not an absolute USDT target), and use BTCUSDT Binance Spot UTC 1-day close observations. Primary: 10%; secondary: 20%, 35%. 5% and 15% are **not** part of the main experiment.

**Frozen estimation period: 2022-01-01 to 2024-12-31**. The first daily return is unavailable (no 2021-12-31 close in the defined sample), matching the original notebook. Later 2025 and pre-origin 2026 observed returns update *states*, never fitted static parameters. Never refit on 2025 or 2026.

1. **Original GBM**: fixed daily log drift 0.0006149477738712015 and fixed daily log-return standard deviation 0.028459921644738977, as exported from the executed approved notebook. Analytical Gaussian probability, identical at each origin.
2. **Original two-state Markov**: frozen original 14-day rolling sample-standard-deviation median threshold, fixed 2022–2024 transition matrix and fitted two-regime drift/volatility, with no re-estimation. At each 2026 origin classify the most recent 14 observed daily returns and use the corresponding frozen state-conditioned **30-day 200,000-path probabilities**, already verified/exported from the original notebook. No 2026 future returns in initial state. This is explicitly a two-level risk model.
3. **EWMA**: λ=0.90 selected using 2024, 2022–2024 fixed mean and initial variance sigma_cal². Filter all observed returns through each origin as \`v_next = 0.90 v + 0.10 (r - mu_cal)²\`; starting next-day variance uses current/past observations only. For every 2026 origin, forecast with 20,000 normal-shock paths for 30 days, updating variance recursively from **simulated** shocks. The forecast is exploratory relative to the original GBM/Markov research, because 2025 EWMA outcomes were already seen.
4. **Adaptive GBM, new**: same fixed calibration-period mean as original GBM; replace only volatility with sample SD (ddof=1) of the most recent **30 observed daily log returns** through the origin. Forecast Gaussian 30-day return with that volatility held fixed *within* the projected horizon. The 30-day window is frozen now, not selected for a favorable 2026 score. Use the normal CDF analytically, not Monte Carlo noise.
5. **GARCH(1,1), new**: Gaussian stationary GARCH model on **demeaned 2022–2024 log returns in percentage units (100 × (r − mu_cal))**, zero-mean residual model, p=1,q=1, fit **once** using the mature Python \`arch\` package (\`arch==7.2.0\`, Gaussian normal distribution, no variance targeting, fixed calibration mean). Freeze omega, alpha and beta. Starting variance at each origin is obtained by a **one-sided recursive filter** using returns available through that origin only. Simulate 20,000 independent Gaussian-shock paths for 30 days and update \`h_next = omega + alpha * epsilon² + beta * h\` on simulated shocks. For price returns use original fixed daily drift plus daily simulated residual /100. Never feed realized returns from future dates into forecast recursion.

The baseline comparator uses the **calibration-only 2022–2024 historical frequency** of each 30-day terminal-loss event, from the already audited 2025 notebook export. All six models/benchmarks use identical 274 forecast dates and observed outcomes. Analytical models and simulation-only models are clearly distinguished.

## Randomness, numerical verification and reporting

- Gaussian stochastic models: **20,000 paths per origin**, independent deterministic streams, seed family anchored at 20261124 and stable by origin/model. Do not select seeds after reading outcomes.
- Cross-check Gaussian GBM analytical results against separate Monte Carlo convergence; GARCH/ EWMA forecast variance one-step and recursion tests, no-lookahead state audit, positive finite variances, ordered event probabilities, duplicate-date detection.
- **Primary score**: mean Brier loss for a 10% terminal loss at day 30 (lower is better), plus calibration and forecast sharpness. Report 20%/35% Brier as secondary; low counts or zero events limit interpretation. Do not select "winner" based on a single threshold's apparent gain.
- Confidence intervals: **paired circular moving-block bootstrap**, length **30 forecast origins**, **3,000 bootstrap replicates** with fixed seed **20261124**. Estimate differences in Brier score between candidate and original GBM, and candidate and Markov. For primary multiplicity, test adaptive-GBM vs original GBM and GARCH vs original GBM as two directional superiority hypotheses, using bootstrap two-sided p-values and **Holm** correction for two comparisons (alpha 0.05). Other model comparisons / thresholds are descriptive/exploratory, with their uncertainty stated.
- Report **observed sample counts, event counts, all probabilities, Brier score, Brier difference, block interval, and adjusted p-values**. If intervals overlap zero or adjusted p-values fail threshold, state "not statistically established".
- Archive official download URL, SHA-256 and day count for each 2022–2024, 2026 month. Compare original 2024-12-31 close and original 2022–2024 drift/volatility against executed-notebook values; do not silently reinterpret upstream revisions.
- Outputs are confined to \`research/phase3_2026/\` (source code, month hashes, CSV forecast ledger, JSON metrics, plain-language findings). **Do not edit the original notebook, original research score files or docs website.**

## Limitations acknowledged in advance

Overlapping 30-day windows make the number of effectively independent outcomes much less than 274; 30-day block bootstrap is an approximation and may be fragile in a single-year holdout. Gaussian GARCH is not a guaranteed tail model, BTC returns may have skew / heavy tails. Model fit was on 2022–2024 and the chosen 2025-era extensions were motivated after observing 2025, so the 2026 test is a separate *retrospective* replication, not a sealed prospective forecast competition. A significance test does not prove economic usefulness, future profitability, or robustness across market regimes.

## Sources (methodological, not model-performance evidence)

- Binance official public spot-archive specification and 2025+ microsecond timestamps: https://github.com/binance/binance-public-data
- Tim Bollerslev (1986), "Generalized Autoregressive Conditional Heteroskedasticity," *Journal of Econometrics*, DOI: https://doi.org/10.1016/0304-4076(86)90063-1
- Robert Engle (1982), "Autoregressive Conditional Heteroscedasticity with Estimates of the Variance of United Kingdom Inflation," *Econometrica*, DOI: https://doi.org/10.2307/1912773
- Kevin Sheppard's \`arch\` forecasting documentation: https://arch.readthedocs.io/en/latest/univariate/forecasting.html
- Original executed notebook and prior research: \`notebook/cryptorisk-lab.ipynb\`, \`research/PHASE1_FINDINGS.md\`.
