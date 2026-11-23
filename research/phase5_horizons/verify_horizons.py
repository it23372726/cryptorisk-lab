#!/usr/bin/env python3
"""Independent 7/14/30/60/90 day historical research audit.

Runs AFTER generate.py, and reconstructs every stored per-origin loss event,
published Brier score, original H=30 baseline and year/horizon date range.
"""
from __future__ import annotations
import csv
import datetime as dt
import json
import math
import pathlib

ROOT=pathlib.Path(__file__).resolve().parents[2]
rpath=ROOT/"research/phase5_horizons/results"
source=(ROOT/"docs/v5-evidence-horizons.js").read_text()
prefix="window.CRL_HORIZON_EVIDENCE="
assert source.count(prefix)==1
data=json.loads(source.split(prefix)[1].strip().rstrip(";"))
assert data["horizons"]==[7,14,30,60,90]
assert data["models"]==["historical","gbm","markov","ewma","adaptive_gbm","garch"]
assert data["thresholds"]==[10,20,35]
assert 0.02445<data["regimeThreshold"]<0.02446
assert len(data["fields"])==30
raw_original={
  "2025":json.loads((ROOT/"research/phase4_2025/results/metrics_2025_extended.json").read_text())["scores"],
  "2026":json.loads((ROOT/"research/phase3_2026/results/metrics_2026.json").read_text())["scores"]
}
old_sources={
 "2025":ROOT/"research/phase4_2025/results/forecast_ledger_2025_extended.csv",
 "2026":ROOT/"research/phase3_2026/results/forecast_ledger_2026.csv"
}
expected={"2025":{7:358,14:351,30:335,60:305,90:275},
          "2026":{7:297,14:290,30:274,60:244,90:214}}
calculated=json.loads((rpath/"scores_by_year_and_horizon.json").read_text())
for year in ("2025","2026"):
    period=data["years"][year]
    with old_sources[year].open(newline="") as f:
        original=list(csv.DictReader(f))
    assert set(int(v) for v in period)==set(data["horizons"])
    for h in data["horizons"]:
        bundle=period[str(h)]
        n=expected[year][h]
        assert bundle["horizon"]==h and bundle["n"]==n
        scores=bundle["scores"]
        assert scores==calculated[year][str(h)]
        if h==30:
            assert bundle["rows"] is None
            assert scores==raw_original[year]
            assert n==len(original)
            print(f"PASS: {year} 30-day original study preserved byte-for-byte in multi-horizon reference")
            continue
        with (rpath/f"forecasts_{year}_{h}d.csv").open(newline="") as f:
            reader=csv.DictReader(f)
            rows=list(reader)
            columns=reader.fieldnames
        assert columns==data["fields"]
        assert len(rows)==len(bundle["rows"])==n
        assert rows[0]["origin"]==f"{year}-01-01"
        assert rows[-1]["target"]==data["yearEnd"][year]
        for i,(row,record) in enumerate(zip(rows,bundle["rows"])):
            assert len(record)==30
            for k,v in zip(columns,record):
                saved_value=row[k]
                if k in ("origin","target"):assert v==saved_value
                else:assert math.isclose(float(v),float(saved_value),rel_tol=1e-12,abs_tol=1e-12)
            assert (dt.date.fromisoformat(row["target"])-dt.date.fromisoformat(row["origin"])).days==h
            assert int(row["regime"]) in (0,1)
            assert float(row["ewma_nextvar"])>0 and float(row["garch_nextvar_pct2"])>0
            assert float(row["rolling30_sigma"])>0
            assert float(row["btc_origin"])>0 and float(row["btc_target"])>0
            for t in data["thresholds"]:
                assert int(row[f"event_{t}"])==int(
                     1-float(row["btc_target"])/float(row["btc_origin"])>=t/100)
                assert all(0<=float(row[f"{m}_p{t}"])<=1 for m in data["models"])
                assert all(float(row[f"{m}_p10"])>=float(row[f"{m}_p20"])>=
                           float(row[f"{m}_p35"]) for m in data["models"])
        for t in data["thresholds"]:
            outcomes=[float(r[f"event_{t}"]) for r in rows]
            sc=scores[str(t)]
            assert sum(outcomes)==sc["events"]
            assert abs(sc["frequency"]-sum(outcomes)/n)<1e-12
            for m in data["models"]:
                ps=[float(r[f"{m}_p{t}"]) for r in rows]
                mean=sum((p-y)**2 for p,y in zip(ps,outcomes))/n
                assert abs(mean-sc["models"][m]["brier"])<1e-12
                assert abs(sc["models"][m]["mean_probability"]-sum(ps)/n)<1e-12
            for key,result in sc["differences"].items():
                assert result["exploratory"] is True
                assert result["bootstrap_block"]==h
                assert len(result["ci95"])==2
                assert math.isfinite(result["mean"])
                assert result["ci95"][0]<=result["ci95"][1]
        print(f"PASS: {year} H={h}: {n} actual prices/outcomes, all 6 model probabilities and exact Brier parity")
assert (rpath/"FINDINGS.md").stat().st_size>1000
print("PASS: Eight new exploratory evidence sets + two immutable original H=30 evaluations audited")
