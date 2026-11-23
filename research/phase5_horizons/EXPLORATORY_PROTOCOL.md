# Frozen design: Multi-horizon historical forecast validation

**Research extension date:** 24 November 2026. This protocol was written before the new horizon results were computed. All 2025/2026 outcomes are already publicly available and earlier 30-day scores were inspected. **7-, 14-, 60-, and 90-day experiments are exploratory retrospective analyses, not fresh confirmatory tests.**

## Primary objective

Compare the same five BTC/USDT downside-risk models at five independently specified terminal forecast horizons: **7, 14, 30, 60 and 90 calendar days**. Preserve original notebook 30-day research and its separate 2026 holdout. Display each historical horizon with its actual endpoint date, event frequency, six forecast sources (five models and calibration-only frequency), Brier scores and descriptive paired block-bootstrap uncertainty.

## Data and origin-date coverage

Only observed UTC Binance daily spot BTC/USDT **closing prices**, never synthetic futures or intra-day candles, are used to determine historical outcomes. Source 2025 closes from docs/btc-historical.json and 2026 closes from the archived, audited 2026 ledger, cross-checking overlaps at identical dates.

Use all forecast origins from January 1 of the selected year for which the **entire H-day outcome** is observed before the frozen year endpoint (2025-12-31 or 2026-10-31). Consequently, counts are:

| H | 2025 origins | 2026 origins |
|---|---:|---:|
| 7 | 358 | 297 |
| 14 | 351 | 290 |
| 30 | **335 original notebook** | **274 original 2026 research** |
| 60 | 305 | 244 |
| 90 | 275 | 214 |

Every model and event threshold shares the exact same origins for each year/H combination. Longer horizons mean fewer origins and more overlapping outcome windows. No complete 2026 November or December outcomes are assumed.

## Models, frozen parameter choices and sampling

- **Constant GBM:** analytically evaluate daily 2022–2024 log-return mean 0.0006149477738712015 and volatility 0.028459921644738977; horizon-specific normal CDF.
- **Two-state Markov:** original 2022–2024 regime means, volatilities and transition probabilities. At each date derive current regime using the 14 most recent **observed** return values and the **exact calibration-only median** of training rolling volatility. For H!=30, simulate 200,000 paths per starting state to the required horizons, with deterministic independent seeds. Reuse original 30-day state-specific probabilities unchanged.
- **EWMA:** frozen lambda .90 and 2024-12-31 starting next-day variance 0.0004616494175752784; update state causally on observed historical returns through the origin, simulate future log-return shocks and variance recursively; 20,000 paths per origin for new horizons. **Original 30-day probabilities remain exactly unchanged** (2025 notebook 10k-path forecasts and 2026 research 20k-path forecasts).
- **Adaptive GBM:** fixed original mean, 30 latest *observed* log returns through origin, ddof=1, horizon-specific analytical normal CDF. **Original 30-day probabilities remain exactly unchanged.**
- **Gaussian GARCH(1,1):** fixed 2022–2024 fit omega 1.7429241072532673, alpha 0.1689729613867537, beta 0.6255015699659665 in percentage-return-squared. Start at 2024-12-31 next-day variance 5.547208876802669, recursively filter only observed information through each origin and simulate future shocks/conditional variance. 20,000 paths per origin for new horizons. **Original 30-day probabilities remain exactly unchanged.**
- **Calibration-only historical frequency:** empirical frequency of H-day terminal losses in the original 2022–2024 training period, using only complete windows ending no later than 2024-12-31, with no future test-year data. For H=30 reuse the archived original baseline scores/probabilities, even if any alternative training-window convention would differ.

The event outcome is **terminal** price decrease at least 10%, 20% or 35% **exactly H calendar days after** the origin. It is not a daily-close touch or maximum drawdown.

## Monte Carlo, statistics, and inference

- 20,000 deterministic simulated paths per origin for EWMA/GARCH at new H, 200,000 for Markov per starting regime. Use a **single common simulated trajectory out to the longest eligible horizon for each origin** and record end-of-horizon event frequencies at 7, 14, 60 and 90 days to avoid unrelated RNG effects among horizons. Independent, fixed model- and origin-specific streams. H=30 always copied from original archived models, never regenerated.
- Exact arithmetic and provenance audit against all pre-existing H=30 row values, dates, observed BTC closes, model regimes, variances, event counts and Brier scores.
- Compute complete per-year/H per-model probability vectors, event counts, Brier score, mean forecast probability and range. Present winning *descriptive* Brier score for each H; do not infer statistically superior future accuracy from the minimum score.
- Report paired circular moving-block bootstrap **descriptive** 95% intervals for candidate-minus-GBM Brier score with block size max(7,H) and 3,000 preselected seed replicates for each year/H; use same date resamples across models. **No new confirmatory p-values for exploratory horizons.** H=30 original 2026 Holm-adjusted p-values remain unchanged.
- Report fewer independent opportunities for H=90, serially dependent rolling outcomes, zero-event rare-tail limitations, and the fact that previous 2025/2026 results have already been examined.
- Do not tune model parameters, thresholds, horizons, path counts or random seeds based on evaluation outcomes. Do not alter original research notebooks, published historical 30-day datasets, website baseline or archived 2026 research scores.

## Website behavior

Unify existing 2025/2026 selector with a **separate historical horizon selector** offering these five verified values. All historical date sliders, forecast-origin counts, event statuses, model probability timelines, score tables, bootstrap commentary, and **real observed H-day price replays** must update from the selected year and horizon.

The scenario simulator above continues to support any integer horizon 7–90. Synchronize only exact matching verified horizon choices: if scenario H is one of the five, update the historical selector to H; otherwise prominently state that no audited historical scores exist at the selected custom H and offer the five evidence presets. Do **not** quietly substitute 30-day scores for a different simulator H. Historical presets should be independently selectable.

## Source references

- Executed original research notebook: notebook/cryptorisk-lab.ipynb
- Original 2025 validation data: docs/v2-validation-data.json
- Original 2025 five-model extension: research/phase4_2025/results/
- Original 2026 fixed holdout: research/phase3_2026/results/
- Official BTC daily data: https://github.com/binance/binance-public-data
- Bollerslev (1986), GARCH, https://doi.org/10.1016/0304-4076(86)90063-1
- Gneiting & Raftery (2007), proper scoring, https://doi.org/10.1198/016214506000001437

AI assistance must be acknowledged. All quantitative claims are to be independently reproduced from executed code and source prices, not suggested numbers.
