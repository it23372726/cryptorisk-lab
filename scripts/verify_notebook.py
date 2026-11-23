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
  "ewma_initial_variance": float(m9_origin_var)
}, separators=(",", ":")))
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
report["phase1_results"] = phase1_results
calibration_json_line = re.search(r"WEB_CALIBRATION_JSON=(\{[^\n]+\})", text_output)
assert calibration_json_line, "Missing notebook-derived browser calibration state"
web_calibration = json.loads(calibration_json_line.group(1))
assert web_calibration["origin_date"] == "2024-12-31"
assert 0 < web_calibration["ewma_initial_variance"] < 1
report["web_calibration"] = web_calibration
print("PASS: Exact notebook-derived 2024-12-31 EWMA initial variance exported", flush=True)
print("PHASE1_VERIFIED_RESULTS=" + json.dumps(phase1_results, separators=(",", ":")), flush=True)

report_path.write_text(json.dumps(report, indent=2) + "\n")
