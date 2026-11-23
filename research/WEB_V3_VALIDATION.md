# CryptoRisk Lab v3: Five-model website and retrospective validation

## What was built

CryptoRisk Lab v3 integrates the existing BTC/USDT risk simulation and the independently verified 2025/2026 research.

**Main functions:**
- Five independent, reproducible historical scenario ensembles: constant GBM, two-state Markov, EWMA, Adaptive GBM and Gaussian GARCH(1,1).
- Actual 2024-12 through 2025-12 BTCUSDT UTC daily candlesticks, independently generated 7–90-day forecast fans and selectable simulated paths.
- 2025 Predictions vs Reality: 335 original 30-day GBM/Markov/EWMA forecast origins, exact notebook probabilities, original Brier scores and authentic future prices.
- 2026 Holdout: 274 retrospective 30-day forecast origins, six fixed-source probability forecasts (five models plus calibration-only historical-frequency benchmark), real daily closing-price replay through 2026-10-31, Brier scoring and dependence-aware uncertainty.
- Responsive visual layout, touch-friendly chart, right-axis cursor price, accessible controls, independent tests and offline local HTML operation.

**The website does NOT refit any model from future observations.** Historical evaluation results and the original notebook are left untouched. Changing investment, horizon, random seed, risk threshold or stress multiplier changes hypothetical 2024-anchored scenario simulations only, never the stored 2025 or 2026 research scores.

## Exactly what the scenario models mean

All five interactive simulations start at the observed 2024-12-31 BTC/USDT close of **93,576 USDT**. Frozen 2022–2024 calibration is used for all fitted models.

1. **Constant GBM:** fixed daily log drift 0.0006149477738712015 and log-return sigma 0.028459921644738977; Gaussian log returns and multiplicative prices.
2. **Two-state Markov:** original, state-dependent fitted Gaussian returns and transition matrix; the initial calm/volatile state is a user-selected *scenario*.
3. **EWMA:** lambda is adjustable, using the 2024-12-31 initial variance exported for each lambda from the executed original research. Simulated Gaussian innovations update conditional volatility, not actual future returns.
4. **Adaptive GBM:** daily log-return sigma is the sample standard deviation (ddof=1) of the **30 observed daily returns ending 2024-12-31**, available without lookahead. Mean remains fixed at the original GBM calibration mean. Sigma is held fixed within the scenario horizon.
5. **Gaussian GARCH(1,1):** one fitting pass on 2022–2024 residuals with frozen omega=1.7429241072532673, alpha=0.1689729613867537, beta=0.6255015699659665. Next-day origin variance=5.547208876802669 in percent-return-squared. Recursion uses *future simulated percentage-return innovations*. The historical 2026 study uses origin-specific filtered GARCH states in its separate frozen ledger.

For every scenario model, a volatility stress multiplier !=1 is *hypothetical*, not re-estimation. Results are Monte Carlo loss probabilities, VaR95/ES95, cumulative maximum drawdown, terminal returns and daily-close loss touches. Percentile price fans are **simulated price distributions**, not guarantees or predictive confidence intervals.

## Historical evaluation: separate 2025 versus 2026 evidence

**2025 original:** all 335 30-day origins and binary actual outcomes from the executed 97-cell notebook. ≥10% Brier scores: historical baseline 0.150874; Markov 0.151176; GBM 0.151631; EWMA 0.159060. The Markov advantage over GBM was **not statistically conclusive**. The original 2025 display and its no-lookahead notes are preserved.

**2025 exploratory five-model add-on (implemented after viewing 2025 outcomes):** Apply the *later frozen 2026* Adaptive GBM (causal rolling 30-return SD, analytical loss CDF) and fitted Gaussian GARCH(1,1) (2022–2024 coefficients and next-day variance; 20,000 seeded paths/origin) to **exactly the same 335 original 2025 dates**. The source 2025 notebook, original GBM/Markov/EWMA forecast probabilities, event counts and Brier scores are untouched. The additional model results are stored separately in `docs/v4-exploratory-2025-data.json` and `research/phase4_2025/FINDINGS.md`, with the method declared in `research/phase4_2025/EXPLORATORY_PROTOCOL.md`. The browser joins the results **only for display**.

For 2025 ≥10% terminal loss: historical baseline 0.150874; Markov 0.151176; **GARCH (exploratory) 0.151623**; GBM 0.151631; **Adaptive GBM (exploratory) 0.154912**; EWMA 0.159060. The GARCH-versus-GBM difference is only about −0.000009 and the exploratory block-bootstrap interval includes zero. Do not claim a GARCH accuracy advantage. The post-hoc 2025 results **do not replace 2026's separate retrospective holdout** or establish any statistically confirmed winner.

The 2025 web explorer now presents five probability curves, individual forecasts, historical score rows, all six sources including the calibration-only frequency benchmark, and independently simulated illustrative price bands for Adaptive GBM/GARCH. The only valid observed candle records are the verified Binance daily OHLC files. New past-only conditional sigma/GARCH variance estimates are fixed from the 2022–2024-calibrated research definition and **never generated from future actual prices**.

**2026 separated retrospective holdout:** all 274 origins (2026-01-01 through 2026-10-01), real final closes through 2026-10-31. 62/274 events at ≥10%, 38/274 at ≥20%, 0/274 at ≥35%.

For 2026 ≥10% loss, verified Brier scores (lower is better):

| Forecast source | Brier score |
|---|---:|
| GBM | 0.175239 |
| Calibration-only historical baseline | 0.176230 |
| Gaussian GARCH | 0.176664 |
| Original Markov | 0.178221 |
| EWMA | 0.215885 |
| Adaptive GBM | 0.218919 |

Neither new adaptive model established a statistically significant improvement over original GBM in the prespecified 10% terminal-loss event, after paired moving-block bootstrap and Holm adjustment. An adapting risk estimate does not necessarily forecast losses better.

The 2026 explorer embeds **exact** archived predictions and outcomes from the verified research ledger (research/phase3_2026/results/forecast_ledger_2026.csv). It does not run browser-side fitted GARCH or independently simulate historical 2026 probabilities. Its price replay uses only real recorded **daily closes**: no 2026 OHLC candles, volumes or synthetic intraday prices are displayed. When a future-day replay price is hidden, the price chart's range also excludes it.

**Limitations:** 30-day rolling forecast windows overlap, so 274 observations are not independent; Bitcoin returns may be heavy-tailed and non-Gaussian; no ≥35% loss events occurred; the 2026 evaluation is retrospective, not prospective; original EWMA exploratory decisions were already informed by earlier outcomes; scores can differ because historical event frequencies differ across years.

## Model and website integrity

The following checks run in GitHub Actions:
- scripts/verify_v3_evidence.py checks *every* embedded 2026 forecast and observed outcome against the frozen CSV ledger, exact Brier score parity, GARCH fit, threshold events and sample dates.
- scripts/verify_browser.py checks all five models, exact seeded reproducibility, model risk table, 2025 notebook-derived scores, new 2026 score and event explorer, actual-price replay, crosshair, drag/zoom, mobile responsiveness and standalone file:// loading.
- scripts/verify_v4_evidence.py and research/phase4_2025/build_exploratory.py check every new 2025 model origin, 30-return sigma, frozen GARCH state, original 2025 source integrity, exact model score reconstruction, deterministic Monte Carlo reproducibility, post-hoc labelling and 2025 browser data consistency.
- scripts/verify_notebook.py executes the original scientific notebook and verifies its calculations, without overwriting notebook source.

To run locally, open docs/index.html in a modern browser. To develop further, serve docs/ with a basic local HTTP server. No chart CDN, Binance API key, Node server or trading connection is required.

## Reproducibility and primary citations

Primary executed research sources:
- Original research notebook: notebook/cryptorisk-lab.ipynb
- Original scientific analysis: research/PHASE1_FINDINGS.md
- Frozen independent experiment protocol: research/phase3_2026/PRE_REGISTERED_PROTOCOL.md
- 2026 executed findings, statistics and archived source hashes: research/phase3_2026/results/

Scientific references:
- Binance public daily spot archives and timestamp conventions: https://github.com/binance/binance-public-data
- Engle (1982), conditional heteroskedasticity: https://doi.org/10.2307/1912773
- Bollerslev (1986), GARCH: https://doi.org/10.1016/0304-4076(86)90063-1
- Hamilton (1989), regime-switching time series: https://doi.org/10.2307/1912559
- Gneiting & Raftery (2007), proper scoring rules: https://doi.org/10.1198/016214506000001437
- Kevin Sheppard, arch forecasting: https://arch.readthedocs.io/en/latest/univariate/forecasting.html

**AI assistance disclosure:** ChatGPT assisted with software, tests and research explanation. The scientific outcomes are attributed only to the independently executed archived code, frozen source data and audited notebooks, not to an AI-generated estimate.
