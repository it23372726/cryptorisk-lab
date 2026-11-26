# Scientific figures and browser evidence

These PNG files are extracted from saved outputs in the [canonical notebook](../notebook/cryptorisk-lab.ipynb), source revision `cd1ea40d2243ed220e233fc2d05db595a85a6505`. Cell positions are one-based, including Markdown and the Colab badge. Its 51 executable code cell sources were compared with the verified revision `aebf3eb40da3dccadbb0906a0cbcb18d7c47faf9` and matched exactly. Saved plots are execution evidence, not newly generated forecasts or evidence of a fresh local execution.

| Figure | Notebook cell/output | Meaning |
|---|---|---|
| [historical-prices.png](historical-prices.png) | 21, output 1 | Historical BTC closes |
| [rolling-volatility.png](rolling-volatility.png) | 21, output 3 | Rolling daily volatility |
| [gbm-simulated-paths.png](gbm-simulated-paths.png) | 26, output 1 | GBM sample price paths |
| [markov-simulated-paths.png](markov-simulated-paths.png) | 41, output 1 | Markov sample price paths |
| [markov-regime-paths.png](markov-regime-paths.png) | 42, output 1 | Simulated Markov state paths |
| [monte-carlo-error-scaling.png](monte-carlo-error-scaling.png) | 64, output 2 | X2 independent Monte Carlo convergence |

[Actual dashboard screenshot](demo-screenshot.png) shows the working five-model browser simulation. More notebook plots, browser captures and verification JSON are archived in the [verification workflow artifacts](https://github.com/it23372726/cryptorisk-lab/actions/workflows/verify-cryptorisk-v2.yml). Historical comparisons and confidence intervals are documented in [research](../research/) and [THEORY.md](../THEORY.md).
