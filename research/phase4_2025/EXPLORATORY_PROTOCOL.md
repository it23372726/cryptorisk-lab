# 2025 five-model historical extension: fixed, retrospective and explicitly exploratory

**Research integrity:** This extension was designed on 2026-11-24, **after** the 2025 results and the separate 2026 comparison had been examined. It is *not* a new blind out-of-sample or preregistered 2025 experiment. No 2025 extension score may be reported as confirmatory statistical evidence of model superiority.

## Fixed choices

- Retain the original, unchanged 335 origins from the executed 97-cell notebook, 2025-01-01 through 2025-12-01, and original binary outcomes after exactly 30 calendar days.
- Preserve the notebook's original GBM, two-state Markov, EWMA and 2022–2024 historical-frequency probabilities **exactly, row-by-row**. No recomputation or replacement.
- For the two additional models, apply exactly the previously documented **2026 research model specifications**, without parameter search:
  - Adaptive GBM: same frozen 2022–2024 mean, analytical Gaussian 30-day log-return tail using 30 **observed** daily log returns through the origin (sample SD, ddof=1), held constant over the projection horizon.
  - Gaussian GARCH(1,1): frozen 2022–2024 fit `omega=1.7429241072532673`, `alpha=0.1689729613867537`, `beta=0.6255015699659665`, log-return residuals expressed in **percentage units**, with the verified initial **next-day 2025-01-01 variance 5.547208876802669 percent²** from the separately executed 2026 study. Update this variance only using returns observed through the forecast date; for future 30 days update exclusively with simulated Gaussian innovations. Do **not** refit GARCH on 2025.
- GARCH tail probabilities: 20,000 independently seeded paths per origin; seeds determined by year, index and fixed model salt, never chosen to improve scores.
- The origin/target prices, outcomes, model states and rolling volatility are verified against the original daily BTCUSDT UTC candles. No 2025 or 2026 future prices can initialize a forecast.
- Compare six sources on exactly the same 335 origins and thresholds **≥10%, ≥20%, ≥35%**. Report Brier scores, average forecast probabilities, and **descriptive** 30-day paired circular moving-block uncertainty bands. They are not statistical proof, particularly for candidates designed after observing the 2025 study.
- Keep independent frozen 2026 274-origin research and primary Holm-adjusted inference completely untouched. Across-year rankings are descriptive, not pooled statistical claims.

## Sources and provenance

- Original approved 2025 notebook export: `docs/v2-validation-data.json`.
- Verified UTC BTCUSDT 2024-12-01 through 2025-12-31 candles: `docs/btc-historical.json`, Binance official spot monthly daily data.
- Frozen GARCH coefficients and 2025-01-01 next-day conditional variance: `research/phase3_2026/results/metrics_2026.json`.
- Frozen 2026 model specification: `research/phase3_2026/PRE_REGISTERED_PROTOCOL.md`.
- Engle (1982), DOI https://doi.org/10.2307/1912773; Bollerslev (1986), DOI https://doi.org/10.1016/0304-4076(86)90063-1.
- This extension was coded with ChatGPT assistance. All scores must be reconstructed from independent committed results, not guessed or polished for presentation.
