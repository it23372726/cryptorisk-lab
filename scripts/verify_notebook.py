"""Execute the CryptoRisk Lab notebook from top to bottom in a clean Python kernel.
The source notebook is never overwritten, and the machine-readable report is saved
only when the notebook reaches its last code cell without exception.
"""
import json
import pathlib
import sys
import time
import traceback
import nbformat
from nbclient import NotebookClient

source = pathlib.Path("notebook/cryptorisk-lab.ipynb")
report_path = pathlib.Path("verification-results.json")
nb = nbformat.read(source, as_version=4)
required_markers = [
    "# M2: Model-selection experiment",
    "# M3: Verify the entire",
    "# M4: Retrospective risk diagnostics",
    "# X2: Independently measured Monte Carlo error scaling",
    "# X5: Explicit 95% paired-seed intervals",
]
cells = ["".join(c.get("source", "")) for c in nb.cells]
for marker in required_markers:
    assert any(marker in content for content in cells), marker
# Add a read-only provenance probe to the in-memory executed copy.
# The committed scientific notebook is unchanged and still contains 97 cells.
last_code_index = max(i for i, cell in enumerate(nb.cells) if cell.cell_type == "code")
nb.cells[last_code_index].source += """
import json as _crl_export_json
print("WEB_CALIBRATION_JSON=" + _crl_export_json.dumps({
  "origin_date": "2024-12-31",
  "origin_price": float(S0),
  "mu": float(mu_cal),
  "sigma": float(sigma_cal),
  "markov_mu": [float(x) for x in regime_mu],
  "markov_sigma": [float(x) for x in regime_sigma],
  "markov_transition": [[float(x) for x in row] for row in transition_matrix],
  "ewma_decay": float(M7_SELECTED_DECAY),
  "ewma_initial_variance": float(m9_origin_var),
  "ewma_variance_by_decay": {
    f"{i/100:.2f}": float(pd.Series(
      ewma_nextday_variances(price_df["log_return"].to_numpy(), mu_cal,
                             i/100, sigma_cal**2),
      index=price_df["date"]
    ).loc[pd.Timestamp("2024-12-31", tz="UTC")])
    for i in range(80, 100)
  }
}, separators=(",", ":")))
"""
# The original code cells already produced each daily 2025 forecast and outcome.
# Export the ACTUAL fitted out-of-sample results from this notebook execution.
# Do not independently refit, resimulate, or replace the original scientific results.
nb.cells[last_code_index].source += """
_web_models = {"gbm": "GBM", "markov": "Original Markov",
               "ewma": "EWMA", "historical": "Historical frequency"}
_web_pcts = (10, 20, 35)
_web_rows = []
for _i, _r in evaluation_windows_df.iterrows():
    _date = _r["date"].strftime("%Y-%m-%d")
    _end = _r["future_date"].strftime("%Y-%m-%d")
    _p = {
        _key: [float(m8_pred[_label][_pct][_i]) for _pct in _web_pcts]
        for _key, _label in _web_models.items()
    }
    _events = [int(_r[f"event_{_pct}"]) for _pct in _web_pcts]
    _web_rows.append({
        "date": _date,
        "end": _end,
        "price": float(_r["close"]),
        "future": float(_r["future_close"]),
        "regime": int(_r["initial_regime"]),
        "variance": float(m8_origin_var[_i]),
        "events": _events,
        "p": _p
    })
_web_scores = {}
for _j, _pct in enumerate(_web_pcts):
    _observed = evaluation_windows_df[f"event_{_pct}"].to_numpy(dtype=float)
    _web_scores[str(_pct)] = {
        "observed": float(_observed.mean()),
        "events": int(_observed.sum()),
        "models": {
            _key: {
                "mean": float(np.mean(m8_pred[_label][_pct])),
                "brier": float(np.mean((m8_pred[_label][_pct]-_observed)**2))
            }
            for _key, _label in _web_models.items()
        }
    }
_web_bootstraps = [
    {"threshold": _rec["Threshold"],
     "compared": _rec["Compared"], "reference": _rec["Reference"],
     "difference": float(_rec["Brier difference"]),
     "low": float(_rec["95% lower"]), "high": float(_rec["95% upper"])}
    for _rec in m8_bootstrap.to_dict(orient="records")
]
_web_export = {
    "meta": {
        "dataset": "Binance spot BTC/USDT daily UTC",
        "originFirst": "2025-01-01",
        "originLast": "2025-12-01",
        "evaluation": "2025 retrospective (selected Markov/EWMA comparisons exploratory)",
        "horizon": 30, "origins": 335, "thresholds": list(_web_pcts),
        "modelOrder": ["gbm", "markov", "ewma", "historical"],
        "calibration": "2022-2024 frozen original model parameters",
        "markovPathsPerState": int(OOS_MC_PATHS),
        "ewmaPathsPerOrigin": int(M8_EWMA_PATHS),
        "source": "Executed notebook/cryptorisk-lab.ipynb, original evaluations"
    },
    "rows": _web_rows,
    "scores": _web_scores,
    "bootstrap": _web_bootstraps
}
assert len(_web_rows)==335
assert _web_rows[0]["date"]=="2025-01-01"
assert _web_rows[-1]["date"]=="2025-12-01"
assert [_web_scores[str(p)]["events"] for p in _web_pcts]==[62,8,0]
for _row in _web_rows:
    assert _row["price"]>0 and _row["future"]>0 and _row["variance"]>0
    assert _row["events"]==[
        int(1-_row["future"]/_row["price"]>=p/100) for p in _web_pcts
    ]
    for _model in _web_models:
        assert len(_row["p"][_model])==3
        assert all(0<=x<=1 for x in _row["p"][_model])
        assert (_row["p"][_model][0]>=_row["p"][_model][1]>=_row["p"][_model][2])
for _rec in m8_results.to_dict(orient="records"):
    if _rec["Model"] not in _web_models.values():
        continue  # Exploratory selected-Markov candidate is NOT a primary model.
    _key = next(k for k,v in _web_models.items() if v==_rec["Model"])
    _pct = int(_rec["Threshold"].strip(">=%"))
    assert abs(_web_scores[str(_pct)]["models"][_key]["brier"]-_rec["Brier"])<1e-12
print("WEB_BACKTEST_JSON=" + _crl_export_json.dumps(
    _web_export, separators=(",", ":"), allow_nan=False
))
"""
print("Notebook source:", source, "cells", len(nb.cells), flush=True)
t0 = time.monotonic()
try:
    client = NotebookClient(nb, timeout=1800, kernel_name="python3",
                            allow_errors=False, resources={"metadata": {"path": "."}})
    executed = client.execute()
except Exception:
    traceback.print_exc()
    sys.exit(1)
elapsed = time.monotonic() - t0
assert all(
    not any(output.get("output_type") == "error" for output in c.get("outputs", []))
    for c in executed.cells
)
text_output = "\n".join(
    str(output.get("text", ""))
    for c in executed.cells
    for output in c.get("outputs", [])
)
for item in [
    "PASS: Original 14-day calibration reproduced",
    "PASS: Day-by-day occupancy matches Markov",
    "PASS: Retrospective diagnostics computed",
    "PASS: Regime classification audit and 250 shuffled controls completed",
    "PASS: 12 alternative regime definitions evaluated without 2025 model selection",
    "PASS: EWMA candidate selection completed using 2024 validation only",
    "PASS: Three-model 2025 validation, historical benchmark and dependence-aware uncertainty completed",
    "PASS: Terminal risk, daily-close touches, max drawdown and exploratory observed-path checks completed",
    "PASS: Independent N^(-1/2) Monte Carlo error-scaling experiment completed",
    "PASS: X5 paired sensitivity confidence intervals completed",
]:
    assert item in text_output, f"Missing expected verification: {item}"
print("PASS: Full notebook executed without errors", flush=True)
print(f"Execution time: {elapsed:.1f}s", flush=True)
for line in text_output.splitlines():
    if "PASS:" in line or "Validation-selected window:" in line:
        print(line[:240])
report = {
    "notebook": str(source), "executed_cells": len(executed.cells),
    "execution_seconds": round(elapsed, 2),
    "result": "PASS",
    "verified_new_sections": required_markers,
}

# Preserve the actual model-selection and forecast scores in the artifact, not
# merely assertion statuses. This evidence is produced by executed notebook cells.
import re
phase1_json_line = re.search(r"PHASE1_RESULT_JSON=(\{[^\n]+\})", text_output)
assert phase1_json_line, "Missing machine-readable Phase 1 results"
phase1_results = json.loads(phase1_json_line.group(1))
assert len(phase1_results["candidate_markov_2024_ranking"]) == 12
assert len(phase1_results["ewma_2024_ranking"]) == 4
assert len(phase1_results["retrospective_2025_comparison"]) == 15
# Save measured extension statistics in the public verification artifact.
x2_line = next((line.split("X2_ERROR_SCALING_JSON=", 1)[1] for line in text_output.splitlines()
                if "X2_ERROR_SCALING_JSON=" in line), None)
assert x2_line, "Missing measured X2 Monte Carlo error-scaling evidence"
x2_evidence = json.loads(x2_line)
assert len(x2_evidence["rows"]) == 4
assert x2_evidence["repeats_per_n"] == 120
assert -0.85 < x2_evidence["observed_slope"] < -0.15
report["x2_error_scaling"] = x2_evidence
x5_line = next((line.split("X5_SENSITIVITY_CI_JSON=", 1)[1] for line in text_output.splitlines()
                if "X5_SENSITIVITY_CI_JSON=" in line), None)
assert x5_line, "Missing measured X5 sensitivity confidence intervals"
x5_evidence = json.loads(x5_line)
assert len(x5_evidence) == 14
assert all(row["95% lower"] <= row["Effect"] <= row["95% upper"] for row in x5_evidence)
report["x5_sensitivity_confidence_intervals"] = x5_evidence
print("PASS: Machine-readable X2 scaling and X5 uncertainty evidence exported", flush=True)
report["phase1_results"] = phase1_results
calibration_json_line = re.search(r"WEB_CALIBRATION_JSON=(\{[^\n]+\})", text_output)
assert calibration_json_line, "Missing notebook-derived browser calibration state"
web_calibration = json.loads(calibration_json_line.group(1))
assert web_calibration["origin_date"] == "2024-12-31"
assert 0 < web_calibration["ewma_initial_variance"] < 1
report["web_calibration"] = web_calibration
backtest_match = re.search(r"WEB_BACKTEST_JSON=(\{[^\n]+\})", text_output)
assert backtest_match, "Missing executed notebook per-origin forecasts"
backtest = json.loads(backtest_match.group(1))
assert backtest["meta"]["origins"] == 335
assert len(backtest["rows"]) == 335
assert backtest["meta"]["thresholds"] == [10, 20, 35]
assert [backtest["scores"][str(t)]["events"] for t in (10,20,35)] == [62,8,0]
from pathlib import Path
target = Path("docs/v2-validation-data.js")
target.parent.mkdir(exist_ok=True, parents=True)
target.write_text(
    "/* Frozen 2025 30-day historical predictions and actual outcomes, exported "
    "from the executed 97-cell notebook. 335 overlapping windows. */\n"
    "window.CRL_VALIDATION = " + json.dumps(backtest, separators=(",", ":"), allow_nan=False) + ";\n",
    encoding="utf-8"
)
Path("docs/v2-validation-data.json").write_text(
    json.dumps(backtest, indent=2, allow_nan=False) + "\n", encoding="utf-8"
)
report["historical_validation_export"] = {
    "rows": len(backtest["rows"]), "thresholds": [10,20,35],
    "brier_scores": backtest["scores"],
    "paths": ["docs/v2-validation-data.js", "docs/v2-validation-data.json"]
}
print("PASS: Exported all 335 frozen per-origin forecasts, outcomes, EWMA states and Brier scores", flush=True)
print("PASS: Exact notebook-derived 2024-12-31 EWMA initial variance exported", flush=True)
print("PHASE1_VERIFIED_RESULTS=" + json.dumps(phase1_results, separators=(",", ":")), flush=True)

report_path.write_text(json.dumps(report, indent=2) + "\n")
