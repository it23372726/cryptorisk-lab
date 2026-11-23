# CryptoRisk Lab

**A reproducible Bitcoin downside-risk research laboratory.** Explore how different volatility assumptions affect simulated BTC/USDT returns, then test probabilistic downside forecasts against actual historical daily closes.

[**Open the website**](https://it23372726.github.io/cryptorisk-lab/) · [**Run original research notebook in Google Colab**](https://colab.research.google.com/github/it23372726/cryptorisk-lab/blob/main/notebook/cryptorisk-lab.ipynb)

The original research question asks whether a two-state Markov model estimates 30-day Bitcoin downside risk more accurately than a constant-volatility Geometric Brownian Motion (GBM) model. The project retains that original experiment and extends it with two additional volatility models and a separate 2026 evaluation.

## What the website does

- **Simulation Lab:** Compare five independent, seeded Monte Carlo scenarios from the fixed December 31, 2024 BTC/USDT forecast origin. Choose investment, horizon, loss threshold, path count, volatility stress multiplier, initial Markov regime and random seed. Explore the chart, simulated paths, forecast percentiles, VaR95, Expected Shortfall and drawdowns.
- **Predictions vs Reality:** Select **2025 or 2026** within a **single historical validation dashboard**. All five models are compared against the same real 30-day BTC outcomes for the selected year. Scrub across dates, examine six probability predictions (five models plus a historical-frequency benchmark), reveal actual daily closing prices and compare Brier scores.
- **Methodology and research evidence:** Inspect scientific assumptions, model equations, calibration, statistical limitations, and links to original verified research outputs.

All website data and simulations work as static files, including through GitHub Pages. No live prices, account connection, or API key is needed.

## Five models

| Model | What changes |
|---|---|
| Constant GBM | Drift and volatility stay fixed at 2022–2024 calibration |
| Two-state Markov | Returns and transition probabilities depend on calm/volatile regimes |
| EWMA | Daily variance responds to past and simulated return shocks |
| Adaptive GBM | A rolling 30-day historical volatility estimate replaces static sigma |
| Gaussian GARCH(1,1) | Conditional variance responds to squared past innovations and its own previous level |

**Calibration:** Static fitted parameters come from BTCUSDT UTC daily returns for 2022–2024. No future daily returns are used to initialize a forecast. The interactive scenario simulator is anchored to **2024-12-31**; it is not today's trading forecast.

## Scientific validation

**Primary event:** Bitcoin price is at least 10% lower **at the close 30 calendar days after forecast origin**. A model's predicted probability is scored against an actual binary event using Brier score; lower is better.

| Forecast source | 2025 Brier (335 dates) | 2026 Brier (274 dates) |
|---|---:|---:|
| Calibration-only historical frequency | **0.150874** | 0.176230 |
| Constant GBM | 0.151631 | **0.175239** |
| Two-state Markov | 0.151176 | 0.178221 |
| EWMA | 0.159060 | 0.215885 |
| Adaptive GBM | 0.154912 (exploratory) | 0.218919 |
| Gaussian GARCH(1,1) | 0.151766 (exploratory) | 0.176664 |

**Interpretation:** In the original 2025 experiment, Markov had a small descriptive advantage over GBM, but the historical-frequency benchmark scored better than both. In the separate fixed-protocol **2026 retrospective** holdout, constant GBM scored better than Markov, GARCH, Adaptive GBM and EWMA. **Neither new adaptive model established a statistically supported improvement over GBM** on the pre-specified 2026 primary metric.

**Crucial research distinction:** The original 2025 GBM, Markov, EWMA and historical-frequency values are preserved from the executed notebook, unchanged. Adaptive GBM and GARCH were subsequently added to the 2025 comparison **after 2025 outcomes were inspected**, so those added 2025 results are explicitly **post-hoc exploratory**, not a new independent confirmation. The 2026 fixed-protocol evaluation was conducted separately, but is also retrospective rather than genuinely prospective.

Forecast windows overlap by up to 29 days and cannot be treated as independent trials. Extreme loss events are sparse (no ≥35% terminal losses in these tested windows). Gaussian shocks may underrepresent heavy tails. These are research comparisons, not investment advice.

## Reproduce the science and website

- **Original assignment research:** `notebook/cryptorisk-lab.ipynb` (preserved). Run all in a fresh Colab session.
- **Fixed 2026 extension:** `research/phase3_2026/run_research.py`, with protocol, archived Binance source hashes, dated forecast ledger, fitted GARCH parameters, Brier scores and moving-block-bootstrap uncertainty in `research/phase3_2026/`.
- **Exploratory 2025 additional models:** `research/phase4_2025/run_exploratory.py`, with research-integrity explanation and per-origin forecasts in `research/phase4_2025/`.
- **Standalone website:** Open `docs/index.html`, or serve the `docs/` directory from any basic static web server.
- **Audits:** `scripts/verify_browser.py`, `scripts/verify_v3_evidence.py`, `research/phase4_2025/verify_extension.py`, and `scripts/verify_v3_models.cjs`.

GitHub Actions rerun the original scientific notebook, verify source data and stored historical score parity, stress-test five Monte Carlo ensembles, test the year selector and inspect the site in Chromium.

## Research sources

1. [Binance official BTCUSDT spot daily data archives](https://github.com/binance/binance-public-data).
2. Hamilton, J. D. (1989), *A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle*. [DOI](https://doi.org/10.2307/1912559).
3. Engle, R. F. (1982), *Autoregressive Conditional Heteroscedasticity*. [DOI](https://doi.org/10.2307/1912773).
4. Bollerslev, T. (1986), *Generalized Autoregressive Conditional Heteroskedasticity*. [DOI](https://doi.org/10.1016/0304-4076(86)90063-1).
5. Gneiting, T. and Raftery, A. E. (2007), *Strictly Proper Scoring Rules, Prediction, and Estimation*. [DOI](https://doi.org/10.1198/016214506000001437).
6. [arch Python documentation](https://arch.readthedocs.io/en/latest/univariate/forecasting.html).

For methods, model caveats and traceable results, see `research/PHASE1_FINDINGS.md`, `research/phase3_2026/PRE_REGISTERED_PROTOCOL.md`, and `research/phase4_2025/EXPLORATORY_PROTOCOL.md`.

## AI assistance

ChatGPT was used to assist research interpretation, develop simulation and website code, create reproducibility audits, and draft documentation. Quantitative claims are grounded in recorded source data and independently executed research and test scripts; AI-generated text is not itself evidence of model accuracy.
