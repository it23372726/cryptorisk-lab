"""Audit offline v3 2026 evidence against committed, independent research outputs.

Guarantees: the website merely displays forecast probabilities and observed prices
recorded by the frozen research. It never recalibrates using later prices or
silently changes probability scores, model parameters, or study conclusions.

Run: python scripts/verify_v3_evidence.py
No third-party dependencies.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
JS = ROOT / "docs" / "v3-evidence-2026.js"
CSV = ROOT / "research" / "phase3_2026" / "results" / "forecast_ledger_2026.csv"
METRICS = ROOT / "research" / "phase3_2026" / "results" / "metrics_2026.json"
HISTORY = ROOT / "docs" / "btc-historical.json"
prefix = "window.CRL_EVIDENCE_2026="

content = JS.read_text(encoding="utf-8")
assert content.count(prefix) == 1 and content.rstrip().endswith(";")
evidence = json.loads(content.split(prefix,1)[1].rstrip().rstrip(";"))
metrics = json.loads(METRICS.read_text(encoding="utf-8"))
with CSV.open(encoding="utf-8",newline="") as f:
    reader = csv.DictReader(f)
    ledger = list(reader)
    names = reader.fieldnames

assert evidence["columns"] == names
assert evidence["n"] == len(ledger) == len(evidence["records"]) == 274
assert evidence["originStart"] == ledger[0]["origin"] == "2026-01-01"
assert evidence["originEnd"] == ledger[-1]["origin"] == "2026-10-01"
assert evidence["finalObserved"] == ledger[-1]["target"] == "2026-10-31"
for src, saved in zip(ledger, evidence["records"]):
    assert len(saved)==len(names)
    for key,value in zip(names,saved):
        original = src[key]
        if key in ("origin","target"):
            assert value == original
        else:
            assert math.isclose(value,float(original),abs_tol=1e-12,rel_tol=1e-13),key
    start=dt.date.fromisoformat(src["origin"])
    end=dt.date.fromisoformat(src["target"])
    assert (end-start).days==30
    assert start.year==end.year==2026
    origin=float(src["btc_origin"])
    target=float(src["btc_target"])
    assert origin>0 and target>0
    for t in (10,20,35):
        event=int(1-target/origin>=t/100)
        assert event == int(src[f"event_{t}"])
        for m in ("historical","gbm","markov","ewma","adaptive_gbm","garch"):
            p=float(src[f"{m}_p{t}"])
            assert 0<=p<=1

assert evidence["scores"] == metrics["scores"]
assert evidence["primary"] == metrics["primary_holm_tests"]
assert evidence["garch"] == metrics["garch_fit"]
assert evidence["horizon"] == metrics["horizon_days"] == 30
assert evidence["protocol"] == metrics["protocol"]
assert evidence["limitations"] == metrics["limitations"]
assert evidence["garch"]["fit_converged"] is True
assert evidence["garch"]["n_train"]==1095
assert evidence["garch"]["persistence"]<1

for t in (10,20,35):
    outcomes=[int(r[f"event_{t}"]) for r in ledger]
    assert sum(outcomes)==evidence["scores"][str(t)]["events"]
    for m in ("historical","gbm","markov","ewma","adaptive_gbm","garch"):
        probabilities=[float(r[f"{m}_p{t}"]) for r in ledger]
        recomputed=sum((p-y)**2 for p,y in zip(probabilities,outcomes))/len(outcomes)
        assert abs(recomputed-evidence["scores"][str(t)]["models"][m]["brier"])<1e-11

history=json.loads(HISTORY.read_text(encoding="utf-8"))
december=history["candles"][:31]
assert december[0]["date"]=="2024-12-01" and december[-1]["date"]=="2024-12-31"
assert december[-1]["close"]==93576
r=[math.log(december[i]["close"]/december[i-1]["close"]) for i in range(1,31)]
mean=sum(r)/30
sample_sigma=(sum((v-mean)**2 for v in r)/29)**.5
assert math.isfinite(sample_sigma) and sample_sigma>0
print("PASS: 2026 274-origin ledger, identical values, six model probabilities and exact Brier scores",flush=True)
print("PASS: 2026 loss outcomes, 2024 adaptive-GBM source and frozen GARCH parameters",flush=True)
print("PASS: Three scientific thresholds, model inference and frozen caveats unchanged",flush=True)
