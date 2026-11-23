# CryptoRisk Lab v2: Website implementation and scientific parity

Branch: website-v2-animated-lab-2026-11-23
Review: Draft PR #1. This is a website redesign, not a modification to the approved research question.

## User experience

The new static site has a responsive scientific research terminal, bundled Binance daily BTC/USDT OHLC candles (1 Dec 2024 through 31 Dec 2025; 396 daily observations), volume bars, crosshair, chart zoom/pan, observed-vs-projected boundary and optional real-outcome reveal. The simulation starts from the 31 Dec 2024 close of 93,576 USDT.

Users can run independent seeded GBM, original two-state Markov and EWMA Monte Carlo paths. Animation progressively reveals selected individual closing-price trajectories and 5th–95th percentile bands. All summary statistics are computed using the FULL path ensemble, not the few drawn paths. Users can pause, replay, change speed, scrub day by day and click a trajectory to inspect its simulated value, drawdown, threshold breach and (for Markov) sampled state.

The comparison reports fixed 10%, 20%, 35% and custom terminal loss probabilities, VaR95, ES95, daily-close touches, maximum drawdown and approximate 95% Monte Carlo probability intervals. The historical 2025 Brier-score table is frozen and is not altered by scenario controls.

## Numeric provenance

The original GBM, Markov and EWMA parameters are copied from the executed 2022–2024 research notebook, rather than estimated from the 396 chart candles. The verification runner executes the original notebook in memory, appends a read-only provenance export to the final executable cell, and writes those values to the CI report without editing the notebook.

Evidence: https://github.com/it23372726/cryptorisk-lab/actions/runs/45210897502

Original GBM mean = 0.0006149477738712015 and sigma = 0.028459921644738977.
Original Markov means = [0.0011709082452031764, 0.0002649261708609547]; sigma = [0.02453708413230616, 0.032033470949311985]. Transition P(Calm|Calm) = 499/540; P(Calm|Volatile) = 41/541.
Selected EWMA decay = 0.90; origin variance = 0.0004616494175752784. For every allowed decay from 0.80 to 0.99 in steps of .01, the executed notebook exports the exact 2024-12-31 next-day initial variance into the website calibration object.

The JS random streams are independent from NumPy's streams, so path-by-path identity is not expected. Model probabilities should instead agree within Monte Carlo error. No actual future observed 2025 returns feed simulated variance recursions.

## Historical conclusions

The small 2025 scoring advantage of the original Markov model over GBM is NOT conclusive evidence of broad superiority. The EWMA benchmark was not consistently better for terminal-loss Brier scores. The 21-day 75th-percentile Markov alternative remains exploratory. Overlapping 30-day evaluation windows cannot be treated as independent samples. The rolling-volatility regime classification's persistence is partly mechanical.

See: https://github.com/it23372726/cryptorisk-lab/blob/main/research/PHASE1_FINDINGS.md

## Verification

- scripts/verify_notebook.py: executes all original scientific notebook cells and exports exact browser calibration.
- scripts/verify_browser.py: Chromium GUI test of all three models, replay, path selection, seed reproducibility, numerical self-checks, fixed validation, local file:// loading, mobile layout and JS errors.
- .github/workflows/verify-cryptorisk-v2.yml: runs notebook and Chromium checks and uploads screenshots plus a standalone site preview.
- Independent 30,000-path simulation smoke test passed structural checks, VaR/ES ordering and finite model probability bands.

## Limits and next checks

The interactive chart bundles all 365 observed BTC/USDT daily candles from 2025 plus 31 historical candles from December 2024. Users can toggle Full 2025 view or Fit forecast, and the simulated model trajectories stop at the chosen 7–90-day horizon. The post-origin historical candles are NEVER used in the on-page model calibration, simulation, or the original notebook-origin variance. Simulated model outputs are daily closing prices, so forecasts are drawn as paths and percentile regions, never invented future OHLC candles. Final review should still cover accessibility, motion preferences, larger screen widths and performance with high path counts.

Historical model calibration is not a current-market forecast. The research site does not provide trading advice.

## Scholarly and data references

Binance public spot OHLC data: https://github.com/binance/binance-public-data
Hamilton (1989): https://doi.org/10.2307/1912559
Ardia, Bluteau and Rüede (2019): https://doi.org/10.1016/j.frl.2018.08.009
Poon and Granger (2003): https://doi.org/10.1257/jel.41.2.478
Glasserman (2003): https://doi.org/10.1007/978-0-387-21617-1
RiskMetrics EWMA: https://www.msci.com/documents/10199/dbb975aa-5dc2-4441-aa2d-ae34ab5f0945

## Full-year observed 2025 data provenance (visual-only extension)

The extended local chart data comes directly from the Binance public **spot BTCUSDT 1d monthly OHLCV CSV archives** for 2025-01 through 2025-12, retrieved and authenticated by the reproducible script `scripts/extend_btc_history_2025.py`. Binance changed spot archive timestamp precision to **microseconds** from 2025-01-01; the parser respects that change. The script checks each full month, verifies all 365 consecutive daily dates, checks old January OHLC overlap with the initial dataset, and preserves the 2024-12-31 close of 93,576 USDT.

Every archive URL, SHA-256 and daily count is recorded in `docs/btc-2025-sources.json`. The resulting `docs/btc-historical.json` and `docs/v2-history.js` are bundled for offline/static operation. No external API requests occur when viewing the website. The full-year chart is observational context only; it does not convert the 30/90-day simulations into 365-day forecasts or alter the retrospective 2025 Brier calculations.

Source specification: https://github.com/binance/binance-public-data

