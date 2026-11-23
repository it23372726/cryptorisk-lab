#!/usr/bin/env python3
"""Independent stdlib audit: 2025 exploratory website data vs original evidence.

The original 335-row notebook records MUST NOT be modified. New 2025 model
results must match all real prices, past-only conditional variance states,
analytic rolling-GBM forecasts, and frozen 2026 GARCH fit parameters.
"""
from __future__ import annotations
import datetime as dt
import json
import math
from pathlib import Path
from statistics import stdev

root=Path(__file__).resolve().parents[1]
original=json.loads((root/"docs/v2-validation-data.json").read_text())
candles=json.loads((root/"docs/btc-historical.json").read_text())["candles"]
extension=json.loads((root/"docs/v4-exploratory-2025-data.json").read_text())
frozen=json.loads((root/"research/phase3_2026/results/metrics_2026.json").read_text())["garch_fit"]
js=(root/"docs/v4-exploratory-2025-data.js").read_text()
assert js.count("window.CRL_EXPLORATORY_2025=")==1
browser=json.loads(js.split("window.CRL_EXPLORATORY_2025=")[1].strip().rstrip(";"))
assert browser==extension
assert len(candles)==396 and len(original["rows"])==335
assert len(extension["rows"])==335
assert extension["meta"]["not_independent_holdout"] is True
assert extension["meta"]["not_prospective"] is True
assert extension["meta"]["models"]==["adaptive_gbm","garch"]
assert extension["meta"]["garch_fit"]==frozen
assert extension["meta"]["rolling_window"]==30
assert extension["meta"]["mc_paths_per_date"]==20000
assert extension["meta"]["thresholds"]==[10,20,35]
assert original["meta"]["modelOrder"]==["gbm","markov","ewma","historical"]
assert "2025 outcomes examined" in extension["meta"]["status"]

bydate={c["date"]:i for i,c in enumerate(candles)}
closes=[float(c["close"]) for c in candles]
returns=[math.log(closes[i]/closes[i-1]) for i in range(1,396)]
mu=0.0006149477738712015
h=frozen["fit_next_variance_2025_01_01_pct2"]
origin_h={}
for index in range(31,396):
    observed=returns[index-1]
    ep=100*(observed-mu)
    h=frozen["omega_pct2"]+frozen["alpha"]*ep**2+frozen["beta"]*h
    origin_h[index]=h

thresholds=[10,20,35]
for row,addition in zip(original["rows"],extension["rows"]):
    assert row["date"]==addition["date"]
    assert row["end"]==(dt.date.fromisoformat(row["date"])+dt.timedelta(days=30)).isoformat()
    index=bydate[row["date"]]
    assert closes[index]==row["price"]
    assert closes[bydate[row["end"]]]==row["future"]
    assert row["events"]==[int(1-row["future"]/row["price"]>=t/100) for t in thresholds]
    assert abs(addition["garch_nextvar_pct2"]-origin_h[index])<1e-10
    sigma=stdev(returns[index-30:index])
    assert abs(sigma-addition["rolling_sigma"])<1e-12
    for j,t in enumerate(thresholds):
        expected=math.erfc(-(math.log1p(-t/100)-mu*30)/(sigma*math.sqrt(60)))/2
        assert abs(expected-addition["p"]["adaptive_gbm"][j])<1e-12
        count=addition["p"]["garch"][j]*20000
        assert abs(round(count)-count)<1e-7
    for name in ("adaptive_gbm","garch"):
        arr=addition["p"][name]
        assert 0<=arr[2]<=arr[1]<=arr[0]<=1

for t in thresholds:
    idx=thresholds.index(t)
    observed=[r["events"][idx] for r in original["rows"]]
    assert sum(observed)==[62,8,0][idx]
    assert extension["scores"][str(t)]["events"]==sum(observed)
    for m in ("adaptive_gbm","garch"):
        probabilities=[r["p"][m][idx] for r in extension["rows"]]
        brier=sum((p-y)**2 for p,y in zip(probabilities,observed))/335
        mean=sum(probabilities)/335
        saved=extension["scores"][str(t)]["models"][m]
        assert math.isclose(brier,saved["brier"],abs_tol=1e-11,rel_tol=0)
        assert math.isclose(mean,saved["mean"],abs_tol=1e-11,rel_tol=0)
    for m in ("gbm","markov","ewma","historical"):
        p=[r["p"][m][idx] for r in original["rows"]]
        brier=sum((x-y)**2 for x,y in zip(p,observed))/335
        assert math.isclose(brier,original["scores"][str(t)]["models"][m]["brier"],abs_tol=1e-11,rel_tol=0)
report=(root/"research/phase4_2025/FINDINGS.md").read_text()
assert "post-hoc/exploratory" in report
assert "2026 holdout" in report
print("PASS: Original 2025 notebook probabilities and outcome dates remain unchanged")
print("PASS: 335 origin-specific new forecasts use prior-only rolling sigma and frozen causal GARCH states")
print("PASS: Exact 2025 source ledger, GARCH 20k path counts and all six models' 10/20/35 Brier scores")
print("PASS: Website JS payload and post-hoc research caveats match audited JSON")
