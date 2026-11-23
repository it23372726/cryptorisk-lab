# Phase 1 research: verified results and model decision

**Research date:** 2026-11-23  
**Scientific status:** Executed in a clean GitHub Actions Python environment.  
**Evidence:** [Successful 97-cell notebook / browser CI run](https://github.com/it23372726/cryptorisk-lab/actions/runs/45196840261). The notebook verification artifact includes machine-readable Phase 1 results.  
**Not a market forecast:** Parameters are based on historical 2022–2024 prices and retrospective 2025 evaluation.

## Research scope, data and evaluation discipline

Original approved question: *To what extent does a two-state Markov regime-switching model improve 30-day Bitcoin downside-risk estimation compared with constant-volatility GBM?* Keep this question and its terminal-loss probabilities, VaR95 and ES95. EWMA is the **approved stretch benchmark**, not a post-hoc substitute for the original research question. Daily-close loss-threshold crossing and maximum drawdown are **secondary exploratory metrics**.

- Historical Binance spot BTC/USDT daily prices, **2022-01-01 to 2025-12-31**.
- Original reference models calibrated using **2022–2024**, initially evaluated in **2025**.
- New regime-window/threshold and EWMA-decay candidates **fitted on 2022–2023, selected on 2024**. Final selected-parameter model versions can then be refitted on 2022–2024.
- The 2025 outcomes had already been inspected when these new candidates and risk metrics were proposed. Their additional 2025 results are **exploratory**, not fresh confirmatory validation.
- The 335 daily 30-day forecast origins in 2025 **overlap strongly**; do not treat them as 335 independent experiments.

## 1. Audit of the original 14-day median-threshold regime definition

Original rolling-volatility median threshold: **2.446% daily return SD**. States: 541 calm / 541 volatile training observations. Historical self-transition probability: **92.414%**.

**250 shuffled-return controls:** Reconstruct 14-day rolling volatility and median-split labels after destroying return chronology. The resulting self-transition rates have **median 91.767%** and 2.5%–97.5% quantiles **89.845%–93.319%**.

**Interpretation:** The observed 92.414% persistence lies **inside the shuffled-series interval**. The impressive persistence is therefore substantially consistent with a mechanical effect from overlapping rolling windows. It must not be presented as proof of genuine financial regime persistence. A permutation test of this sort diagnoses the measurement rule; it is not proof of the absence of any volatility clustering.

Actual next-day return statistics conditioned on the regime known at the previous day's close:

| Statistic | Calm | Volatile |
|---|---:|---:|
| Sample count | 540 | 541 |
| Next-day log-return SD | **2.454%** | **3.203%** |
| Mean absolute next-day log return | **1.641%** | **2.238%** |
| Next-day absolute log return ≥5% | **6.852%** | **8.318%** |

The classifications **do** separate next-day return magnitudes descriptively, but the predictive benefit for 30-day terminal-loss probabilities remains limited.

## 2. Candidate regime definitions: 2024 selection

Compared 12 alternatives using rolling volatility windows **7, 14, 21, 30** days and high-volatility thresholds at historical **50th, 65th, 75th percentiles**. Parameters were estimated on 2022–2023 returns; candidates were scored on rolling 30-day forecast origins with outcomes entirely within 2024.

| Candidate | 2024 Brier ≥10% | 2024 Brier ≥20% | Mean |
|---|---:|---:|---:|
| Original 14-day, median rule | 0.109767 | 0.009429 | **0.059598** |
| Best 21-day, 75th-percentile rule | 0.103847 | 0.007301 | **0.055574** |

An additional 30-day moving-block bootstrap gave a selected-minus-original combined Brier difference of **−0.003757** (unadjusted 95% interval **[−0.005171, −0.002132]**), but this interval is **post-selection optimistic**, because the same 2024 observations selected the winning candidate. It is not independent confirmation.

**2025 exploratory check:** At ≥10% terminal loss, the candidate scored **0.151840** versus original Markov **0.151176** (worse). At ≥20%, candidate **0.024153** versus original **0.024159** (difference negligible). Thus **do not replace the approved original 14-day Markov model** on evidence currently available. Retain the selected 21-day, 75th-percentile method as an exploratory sensitivity candidate.

## 3. EWMA volatility benchmark

Added a separately verified simulation:

- Variance update after each observed or simulated daily log return: **v(next) = λ v(current) + (1−λ)(r−μ)²**.
- At each historical forecast origin, the initial EWMA variance uses only returns available through that date.
- During 30-day simulation, future variances update from **simulated shocks**, never actual future market returns.
- Validated four predefined decay rates **0.90, 0.94, 0.97, 0.98** on 2024. Selection by mean of 10% and 20% loss Brier scores selected **λ=0.90**, with small differences from other candidates. **0.94** remains a documented classic RiskMetrics reference, not a universally optimal Bitcoin decay.
- Verified **λ=1** constant-variance limiting case against analytical GBM, reproducibility, and increasing-sample Monte Carlo stability (1k / 5k / 10k / 30k paths, five independent seeds each).

2025 exploratory comparison:

| Model | ≥10% Brier | ≥20% Brier |
|---|---:|---:|
| Calibration-only historical frequency | **0.150874** | 0.024360 |
| GBM | 0.151631 | 0.024658 |
| Original Markov | 0.151176 | **0.024159** |
| 2024-selected Markov | 0.151840 | 0.024153 |
| EWMA (λ=0.90) | 0.159060 | 0.024437 |

At the ≥10% threshold, EWMA's average probability forecast was **11.91%** versus **18.51% observed**. EWMA does not provide a consistent terminal-loss forecasting improvement over the original models. At the ≥20% threshold, its mean probability (**2.65%**) was close to the observed event frequency (**2.39%**), but its Brier score was not better than original Markov's.

The 2025 block-bootstrap comparisons do not establish broad superiority. No ≥35% loss events occurred in the test, preventing a meaningful extreme-event detection claim.

## 4. Path-dependent risk: 2024-12-31 origin scenario

For a hypothetical **1,000 USDT**, **30-day** investment, with **80,000 simulation paths per model** and the final chosen EWMA decay:

| Measure | GBM | Original Markov (calm start) | EWMA |
|---|---:|---:|---:|
| Terminal loss ≥10% | 21.01% | 19.45% | 12.96% |
| **Touched ≥10% loss at a daily close** | **39.24%** | **36.40%** | **24.11%** |
| Mean path maximum drawdown | 14.17% | 13.64% | 10.35% |
| VaR95, USDT | 209.62 | 202.21 | 158.41 |
| ES95, USDT | 258.80 | 251.48 | 211.07 |

Terminal loss and within-horizon touches answer *different* questions. A path may fall below its 10% threshold and recover before day 30. The touch measure uses daily closing prices only, not intraday lows. Lower model-estimated losses **do not imply greater real-world accuracy**.

2025 historical daily-close 10%-loss touches occurred in **26.57%** of the 335 overlapping windows:

| Model | Mean forecast | 2025 touch Brier |
|---|---:|---:|
| GBM | 39.24% | 0.211138 |
| Original Markov | 37.28% | 0.205647 |
| EWMA | 22.17% | **0.199804** |

EWMA had the lowest **descriptive** touch Brier score in this retrospective test, but the paired 30-day block-bootstrap 95% CI for EWMA − original Markov was **[−0.064330, +0.060934]**, crossing zero; the comparison is not statistically conclusive.

## 5. Model freeze for Phase 2 website

**Keep as primary and verified:** calibrated GBM and the **original 14-day median-rule Markov** model, exactly as the approved research specifies.

**Add as verified stretch benchmark:** EWMA with the **2024-selected λ=0.90**, and show that 0.94 was also evaluated. Clearly label it as a historical parameter choice; never imply real-time calibration.

**Keep exploratory, not a new default:** the 21-day / 75th-percentile Markov classifier. Explain that although it improved the 2024 selection score, it did not improve 2025 10% loss forecasting.

**Primary outputs:** 30-day terminal 10%/20%/35% loss probabilities, 95% VaR, 95% ES, model differences and historical validation. **Secondary outputs:** custom daily-close loss-touch probability and maximum drawdown. Keep calibration assumptions, confidence intervals and retrospective labels visible.

**No trading advice; no claim that one model has been proven superior**. The strongest conclusion is that modelling volatility differently changes the risk distribution, but the empirical 2025 evidence is not sufficient to establish robust general outperformance.

## 6. Verification and sources

- [GitHub Actions execution with both notebook and browser jobs passing](https://github.com/it23372726/cryptorisk-lab/actions/runs/45196840261)
- [Notebook containing auditable calculations](../notebook/cryptorisk-lab.ipynb)
- [Binance Public Data](https://github.com/binance/binance-public-data), historical daily candles
- [RiskMetrics, *Return to RiskMetrics: The Evolution of a Standard*](https://www.msci.com/documents/10199/dbb975aa-5dc2-4441-aa2d-ae34ab5f0945), EWMA recursion and reference decay factors
- [Hamilton (1989)](https://doi.org/10.2307/1912559), regime-switching methodology
- [Ardia, Bluteau & Rüede (2019)](https://doi.org/10.1016/j.frl.2018.08.009), Bitcoin regime-switching volatility literature
- [Poon & Granger (2003)](https://doi.org/10.1257/jel.41.2.478), volatility forecasting review
- [Glasserman (2003)](https://doi.org/10.1007/978-0-387-21617-1), Monte Carlo methods

Keep the old website untouched during this phase. Any future website implementation must be numerically compared to these notebook calculations and labeled as a historical research simulator.
