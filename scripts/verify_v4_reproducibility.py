#!/usr/bin/env python3
"""Reproducibility audit for 2025 exploratory forecasts.

Compare independently regenerated results with the exact committed evidence.
Exact agreement is required for research design, labels, dates and Monte Carlo
loss-event COUNTs. IEEE floating-point outputs from np.log/erfc/SD may differ
at ~1e-15 between runners, so use strict absolute tolerance for those values.
Restore committed published files after this audit before browser tests.
"""
from __future__ import annotations

import json
import math
import pathlib
import subprocess

ROOT=pathlib.Path(__file__).resolve().parents[1]
FILES=("docs/v4-exploratory-2025-data.json","docs/v4-exploratory-2025-data.js",
       "research/phase4_2025/FINDINGS.md")

def original(path):
    return subprocess.check_output(["git","show","HEAD:"+path],cwd=ROOT,text=True)

saved=json.loads(original(FILES[0]))
regen=json.loads((ROOT/FILES[0]).read_text(encoding="utf-8"))
assert saved["meta"]==regen["meta"],"Frozen historical method or training settings changed"
assert len(saved["rows"])==len(regen["rows"])==335
for i,(a,b) in enumerate(zip(saved["rows"],regen["rows"])):
    assert a["date"]==b["date"],f"Forecast origin date changed at {i}"
    for key in ("rolling_sigma","garch_nextvar_pct2"):
        assert math.isclose(a[key],b[key],abs_tol=1e-10,rel_tol=0),f"Conditional model state changed: {i} {key}"
    for m in ("adaptive_gbm","garch"):
        assert len(a["p"][m])==len(b["p"][m])==3
        for k,(pa,pb) in enumerate(zip(a["p"][m],b["p"][m])):
            if m=="garch":
                assert pa==pb, f"Fixed-seed 20,000-path Monte Carlo count changed: {i}/{k}"
            else:
                assert math.isclose(pa,pb,abs_tol=2e-11,rel_tol=0),f"Analytic Adaptive GBM probability changed {i}/{k}"
assert saved["scores"].keys()==regen["scores"].keys()
for t in ("10","20","35"):
    a=saved["scores"][t];b=regen["scores"][t]
    for key in ("events","n"):
        assert a[key]==b[key],f"Research event count changed {t}%"
    assert math.isclose(a["observed"],b["observed"],abs_tol=1e-15,rel_tol=0)
    assert a["models"].keys()==b["models"].keys()
    for m in ("adaptive_gbm","garch"):
        assert a["models"][m].keys()==b["models"][m].keys()
        for metric in a["models"][m]:
            assert math.isclose(a["models"][m][metric],b["models"][m][metric],abs_tol=1e-10,rel_tol=0),f"{t}% {m} {metric} differs"
    assert a["differences"].keys()==b["differences"].keys()
    for key,diff in a["differences"].items():
        new=b["differences"][key]
        for field in ("block_days","replications","inference"):
            assert diff[field]==new[field]
        assert math.isclose(diff["mean"],new["mean"],abs_tol=1e-10,rel_tol=0)
        assert all(math.isclose(x,y,abs_tol=1e-10,rel_tol=0)
                   for x,y in zip(diff["ci95"],new["ci95"]))

def check_embedded(path,local):
    p=path.split("window.CRL_EXPLORATORY_2025=",1)
    assert len(p)==2 and p[1].strip().endswith(";")
    return json.loads(p[1].strip().rstrip(";"))==local

assert check_embedded(original(FILES[1]),saved)
assert check_embedded((ROOT/FILES[1]).read_text(),regen)
assert original(FILES[2])==(ROOT/FILES[2]).read_text(),"Written scientific interpretation changed"
print("PASS: All 335 origin-date states and 10/20/35 analytic forecasts numerically reproducible")
print("PASS: Every seeded 2025 GARCH Monte Carlo event count reproduced exactly")
print("PASS: Historical 2025 event counts, Brier scores and block-bootstrap intervals unchanged")
print("PASS: Website payload matches research JSON and findings are identical")
