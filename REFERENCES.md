# Research references

Research sources for the BTC/USDT risk simulations, mathematical methods and historical evaluation. Publication details and DOIs below have been cross-checked against publisher, journal, publisher-hosted metadata or author/institutional copies. The empirical results in this repository are our own computations from the cited historical data; academic sources motivate methods rather than establish our model results.

## Peer-reviewed research and classic texts (IEEE format)

[1] J. D. Hamilton, “A new approach to the economic analysis of nonstationary time series and the business cycle,” *Econometrica*, vol. 57, no. 2, pp. 357–384, Mar. 1989, doi: [10.2307/1912559](https://doi.org/10.2307/1912559).  
**Use:** foundational regime-switching framework; our observed-volatility two-state chain is a simpler model and is not Hamilton's filtered hidden-state estimator.

[2] D. Ardia, K. Bluteau, and M. Rüede, “Regime changes in Bitcoin GARCH volatility dynamics,” *Finance Research Letters*, vol. 29, pp. 266–271, Jun. 2019, doi: [10.1016/j.frl.2018.08.009](https://doi.org/10.1016/j.frl.2018.08.009).  
**Use:** directly relevant evidence and motivation for Bitcoin volatility-regime analysis; it studies MSGARCH, not our rolling-threshold DTMC.

[3] L. Maciel, “Cryptocurrencies value-at-risk and expected shortfall: Do regime-switching volatility models improve forecasting?,” *International Journal of Finance & Economics*, vol. 26, no. 4, pp. 4840–4855, 2021, doi: [10.1002/ijfe.2043](https://doi.org/10.1002/ijfe.2043).  
**Use:** related comparison of cryptocurrency VaR/ES and regime-switching volatility modelling; forecasting horizons and methods differ from this project.

[4] S.-H. Poon and C. W. J. Granger, “Forecasting volatility in financial markets: A review,” *Journal of Economic Literature*, vol. 41, no. 2, pp. 478–539, 2003, doi: [10.1257/jel.41.2.478](https://doi.org/10.1257/jel.41.2.478).  
**Use:** volatility modelling, measurement challenges and forecast evaluation.

[5] R. F. Engle, “Autoregressive conditional heteroscedasticity with estimates of the variance of United Kingdom inflation,” *Econometrica*, vol. 50, no. 4, pp. 987–1007, Jul. 1982, doi: [10.2307/1912773](https://doi.org/10.2307/1912773).  
**Use:** foundational ARCH conditional-variance model.

[6] T. Bollerslev, “Generalized autoregressive conditional heteroskedasticity,” *Journal of Econometrics*, vol. 31, no. 3, pp. 307–327, 1986, doi: [10.1016/0304-4076(86)90063-1](https://doi.org/10.1016/0304-4076(86)90063-1).  
**Use:** GARCH(1,1) variance recursion and model assumptions.

[7] T. Gneiting and A. E. Raftery, “Strictly proper scoring rules, prediction, and estimation,” *Journal of the American Statistical Association*, vol. 102, no. 477, pp. 359–378, 2007, doi: [10.1198/016214506000001437](https://doi.org/10.1198/016214506000001437).  
**Use:** scientific basis for evaluating probabilistic forecasts with proper scoring rules (including the Brier score).

[8] P. Glasserman, *Monte Carlo Methods in Financial Engineering*. New York, NY, USA: Springer, 2003, doi: [10.1007/978-0-387-21617-1](https://doi.org/10.1007/978-0-387-21617-1).  
**Use:** risk simulation, variance and sampling-error concepts.

## Official data and technical documentation

[9] Binance, “Binance Public Data,” GitHub repository, [Online]. Available: [github.com/binance/binance-public-data](https://github.com/binance/binance-public-data). Accessed: Nov. 24, 2026.  
**Use:** authoritative Binance spot BTCUSDT daily kline archive structure; the original downloaded data remain subject to provider terms. Data lineage and archive hashes are recorded under [research/phase3_2026/results](research/phase3_2026/results/).

[10] K. Sheppard, “Forecasting,” *arch* Python documentation, [Online]. Available: [arch.readthedocs.io/en/latest/univariate/forecasting.html](https://arch.readthedocs.io/en/latest/univariate/forecasting.html). Accessed: Nov. 24, 2026.  
**Use:** software documentation for conditional variance forecasting and how GARCH recursion is implemented.

[11] RiskMetrics Group, *RiskMetrics: Technical Document*, 4th ed., J. P. Morgan/Reuters, 1996. [Online]. Available: [MSCI RiskMetrics archive](https://www.msci.com/documents/10199/dbb975aa-5dc2-4441-aa2d-ae34ab5f0945).  
**Use:** background for EWMA volatility filtering and commonly used decay reference values; the final Bitcoin decay is selected by the project's 2024 experiment rather than fixed from an external convention.

## Evidence mapping

| Scientific claim or method | Sources | Repository evidence |
|---|---|---|
| Volatility regimes are relevant modelling candidates | [1], [2], [4] | [THEORY.md](THEORY.md), [Phase 1 findings](research/PHASE1_FINDINGS.md) |
| Normal/lognormal simulation and MC uncertainty | [8] | Main [notebook](notebook/cryptorisk-lab.ipynb), independent analytical tests |
| EWMA recursive conditional variance | [11] | Notebook §6B and [Phase 1 findings](research/PHASE1_FINDINGS.md) |
| Gaussian GARCH conditional variance | [5], [6], [10] | [Frozen 2026 protocol](research/phase3_2026/PRE_REGISTERED_PROTOCOL.md) |
| Brier scoring and comparative interpretation | [7] | Archived forecast ledgers and result-check scripts |
| Actual BTC/USDT historical observations | [9] | Archive SHA-256 manifest, dataset assertions and local browser assets |

**Reproducibility caveat:** The project's empirical rankings are conditional on its own historical data, initial states, calibration decisions and evaluation windows. These publications do **not** validate our specific numerical conclusions. Every DOI is a reference to an external work, not a substitute for executing the notebook.
