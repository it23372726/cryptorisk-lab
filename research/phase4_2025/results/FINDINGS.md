# Five-model 2025 extension · exploratory, post-hoc

**This is NOT an independent new blind 2025 evaluation.** The original three-model notebook predictions and historical baseline were preserved exactly. Added Adaptive GBM/GARCH comparisons were specified after seeing the 2025 results and the separate 2026 research.

**Forecast origins:** 335 dates, 2025-01-01 through 2025-12-01. Same real BTC/USDT closes, same 30-day terminal loss events as original notebook.

| Model | ≥10% Brier | ≥20% Brier | ≥35% Brier |
|---|---:|---:|---:|
| Historical | 0.150874 | 0.024360 | 0.000022 |
| Markov | 0.151176 | 0.024159 | 0.000004 |
| Gbm | 0.151631 | 0.024658 | 0.000004 |
| Garch | 0.151766 | 0.024683 | 0.000013 |
| Adaptive Gbm | 0.154912 | 0.024071 | 0.000010 |
| Ewma | 0.159060 | 0.024437 | 0.000035 |

## Interpretation

Lower descriptive Brier is better, but candidate selection after viewing 2025 makes superiority claims from 2025 exploratory. The separate 2026 evaluation retains its original frozen protocol and findings, including its conclusion that new models did not establish statistical improvement over GBM.

The data files contain every origin's input state, archived probability, observed price and actual loss event. Both added models use no 2025 prices after the forecast origin to initialize a forecast.

## Reproduction

Run: \`python research/phase4_2025/run_exploratory.py\` in the pinned scientific environment from \`research/phase3_2026/requirements-lock.txt\`.
Audit: \`python research/phase4_2025/verify_extension.py\`.

Methods: \`research/phase4_2025/EXPLORATORY_PROTOCOL.md\`; original 2025 notebook: \`notebook/cryptorisk-lab.ipynb\`.
