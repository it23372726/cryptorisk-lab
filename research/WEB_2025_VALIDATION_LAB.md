# Predictions vs Reality: 2025 Historical Forecast Validation

## Purpose

This website section makes the original study's central research question testable: whether a two-state Markov volatility model estimated 30-day Bitcoin downside risk more reliably than constant-volatility GBM. EWMA is retained as an exploratory comparison, not retroactively elevated to the original primary research question.

## Original, notebook-executed data

The original 97-cell notebook (notebook/cryptorisk-lab.ipynb) is **not edited**. Instead, scripts/verify_notebook.py appends a read-only export probe to the **in-memory executed copy** after the original model code and validation calculations. The output files are docs/v2-validation-data.js and docs/v2-validation-data.json. They contain:

- 335 consecutive 2025 30-day forecast origins, 2025-01-01 through 2025-12-01, with outcomes ending 2025-01-31 through 2025-12-31.
- The actual Bitcoin price on each forecast date and its exactly 30-day-later close, from official Binance BTC/USDT 1-day UTC spot candles.
- The historically determined initial Markov state and next-day EWMA variance, computed only from prices available through that origin.
- The original GBM analytical predicted loss probabilities, original Markov predicted probabilities from 200,000 Monte Carlo paths **per initial regime**, EWMA forecast probabilities with 10,000 paths **per origin**, and a calibration-only historical-frequency benchmark.
- Actual terminal-loss events for >=10%, >=20% and >=35% price declines.
- Original 2025 Brier score summaries and dependence-aware moving-block bootstrap intervals.

These values are never regenerated or silently replaced in the browser. The CI generator asserts all 335 dates, exactly 30-day outcome alignment, positive prices and variances, probability ordering, and exact agreement of reconstructed Brier scores with the original notebook's 15-model/threshold summary.

For the original 335 windows, **62 losses of >=10%, 8 losses of >=20%, and 0 losses of >=35%** occurred. These are not independent observations: forecast windows overlap by 29 days.

## Interactive explanation

The main Validation tab is titled **Predictions vs Reality**. Its controls provide:
1. A date slider and previous/next origin buttons for any of the 335 historical forecasts.
2. Three predefined loss thresholds (10%, 20%, 35%) and navigation to recorded loss events.
3. Model-predicted probabilities next to whether the selected event actually happened. One outcome is binary and does not represent a continuous observed "probability."
4. A 335-date timeline displaying all three **archived** model probabilities and markers for **actual observed loss events**.
5. An origin-specific price replay which reveals genuine subsequent Binance daily closes progressively. The actual 30-day return is shown after revealing day 30; the model forecasts are shown immediately and use only the origin state.
6. Brier score comparisons, historical-frequency baseline and moving-block uncertainty commentary, including the "no >=35% events" limitation.

### Important distinction: price forecast bands vs evaluated risk forecasts

The **probability forecasts** displayed and scored are exactly the values exported from the executed research notebook.

For an intuitive chart, the browser also draws **illustrative projected closing-price distributions** of 1,800 independent paths per model using the 2022–2024 frozen parameters, the historical Markov regime at the selected forecast origin, and the initial EWMA variance known at that origin. This is an independent deterministic browser simulation for **visualization only**. It does not replace the notebook's Monte Carlo runs, and these price percentile regions are not confidence intervals for the scored loss probabilities.

The browser does not insert future observed prices into the model generation or daily variance recurrence. Real prices are concealed in the replay until the user explicitly reveals them.

## Score interpretation

Brier = average over forecast origins of (predicted probability − binary loss occurrence)^2. Lower means better historical scoring. However:

- 335 rolling 30-day forecast windows are **strongly dependent**.
- The original Markov-vs-GBM Brier difference is small; a lower descriptive score should not be called a statistically proven improvement without checking block-bootstrap uncertainty.
- Historical-frequency-only forecasts form a meaningful calibration-period-only benchmark.
- EWMA and post-hoc candidate choices were examined after earlier 2025 results had already been inspected. Their 2025 comparisons are **exploratory**, not fresh confirmatory validation.
- Zero observed >=35% loss events prevents demonstrating useful extreme-downside event-detection skill.

The scientific conclusion remains unchanged: these volatility assumptions yield different risk predictions, but the evidence does not establish robust general outperformance.

## Verification

GitHub Actions runs the original notebook and generates an immutable evidence artifact. The Chromium test then verifies:

- 335 genuine date-aligned observations and exact 62/8/0 event counts.
- Brier reconstruction from each stored model probability and observed event matches original notebook score to within 1e−12.
- Predefined threshold controls alter only displayed comparisons, not the frozen model forecasts or scores.
- Origin selection, previous/next controls, event navigation and actual day-30 reveal/hide.
- Forecast percentile bands remain positive, sorted, and tied to the selected observed origin price.
- Standalone file:// operation, mobile layout, complete original chart interactivity and no uncaught JavaScript errors.

## Primary sources

- Executed notebook: notebook/cryptorisk-lab.ipynb in this repository.
- Verified Phase 1 research: research/PHASE1_FINDINGS.md in this repository.
- Official Binance public market data: https://github.com/binance/binance-public-data
- Hamilton, J. D., "A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle," *Econometrica*, 57(2), 1989. DOI: https://doi.org/10.2307/1912559
- Gneiting, T. and Raftery, A. E., "Strictly Proper Scoring Rules, Prediction, and Estimation," *Journal of the American Statistical Association*, 102(477), 2007. DOI: https://doi.org/10.1198/016214506000001437
- Glasserman, P., *Monte Carlo Methods in Financial Engineering*, 2003. DOI: https://doi.org/10.1007/978-0-387-21617-1
