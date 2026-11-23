# Theory and mathematics

CryptoRisk Lab compares models for downside risk in daily BTC/USDT spot prices. The **primary scientific question** is whether a two-state observed-regime Markov model improves **30-day terminal-loss probability estimates** over a constant-volatility geometric Brownian motion (GBM) baseline. The historical tests do **not** establish general Markov superiority. EWMA is an additional dynamic-volatility benchmark; adaptive GBM and Gaussian GARCH(1,1), and horizons other than 30 days, are separately labelled retrospective extensions.

## 1. Scope, definitions and units

Let \(P_t>0\) be the BTC/USDT UTC daily closing price in **USDT per BTC** at day \(t\), and let \(r_t=\ln(P_t/P_{t-1})\) be the **dimensionless daily log return**. Let \(V_0>0\) be a hypothetical unleveraged investment denominated in USDT, \(H\) a horizon in calendar days, and \(\ell\in(0,1)\) a loss threshold.

At the forecast origin \(t\), a simulated terminal investment has value \(V_{t+H}=V_0 P_{t+H}/P_t\). Define monetary loss \(L=V_0-V_{t+H}=V_0(1-P_{t+H}/P_t)\), in USDT. Losses can be negative when the investment makes a gain. The terminal-loss event is **\(L\geq \ell V_0\) exactly at day \(H\)**, not a loss touched at some intermediate day. A 10% loss means \(P_{t+H}\leq0.9P_t\).

The approved primary horizon is **30 days**, with 10%, 20%, and 35% terminal-loss thresholds. The fixed simulated scenario origin is **31 December 2024**. Model parameters are estimated from **2022–2024**, with subsequent retrospective evaluation in 2025 and separately in 2026. There are no live prices, leverage, trading costs or personalized trading recommendations.

## 2. Data preparation and input modelling

Historical BTCUSDT Binance **spot** UTC 1-day candles are downloaded from the [official public archive](https://github.com/binance/binance-public-data). The primary notebook verifies expected daily dates, uniqueness, positive finite prices and timestamp units; Binance spot timestamps switch from milliseconds to microseconds beginning in January 2025. The first log return in 2022 is undefined because the chosen sample does not include the previous day's close.

For rolling-window regime identification, let \(s_{t,w}\) be the **sample standard deviation** (ddof=1) of the last \(w\) daily log returns, with the window ending at \(t\). The original rule is \(w=14\) and threshold \(q\), the median of complete rolling-volatility values from the 2022–2024 calibration period:

\[
S_t=\begin{cases}0& s_{t,14}<q\quad\text{(calm)}\\
1& s_{t,14}\ge q\quad\text{(volatile)}.\end{cases}
\]

The calculated original threshold is approximately **2.446% daily log-return standard deviation**. The interpretation is a statistical regime label, not an observed economic or physical market state. Adjacent 14-day windows share 13 daily observations, which can create artificial apparent label persistence.

**Important time alignment:** For the Markov model, the return distribution conditioned on current state \(S_t\) describes the **next day's** log return \(r_{t+1}\). Forecast-origin states use only information known at the origin.

## 3. Model A: fixed-volatility GBM baseline

With calibrated mean daily log return \(\mu\) and daily log-return standard deviation \(\sigma>0\),

\[
r_{t+d}=\mu+\sigma Z_d,\quad Z_d\overset{\mathrm{iid}}{\sim}N(0,1),
\qquad
P_{t+d}=P_{t+d-1}\exp(r_{t+d}).
\]

Here \(d=1,\ldots,H\). This is the daily lognormal discretization of GBM, with \(\mu\) already defined as a **log-return mean**, not an undiscounted price drift requiring another \(-\sigma^2/2\) correction.

The fitted daily parameters from the executed 2022–2024 research notebook are:

| Parameter | Value | Units |
|---|---:|---|
| \(\mu\) | 0.0006149477738712015 | log return/day |
| \(\sigma\) | 0.028459921644738977 | log-return SD/\(\sqrt{\text{day}}\) under a daily-step convention |
| Default \(H\) | 30 | days |
| Default \(V_0\) | 1,000 | USDT |

The terminal cumulative log return obeys \(Y_H=\ln(P_{t+H}/P_t)\sim N(H\mu,H\sigma^2)\). Setting \(m=H\mu\), \(s=\sqrt{H}\sigma\), and \(\Phi\) to the standard normal CDF:

\[
\Pr(L\ge\ell V_0)=\Phi\!\left(\frac{\ln(1-\ell)-m}{s}\right).
\]

These closed-form probabilities provide a useful **independent numerical oracle** for the Monte Carlo implementation.

## 4. Model B: two-state Markov regime switching

Let \(S_d\in\{0,1\}\) indicate calm or volatile conditions. A first-order discrete-time Markov chain has row-stochastic transition matrix

\[
\mathbf P=\begin{bmatrix}p_{00}&p_{01}\\p_{10}&p_{11}\end{bmatrix},
\quad p_{ij}=\Pr(S_{d+1}=j\mid S_d=i),
\quad p_{ij}\ge0,\ \sum_jp_{ij}=1.
\]

Count observed consecutive 2022–2024 label transitions \(n_{ij}\) and estimate \(p_{ij}=n_{ij}/(n_{i0}+n_{i1})\). The original fitted matrix is

\[
\mathbf P =
\begin{bmatrix}
499/540 & 41/540\\
41/541 & 500/541
\end{bmatrix}.
\]

The daily **next-return** conditional distributions are \(r_{d+1}\mid S_d=i\sim N(\mu_i,\sigma_i^2)\), with original fitted values

| Regime | Mean \(\mu_i\) (daily log return) | SD \(\sigma_i\) (daily log return) |
|---|---:|---:|
| Calm (0) | 0.0011709082452031764 | 0.02453708413230616 |
| Volatile (1) | 0.0002649261708609547 | 0.032033470949311985 |

For each simulated path, initialize \(S_0\) using the observed origin regime (calm for 2024-12-31 in the main scenario), generate a next-day return conditional on \(S_d\), update the price, then sample \(S_{d+1}\) from row \(S_d\) of \(\mathbf P\). The simulator uses independent seeded random streams for shocks and regime transitions. It does **not** recompute the rolling-volatility label from simulated returns each day, a simplification to disclose.

Independent theoretical checks include \(\pi_d=\pi_0\mathbf P^d\) for the state occupancy distribution at day \(d\), transition-frequency comparisons, valid matrix rows and the **identical-regime limiting case**: if both regimes have equal means and volatilities, their terminal-return distribution agrees with the one-distribution GBM benchmark within Monte Carlo error.

## 5. Model C: EWMA conditional volatility

The EWMA benchmark maintains a time-varying daily return variance \(v_d>0\). For the current return deviation \(\epsilon_d=r_d-\mu\), its one-step recursion is

\[
v_{d+1}=\lambda v_d+(1-\lambda)\epsilon_d^2,\qquad 0<\lambda\le1.
\]

The next return is sampled as \(r_{d+1}=\mu+\sqrt{v_{d+1}}Z_{d+1}\). At a historical origin, initialize \(v\) by filtering **observed past and current returns only**. Subsequently update variance using **simulated shocks**, never unknown future observations. A 2024 validation exercise selected \(\lambda=0.90\); the commonly discussed 0.94 is a comparison value, not a universally optimal BTC parameter.

At \(\lambda=1\), variance is fixed, providing a constant-volatility limiting-case verification. EWMA is the proposed stretch benchmark, but its 2025 results are **exploratory** because some 2025 observations had already been inspected before this extension was designed.

## 6. Additional models: adaptive GBM and Gaussian GARCH(1,1)

**Adaptive GBM:** hold the calibrated \(\mu\) constant and replace \(\sigma\) by the sample standard deviation of the **30 latest observed log returns available at each forecast origin**. This volatility is held fixed over the simulated horizon and gives an analytical normal-CDF terminal-loss probability. The window length was fixed for the separate 2026 retrospective study.

**Gaussian GARCH(1,1):** estimate \(h\), the conditional variance of demeaned returns expressed in **percent squared**. Fitted using \(\text{arch}\) once on 2022–2024 demeaned return residuals,

\[
h_{d+1}=\omega+\alpha\epsilon_d^2+\beta h_d,\qquad
\epsilon_{d+1}=\sqrt{h_{d+1}}Z_{d+1},
\quad r_{d+1}=\mu+\epsilon_{d+1}/100.
\]

Here \(\omega\) is in percent-return squared, \(\alpha,\beta\) are dimensionless, and \(h\) is conditional variance of the **percentage-point** return. The archived fit uses \(\omega=1.7429241072532673\), \(\alpha=0.1689729613867537\), and \(\beta=0.6255015699659665\). Frozen coefficients are used for future evaluations; only origin-specific variance state is updated with observed **pre-origin** returns. Future paths evolve from their own simulated residuals. See the [frozen 2026 protocol](research/phase3_2026/PRE_REGISTERED_PROTOCOL.md) for the exact chronology and fitting specification.

Adaptive GBM and GARCH were added after the original model comparison, and their extra 2025 results are explicitly **post-hoc**, not fresh independent evidence of forecasting superiority.

## 7. Downside risk statistics and analytical checks

For \(N\) simulated paths, define \(L_i=V_0(1-P_{H,i}/P_0)\). The Monte Carlo estimator for loss event \(A_\ell=\{L\ge\ell V_0\}\) is \(\hat p_\ell=N^{-1}\sum_i\mathbf1(A_{\ell,i})\). Its approximate standard error is \(\sqrt{\hat p(1-\hat p)/N}\). The notebook reports **Wilson 95% intervals** for individual binomial probability estimates.

For a loss-distribution random variable \(L\), 95% Value at Risk is the 95th percentile of \(L\): \(VaR_{.95}=\inf\{x:\Pr(L\le x)\ge .95\}\). For this continuous loss distribution, \(ES_{.95}=E[L\mid L\ge VaR_{.95}]\). Sample ES averages losses in the upper 5% tail, and must not be confused with a worst-possible loss guarantee.

For baseline GBM, with \(m=H\mu\), \(s=\sigma\sqrt H\), and \(z_{.05}=\Phi^{-1}(.05)\), the **independent analytical checks** are

\[
VaR_{.95}=V_0\big[1-\exp(m+s z_{.05})\big],
\]

\[
ES_{.95}=V_0\left[1-\frac{\exp(m+s^2/2)\Phi(z_{.05}-s)}{.05}\right].
\]

For secondary path-dependent experiments, a **daily-close touch** means \(P_d\le(1-\ell)P_0\) for at least one observed or simulated daily close \(d\le H\). Maximum drawdown is \(\max_{d\le H}(1-P_d/\max_{j\le d}P_j)\). Neither statistic uses intraday lows.

A 5th–95th *forecast price percentile band* is not a 95% *confidence interval on an estimated loss probability*. The website labels these concepts separately.

## 8. Historical validation and statistical uncertainty

For origin \(t\) and threshold \(\ell\), the realized event \(y_t\in\{0,1\}\) is whether the **exact \(H\)-day** terminal close meets the loss threshold. With predictive probability \(p_t\), the Brier score is

\[
BS=\frac1n\sum_{t=1}^n(p_t-y_t)^2;
\quad\Delta BS=BS_{\mathrm{candidate}}-BS_{\mathrm{GBM}}.
\]

Smaller values indicate better historical probability forecasts **for the same event, period and horizon**. A negative \(\Delta BS\) favours the candidate, but does not alone establish statistical significance.

### Original 30-day, 10%-loss evaluation

| Model or benchmark | 2025 Brier, 335 origins | 2026 Brier, 274 origins |
|---|---:|---:|
| Calibration-only historical event frequency | **0.150874** | 0.176230 |
| GBM | 0.151631 | **0.175239** |
| Original Markov | 0.151176 | 0.178221 |
| EWMA | 0.159060 | 0.215885 |
| Adaptive GBM (2025 exploratory) | 0.154912 | 0.218919 |
| Gaussian GARCH (2025 exploratory) | 0.151766 | 0.176664 |

Source: [executed Phase 1 findings](research/PHASE1_FINDINGS.md), [frozen 2026 findings](research/phase3_2026/results/FINDINGS.md) and archived per-origin forecast ledgers. The 2025 30-day windows overlap up to 29 days; the same holds for the 2026 30-day windows. Treating the sample as hundreds of independent forecast experiments is incorrect.

A **paired circular moving-block bootstrap** resamples the per-origin score differences in 30-day blocks and reports approximate uncertainty intervals. The original 2025 analysis uses 5,000 bootstrap resamples and applies a conservative three-threshold familywise adjustment. The 2026 primary comparison uses 3,000 bootstrap resamples and Holm correction for the two newly proposed adaptive models.

**Interpretation:** Markov had a very small descriptive advantage over GBM in 2025, while the calibration-only historical benchmark led for 10% events. GBM led in 2026. Neither period proves a general Markov improvement. For 2026 the adaptive-GBM-minus-GBM Brier difference was +0.043680 (95% interval [-0.005052, +0.102579]); GARCH-minus-GBM was +0.001425 ([-0.001689, +0.005196]). Both include zero. These experiments are retrospective, **not prospective predictions recorded before 2026 happened**.

Additional exploratory horizons of **7, 14, 60 and 90 days** are archived separately with their own eligible origin counts, and the original 30-day evidence is unchanged. Their event frequencies, overlapping-window dependencies and numerical Brier scores should not be interpreted as directly interchangeable with the 30-day question. See [five-horizon validation](research/WEB_V5_HORIZON_VALIDATION.md).

## 9. Verification and numerical stability

| Check | Independent expected property | Evidence |
|---|---|---|
| Input integrity | Exact daily UTC dates, finite positive closes, unique timestamps | Main notebook data asserts |
| GBM terminal loss | Monte Carlo loss probability within sampling uncertainty of analytical normal-CDF result | Notebook §4 and §5.3 |
| GBM VaR/ES | Analytical lognormal values inside Monte Carlo uncertainty limits | Notebook §4 |
| Markov transition matrix | Each entry in [0,1]; rows total 1 | Notebook §3.9 |
| Markov occupancy | Daily simulated occupancy follows \(\pi_0P^d\) | Notebook §4 and §6A |
| Markov identical-regime limit | Risk measures agree with the GBM one-distribution case | Notebook §4.5 |
| EWMA constant variance | \(\lambda=1\) agrees with fixed-variance theory | Notebook §6B |
| Reproducibility | Identical settings and seeds reproduce paths | Notebook and browser automated checks |
| Historical score parity | Stored probabilities/observations recreate archived Brier scores | Scientific verification scripts |
| Browser parity | Executed notebook's original 335 forecasts and scores exactly preserved in the historical dashboard | scripts/verify_notebook.py; scripts/verify_browser.py |
| Numerical load | Five models × 30,000 paths × 90 days tested | GitHub Actions browser workflow |

A finite-step update does not have a PDE-style CFL stability condition here; daily sampling **defines** the discrete-time model. A larger number of paths reduces Monte Carlo sampling error approximately as \(N^{-1/2}\) but does not eliminate **model misspecification** or parameter-estimation uncertainty. See the notebook's independent Monte Carlo error-scaling experiment.

## 10. Concepts applied

| Applied mathematical/computational concept | Where it appears |
|---|---|
| Input modelling and random variate generation | Historical log returns, normal variates and independent random streams |
| Discrete-time Markov chains (DTMC) | Two-state transition matrix, state trajectories and theoretical \(P^d\) occupancy |
| Monte Carlo integration and law of large numbers | Estimation of event probabilities, VaR/ES, repeated seeds and convergence |
| Model verification and limiting cases | GBM closed forms, identical-regime and EWMA constant-variance checks |
| Statistical inference for dependent outcomes | Paired moving-block bootstrap of overlapping historical forecast windows |

## 11. Reproducible evidence and limitations

The [main Colab notebook](notebook/cryptorisk-lab.ipynb) is the canonical implementation of the original GBM/Markov/EWMA study. The separate [2026 extension](research/phase3_2026/) adds Gaussian GARCH and adaptive GBM without overwriting the original results. The [2025 exploratory extension](research/phase4_2025/) and [multi-horizon extension](research/phase5_horizons/) are explicitly post-hoc and reproduce their archived score ledgers from local scientific code.

These models use simplified conditional normal shocks, a small number of regimes, an assumed stationary transition law and a fixed historical calibration period. Real cryptocurrency markets can have fat tails, asymmetric crashes, nonstationarity, exchange-specific risks, spreads and sudden structural breaks. Significant Monte Carlo precision is **not** the same as precise knowledge of future price behavior.

See [REFERENCES.md](REFERENCES.md) for published methods, authoritative data and their respective roles.
