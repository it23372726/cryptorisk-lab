# CryptoRisk Lab — user guide

**Live demonstration:** [Open CryptoRisk Lab](https://it23372726.github.io/cryptorisk-lab/).  
**Local, offline option:** Open [docs/index.html](docs/index.html) directly in current Chrome, Edge or Firefox after downloading the repository, with its adjacent scripts, data and styles intact. No account, backend, key or paid API is required.

CryptoRisk Lab is a **historical probabilistic research simulator**, not a live-price service and not investment advice. The interactive simulation starts at the actual BTCUSDT close on **31 December 2024 (93,576 USDT)** and uses historical model calibration from **2022–2024**. Its scenario charts do **not** predict today's price.

## Quick start

1. Open the live site or the local HTML page. The main area presents actual Binance historical daily BTC/USDT candlesticks. Forecast data are initially absent.
2. In **Scenario settings**, leave the default **1,000 USDT investment**, **30 days**, **10,000 paths per model**, **10% downside threshold**, **1.00× volatility**, **Calm** starting regime and seed **42**.
3. Select **Run simulation**. Five independently seeded ensembles of mathematical price paths are generated.
4. Observe the forecast fan and selected simulated paths grow from the real 31-Dec-2024 closing price. Use **Pause**, **Play**, **Replay** and the **day slider** to inspect the generated values.
5. Compare **terminal loss probabilities**, **95% Value at Risk**, **95% Expected Shortfall**, **daily-close touches** and **mean maximum drawdown** in the scenario results. Review model-overlay tabs to declutter the chart.
6. Open **Predictions vs Reality** to see the real historical validation. Select 2025 or 2026, an evaluated horizon and an origin date, then reveal the subsequently observed BTC closing-price path. This validation is historical and **does not change** when scenario controls change.

There is also a compact **How it works** dialog in the top navigation. It explains the entire scenario workflow without requiring you to scroll to the bottom of the research dashboard.

## Simulation controls

| Control | Supported values / default | Interpretation |
|---|---|---|
| Investment | 100–10,000,000 USDT / 1,000 | Hypothetical unleveraged amount used to scale monetary VaR and ES |
| Forecast horizon | 7–90 days / 30 | Exactly how many simulated daily closes follow the fixed origin |
| Paths per model | 1k / 5k / **10k** / 30k | Number of Monte Carlo trajectories used to estimate probabilities and tail statistics |
| Downside threshold | 1–60% / 10% | Terminal fraction lost at the final simulated day, also used for touch probability |
| Volatility scenario | 0.50×–2.00× / 1.00× | Hypothetical scaling of shock magnitude; **not** recalibration |
| Initial Markov regime | **Calm** / Volatile | Start-state sensitivity; the historically observed origin state is Calm |
| Random seed (Advanced) | 1–2,147,483,647 / 42 | Same settings and seed give identical generated results |
| EWMA decay (Advanced) | 0.80–0.99 / 0.90 | Weight on previous variance in the EWMA update |

Changing any model input **invalidates the prior scenario**, preventing a chart produced under one setting from being labelled as another. The scenario plots use 28 representative paths per model for display while computing numerical risk metrics from **all** generated paths.

## Model navigation and chart controls

The five simulated models are **GBM**, **Markov**, **EWMA**, **Adaptive GBM**, and **Gaussian GARCH**. Choose an individual model tab or **All models** to switch visible forecast overlays. The historical candles are genuine recorded Binance daily OHLC candles; projected future values are simulated **closing-price paths**, never invented future high/low candles.

Use mouse/trackpad/touch to zoom and pan, crosshair interaction to inspect dates and price values, and **Fit forecast** to restore the chosen simulated window. **Full 2025 view** reveals the genuine historical candles of that year. Historical information is shown separately from simulated paths.

## Reading the statistical outputs

**Terminal loss ≥10%:** probability that your simulated investment is at least 10% below its origin value **at the end of the chosen horizon**. It does not say anything about losses that happened earlier and recovered.

**VaR95:** loss boundary at the 95th percentile of the simulated loss distribution. A VaR95 of 200 USDT means approximately 5% of model-generated outcomes have **greater** losses, not that 200 USDT is a maximum possible loss.

**ES95:** average simulated loss among the worst approximately 5% of outcomes, also called Expected Shortfall. A larger ES indicates more severe modelled tail losses.

**Daily-close touch probability:** share of paths that touch the chosen loss threshold **at any simulated daily close**, even if they recover by the horizon. It excludes intraday lows.

**Mean maximum drawdown:** average largest decline from a prior **daily closing-price peak** along each path. It is not identical to terminal loss.

**Percentile fans:** a 5th–95th price band encloses the central 90% of projected prices in the sampled scenario. A **95% confidence interval for a Monte Carlo probability** quantifies uncertainty in the estimate, not the distribution of individual future prices.

## Historical validation: Predictions vs Reality

- Choose **2025** (original 335 overlapping 30-day origins, plus post-hoc exploratory added models) or **2026** (274 separate retrospective 30-day origins through 1 October; observed outcomes through 31 October).
- Choose an audited **7, 14, 30, 60 or 90-day** horizon. **30 days** is the preserved original primary experiment; other horizons are additional exploratory research.
- Select a date and a loss threshold of **10%, 20% or 35%**. The dashboard displays the archived model probabilities and actual observed event and recalculates each published **Brier score** from the appropriate fixed evidence.
- Press the reveal/play controls to compare the **observed H-day BTC closes** with the chosen original price and terminal loss threshold. Future prices are hidden until revealed.
- At custom scenario horizons such as 18 days, the site explicitly says that no matching historical validation has been computed. It does not silently reuse 30-day scores.

**Important:** Different years/horizons have different event rates and eligible sample sizes, so comparing raw Brier scores across them can be misleading. Overlapping windows do not constitute independent trials. The model with the smallest historical Brier score in one period is not guaranteed to dominate in another.

## A useful experiment

Start with the defaults and record each model's probability of terminal loss ≥10%, VaR95 and ES95. Next, change **Volatility scenario** from **1.00× to 1.50×**, rerun with the same seed and compare the changes. Then reset to 1.00× and switch Markov from **Calm** to **Volatile** while holding the remaining settings constant.

Interpret any differences as conditional **model sensitivity**, not reliable estimates of how actual future BTC prices will behave.

## Scientific reference and numerical consistency

The original reference simulation is described in [THEORY.md](THEORY.md) and the canonical [notebook](notebook/cryptorisk-lab.ipynb), Section 5.2. In its original **10,000-path, seed 42, 30-day, 1,000 USDT** run the notebook reported the following **reference estimates**:

| Reference statistic | GBM | Original Markov |
|---|---:|---:|
| Loss ≥10% | 21.290% | 19.210% |
| VaR95 | 209.63 USDT | 202.79 USDT |
| ES95 | 256.15 USDT | 250.67 USDT |

**Do not require bit-identical browser and Python Monte Carlo draws.** The browser uses a different RNG and performs all five models in separate random streams. Instead compare within justified Monte Carlo sampling tolerance. For the GBM 10%-loss probability, check against the independent analytical normal-CDF value with an error allowance of **four binomial standard errors plus 0.5 percentage points**, as implemented in the browser. For the **frozen historical** 2025 probabilities and Brier scores, exact parity with the notebook export **is** required and verified by automated regression scripts. See [research/WEB_V2_VERIFICATION.md](research/WEB_V2_VERIFICATION.md) for further checks.

## Limitations and reproducibility

- Calibration is historical and static: the main scenario uses **2022–2024**, not current-market parameters.
- The original Markov labels use overlapping 14-day volatility windows; observed label persistence is partly mechanical.
- Daily Gaussian log returns may underrepresent Bitcoin's extreme losses, skew and market breaks.
- The two-state Markov simulation simplifies the relationship between simulated returns and rolling-volatility labels.
- Volatility, regime, horizon and seed sliders are **hypothetical inputs**, not model forecasts of what those values will be.
- Some retrospective extensions were designed after viewing earlier outcomes. They are properly labelled **exploratory**.
- The site excludes leverage, spreads, trading fees, slippage, exchange failure and other real-world frictions.
- The unleveraged investment's theoretical worst possible loss is its entire amount even if the simulated VaR is smaller.

To reproduce the underlying evidence, run the main notebook from beginning to end or inspect the reproducibility scripts linked in [README.md](README.md). For methods and citations see [THEORY.md](THEORY.md) and [REFERENCES.md](REFERENCES.md).
