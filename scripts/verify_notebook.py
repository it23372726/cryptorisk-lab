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
report_path.write_text(json.dumps(report, indent=2) + "\n")
