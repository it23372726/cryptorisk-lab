# Multi-horizon evaluation: executed exploratory results

**Additional 7, 14, 60 and 90-day forecasts are retrospective exploratory analyses.** All original 2025/2026 30-day scores and probability ledgers were preserved and remain scientifically distinct.

| Year | Horizon | Origins | 10% events | GBM Brier | Markov Brier | EWMA Brier | Adaptive GBM Brier | GARCH Brier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025 | 7 | 358 | 13 | 0.036314 | 0.035842 | 0.036277 | 0.036696 | 0.035587 |
| 2025 | 14 | 351 | 28 | 0.077312 | 0.077174 | 0.077344 | 0.077831 | 0.075989 |
| 2025 | 30 | 335 | 62 | 0.151631 | 0.151176 | 0.159060 | 0.154912 | 0.151766 |
| 2025 | 60 | 305 | 99 | 0.223486 | 0.225412 | 0.257683 | 0.246640 | 0.223941 |
| 2025 | 90 | 275 | 79 | 0.204878 | 0.205838 | 0.241763 | 0.237301 | 0.205043 |
| 2026 | 7 | 297 | 16 | 0.051322 | 0.051853 | 0.055005 | 0.056324 | 0.051341 |
| 2026 | 14 | 290 | 35 | 0.106588 | 0.107444 | 0.118013 | 0.122770 | 0.106821 |
| 2026 | 30 | 274 | 62 | 0.175239 | 0.178221 | 0.215885 | 0.218919 | 0.176664 |
| 2026 | 60 | 244 | 91 | 0.246760 | 0.251992 | 0.313972 | 0.307386 | 0.247845 |
| 2026 | 90 | 214 | 88 | 0.260441 | 0.265365 | 0.329525 | 0.313242 | 0.260693 |

## Interpretation

This is not evidence that the smallest descriptive Brier at a hand-picked horizon guarantees a better model.
Paired bootstrap intervals are descriptive, with overlapping H-day terminal-outcome windows. The 2026 30-day Holm-adjusted primary inference remains unchanged.
Calibration and fitted model parameters use 2022–2024. Observed prices after each origin are never used to estimate the origin forecast; they are used only to score the H-day outcome.
The 2025 new-model forecasts and all added horizon forecasts are explicitly exploratory because earlier 2025 and 2026 outcomes were already inspected.
No 2026 observations later than 31 October 2026 were used.

## Sources

See research/phase5_horizons/EXPLORATORY_PROTOCOL.md, original notebook, research/phase3_2026, research/phase4_2025, and docs/v5-evidence-horizons.js.
