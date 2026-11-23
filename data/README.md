# Historical data provenance and use

CryptoRisk Lab derives its research inputs from Binance's **public BTCUSDT spot, 1-day OHLCV archives**, measured at daily **UTC** boundaries. The scientific notebook downloads monthly CSV ZIP archives; the website packages derived historical observations and fixed retrospective validation records so it also opens as a standalone local file.

**Official data provider:** [Binance Public Data](https://github.com/binance/binance-public-data). Archive base: https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1d/

## Sources and intervals

| Dataset or derived asset | UTC coverage | Purpose | Source and provenance |
|---|---|---|---|
| Notebook daily spot closes | 2022-01-01 to 2025-12-31 | Fit 2022–2024 models, evaluate 2025 | Official monthly Binance BTCUSDT/1d archives, live download in notebook |
| docs/btc-historical.json | 2024-12 to 2025-12 | Website historical BTC OHLC candles | Derived from official Binance archive; source proof in docs/btc-2025-sources.json |
| docs/v2-validation-data.{js,json} | 2025 daily eligible origin dates | Archived original 335-origin 30-day events and probabilities | Exact export from executed primary research notebook |
| research/phase3_2026/results/forecast_ledger_2026.csv | 2026-01-01 to 2026-10-01 origins | Separate retrospective 30-day evaluation | Archived 2026 prices to 2026-10-31; official-source SHA-256 proof and frozen 2022–2024 fitting |
| research/phase4_2025/results/forecast_ledger_2025_extended.csv | 2025 original 335 origins | Added 2025 adaptive/GARCH exploratory scores | Original notebook forecasts preserved; extra models labelled post-hoc |
| research/phase5_horizons/results/forecasts_*.csv | 2025 and 2026, 7/14/60/90 days | Additional exploratory historical horizons | Official recorded daily closes, prior-only filters, audited exact-H events |

## Validation and timestamp handling

- Price observations are required to be positive, finite, correctly ordered and unique by UTC day.
- The notebook expects **1,461** daily close observations across 2022–2025, including leap day in 2024. The 2022-01-01 daily return is undefined from the restricted first-close sample.
- **Spot archive timestamp units change on 2025-01-01**: milliseconds for the earlier period and microseconds for 2025 onward. Parsing is checked explicitly.
- 2025 records are excluded from the initial 2022–2024 model fitting. The separate 2026 models retain frozen 2022–2024 parameters, while lagged variance/regime states are updated from information known **at each forecast origin**.
- The frozen 2026 source archive URL/hash list is in [archive_sha256_manifest.json](../research/phase3_2026/results/archive_sha256_manifest.json); source provenance and checks are also in [docs/btc-2025-sources.json](../docs/btc-2025-sources.json).
- Completed forecast windows require the **actual terminal close exactly H days later**. There is no future-data interpolation or fabricated 2026 Nov–Dec pricing.

## Rights and attribution

Data are provided by the respective public-data publisher under its applicable terms. **No Creative Commons or MIT licence is asserted for Binance market data** simply because the access endpoint is public. The [repository code licence](../LICENSE) is separate from third-party data rights.

The public source links above were checked on **24 November 2026**. See [REFERENCES.md](../REFERENCES.md) for academic research and model documentation.
