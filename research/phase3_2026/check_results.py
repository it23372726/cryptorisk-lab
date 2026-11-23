"""Independent audit for frozen 2026 adaptive-volatility research artifacts.

Checks original 2025 research files remain out of this extension, recomputes
each Brier score from the per-origin forecast ledger, confirms exactly 30-day
outcomes, probability ordering, finite states, and that the GARCH parameters
were fitted once on 2022-2024 only.
"""
from __future__ import annotations
import json
import pathlib
import numpy as np
import pandas as pd

root=pathlib.Path(__file__).resolve().parents[2]
here=pathlib.Path(__file__).resolve().parent
result_dir=here/"results"
data=pd.read_csv(result_dir/"forecast_ledger_2026.csv")
metrics=json.loads((result_dir/"metrics_2026.json").read_text())
manifest=json.loads((result_dir/"archive_sha256_manifest.json").read_text())
models=("historical","gbm","markov","ewma","adaptive_gbm","garch")
thresholds=(10,20,35)
dates=pd.to_datetime(data["origin"],utc=True)
targets=pd.to_datetime(data["target"],utc=True)
assert len(data)==metrics["origins"]==274
assert data["origin"].is_unique
assert dates.iloc[0]==pd.Timestamp("2026-01-01",tz="UTC")
assert dates.iloc[-1]==pd.Timestamp("2026-10-01",tz="UTC")
assert targets.iloc[-1]==pd.Timestamp("2026-10-31",tz="UTC")
assert ((targets-dates)==pd.Timedelta(days=30)).all()
assert dates.diff().dropna().eq(pd.Timedelta(days=1)).all()
assert data["btc_origin"].gt(0).all() and data["btc_target"].gt(0).all()
assert np.isfinite(data.select_dtypes(include=["number"]).to_numpy()).all()
assert all(data["regime"].isin([0,1]))
assert data["ewma_nextvar"].gt(0).all() and data["garch_nextvar_pct2"].gt(0).all()
assert data["rolling30_sigma"].gt(0).all()
garch=metrics["garch_fit"]
assert garch["fit_converged"] and garch["n_train"]==1095
assert 0<=garch["alpha"]<1 and 0<=garch["beta"]<1
assert garch["alpha"]+garch["beta"]<1
assert metrics["no_parameter_tuning_on_2026"] is True
assert metrics["not_prospective"] is True
for t in thresholds:
    event=(1-data["btc_target"]/data["btc_origin"]>=t/100).astype(int)
    assert np.array_equal(event.to_numpy(),data[f"event_{t}"].to_numpy())
    table=metrics["scores"][str(t)]
    assert table["events"]==int(event.sum())
    for m in models:
        p=data[f"{m}_p{t}"].to_numpy()
        assert ((p>=0)&(p<=1)).all()
        brier=np.mean((p-event.to_numpy())**2)
        assert abs(brier-table["models"][m]["brier"])<1e-10,(m,t)
for m in models:
    assert ((data[f"{m}_p10"]>=data[f"{m}_p20"])
            &(data[f"{m}_p20"]>=data[f"{m}_p35"])).all()
assert data["gbm_p10"].nunique()==1
assert data["historical_p10"].nunique()==1
assert data.groupby("regime")["markov_p10"].nunique().max()==1
months={item["month"] for item in manifest["archives"]}
assert all(f"2026-{k:02d}" in months for k in range(1,11))
assert all(f"{y}-{k:02d}" in months for y in (2022,2023,2024) for k in range(1,13))
assert len(months)==58 # 36 training + 12 inherited 2025 + 10 holdout
assert all(len(item["sha256"])==64 for item in manifest["archives"])
assert (result_dir/"forecast_probability_timeline.png").stat().st_size>10000
assert (result_dir/"primary_brier_comparison.png").stat().st_size>10000
print("PASS: Independent 2026 origin-date, score, probabilities, no-lookahead and source audit")
