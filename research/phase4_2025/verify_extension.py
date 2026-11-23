#!/usr/bin/env python3
"""Independent 2025 five-model extension audit against the original notebook.

All 335 original GBM/Markov/EWMA and historical-frequency forecasts must
remain exactly equal to the previously published 2025 notebook export.
"""
from __future__ import annotations
import csv
import json
import pathlib
import math
import datetime as dt

ROOT=pathlib.Path(__file__).resolve().parents[2]
original=json.loads((ROOT/"docs"/"v2-validation-data.json").read_text())
metrics=json.loads((ROOT/"research"/"phase4_2025"/"results"/"metrics_2025_extended.json").read_text())
js=(ROOT/"docs"/"v4-evidence-2025.js").read_text()
prefix="window.CRL_EVIDENCE_2025="
assert prefix in js
web=json.loads(js.split(prefix)[1].rstrip().rstrip(";"))
with (ROOT/"research"/"phase4_2025"/"results"/"forecast_ledger_2025_extended.csv").open(newline="") as f:
    rd=csv.DictReader(f);ledger=list(rd);fields=rd.fieldnames
assert len(ledger)==len(original["rows"])==len(web["records"])==335
assert web["columns"]==fields and metrics["scores"]==web["scores"]
assert metrics["original2025ScoresPreserved"] and web["exploratory"]
assert web["originStart"]=="2025-01-01" and web["originEnd"]=="2025-12-01"
hist=json.loads((ROOT/"docs"/"btc-historical.json").read_text())
closes={r["date"]:r["close"] for r in hist["candles"]}
assert len(closes)==396
for i,(orig,r,encoded) in enumerate(zip(original["rows"],ledger,web["records"])):
    assert r["origin"]==orig["date"]==encoded[0]
    assert r["target"]==orig["end"]==encoded[1]
    assert (dt.date.fromisoformat(r["target"])-dt.date.fromisoformat(r["origin"])).days==30
    assert math.isclose(float(r["btc_origin"]),orig["price"],abs_tol=1e-9)
    assert math.isclose(float(r["btc_target"]),orig["future"],abs_tol=1e-9)
    assert math.isclose(closes[r["origin"]],orig["price"],abs_tol=.001)
    assert math.isclose(closes[r["target"]],orig["future"],abs_tol=.001)
    assert int(r["regime"])==orig["regime"]
    assert math.isclose(float(r["ewma_nextvar"]),orig["variance"],abs_tol=1e-15)
    for field,value in zip(fields,encoded):
        if field in ("origin","target"):assert value==r[field]
        else:assert math.isclose(float(value),float(r[field]),abs_tol=1e-12,rel_tol=1e-13)
    for j,t in enumerate((10,20,35)):
        assert int(r[f"event_{t}"])==orig["events"][j]
        for model in ("gbm","markov","ewma","historical"):
            assert float(r[f"{model}_p{t}"])==orig["p"][model][j]
for t in (10,20,35):
    sc=metrics["scores"][str(t)]
    assert sc["n"]==335
    for m in ("historical","gbm","markov","ewma","adaptive_gbm","garch"):
        ys=[int(r[f"event_{t}"]) for r in ledger]
        ps=[float(r[f"{m}_p{t}"]) for r in ledger]
        bs=sum((p-y)**2 for p,y in zip(ps,ys))/335
        assert abs(bs-sc["models"][m]["brier"])<1e-11,(m,t)
        if m in ("historical","gbm","markov","ewma"):
            assert abs(bs-original["scores"][str(t)]["models"][m]["brier"])<1e-11
assert metrics["garchFit"]==json.loads((ROOT/"research"/"phase3_2026"/"results"/"metrics_2026.json").read_text())["garch_fit"]
assert "exploratory" in metrics["status"]
print("PASS: Original notebook forecasts preserved exactly across all 335 2025 origins and 3 thresholds")
print("PASS: Added Adaptive GBM/GARCH 2025 predictions, exact Brier parity and 2024-only fitted coefficients")
print("PASS: Website supplement, archived CSV and exploratory research scores match row-by-row")
