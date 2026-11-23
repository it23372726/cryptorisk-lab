#!/usr/bin/env python3
"""Frozen 7/14/30/60/90-day retrospective extension. No 30d research replacement.

Science/limitations: research/phase5_horizons/EXPLORATORY_PROTOCOL.md
Outputs a compact offline static evidence bundle and auditable per-year/H CSV
ledgers with all six model probabilities on common, complete-outcome origin dates.
"""
from __future__ import annotations
import csv
import datetime as dt
import hashlib
import json
import math
import pathlib
import sys
import time
import numpy as np
from scipy.stats import norm

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.phase3_2026.run_research import read_official_month

OUT=ROOT/"research/phase5_horizons/results"
HORIZONS=(7,14,30,60,90)
THRESHOLDS=(10,20,35)
MODELS=("historical","gbm","markov","ewma","adaptive_gbm","garch")
MU=0.0006149477738712015
SIGMA=0.028459921644738977
LAM=.90
MARKOV_MUS=np.array([0.0011709082452031764,0.0002649261708609547])
MARKOV_SIGMAS=np.array([0.02453708413230616,0.032033470949311985])
NEXT_CALM=np.array([499/540,41/541])
GARCH_FIT=(1.7429241072532673,.1689729613867537,.6255015699659665)
GARCH_START=5.547208876802669
EWMA_START=.0004616494175752784
PATHS=20000
MARKOV_PATHS=200000
SEED=20261124
REPS=3000
FIELDS=("origin","target","btc_origin","btc_target","realized_return","regime","rolling30_sigma",
        "ewma_nextvar","garch_nextvar_pct2") + tuple(
         f for t in THRESHOLDS for f in (f"event_{t}",)+tuple(f"{m}_p{t}" for m in MODELS))


def read_csv(path):
    with path.open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    assert rows and set(FIELDS)==set(rows[0])
    return rows


def existing_and_price_sources():
    """Source retained H=30 data, plus authentic daily observed closes for all horizons."""
    originals={
      2025:read_csv(ROOT/"research/phase4_2025/results/forecast_ledger_2025_extended.csv"),
      2026:read_csv(ROOT/"research/phase3_2026/results/forecast_ledger_2026.csv")
    }
    old_scores={
      2025:json.loads((ROOT/"research/phase4_2025/results/metrics_2025_extended.json").read_text())["scores"],
      2026:json.loads((ROOT/"research/phase3_2026/results/metrics_2026.json").read_text())["scores"]
    }
    history=json.loads((ROOT/"docs/btc-historical.json").read_text())["candles"]
    assert len(history)==396
    assert history[0]["date"]=="2024-12-01" and history[30]["date"]=="2024-12-31"
    assert history[-1]["date"]=="2025-12-31" and history[30]["close"]==93576
    price={c["date"]:float(c["close"]) for c in history}
    for row in originals[2026]:
        for date,key in ((row["origin"],"btc_origin"),(row["target"],"btc_target")):
            value=float(row[key])
            if date in price:
                assert abs(price[date]-value)<.011,date
            price[date]=value
    assert len(price)==700  # 31 Dec-2024 + 365 days in 2025 + 304 in 2026
    assert set(price)>=set(r["origin"] for r in originals[2025])
    assert set(price)>=set(r["origin"] for r in originals[2026])
    assert price["2026-10-31"]>0
    for year,expected in ((2025,335),(2026,274)):
        assert len(originals[year])==expected
    return originals,old_scores,price


def retrieve_calibration():
    """Compute exact original regime median and calibration-only H-event baselines."""
    original=json.loads((ROOT/"research/phase3_2026/results/archive_sha256_manifest.json").read_text())
    pinned={r["month"]:r for r in original["archives"]}
    closes=[]
    for year in (2022,2023,2024):
        for month in range(1,13):
            candles,source=read_official_month(year,month)
            key=source["month"]
            if source["sha256"]!=pinned[key]["sha256"]:
                raise AssertionError("Official training archive changed: "+key)
            closes.extend(float(c["close"]) for c in candles)
    assert len(closes)==1096
    rets=np.log(np.array(closes[1:])/np.array(closes[:-1]))
    assert np.isclose(rets.mean(),MU,atol=1e-11,rtol=0)
    assert np.isclose(rets.std(ddof=1),SIGMA,atol=1e-11,rtol=0)
    v14=np.array([np.std(rets[i-13:i+1],ddof=1) for i in range(13,len(rets))])
    threshold=float(np.median(v14))
    assert .02445<threshold<.02446
    frequencies={}
    cuts=np.log1p(-np.array(THRESHOLDS)/100)
    lp=np.log(np.array(closes))
    for horizon in HORIZONS:
        tails=lp[horizon:]-lp[:-horizon]
        assert len(tails)==1096-horizon
        frequencies[horizon]=(tails[:,None]<=cuts).mean(axis=0)
    return threshold,frequencies


def markov_horizon_probabilities():
    """Frozen training fit, one common 90-day simulated path per starting regime."""
    cuts=np.log1p(-np.array(THRESHOLDS)/100)
    result={}
    for initial in (0,1):
        rng=np.random.default_rng(20251121+initial)
        state=np.full(MARKOV_PATHS,initial,dtype=np.int8)
        total=np.zeros(MARKOV_PATHS,dtype=float)
        result[initial]={}
        for day in range(1,91):
            total+=MARKOV_MUS[state]+MARKOV_SIGMAS[state]*rng.standard_normal(MARKOV_PATHS)
            uniforms=rng.random(MARKOV_PATHS)
            state=np.where(uniforms<NEXT_CALM[state],0,1).astype(np.int8)
            if day in HORIZONS:
                result[initial][day]=(total[:,None]<=cuts).mean(axis=0)
        print("PASS: Frozen two-regime Markov simulated through 90 days, state "+str(initial),flush=True)
    return result


def model_shocks(var_ewma,var_garch,days,seed_e,seed_g,omega,alpha,beta):
    """Per-origin independent EWMA and GARCH paths, sharing shocks across horizons."""
    e_rng=np.random.default_rng(seed_e)
    g_rng=np.random.default_rng(seed_g)
    ewma=np.full(PATHS,float(var_ewma))
    garch=np.full(PATHS,float(var_garch))
    total_e=np.zeros(PATHS)
    total_g=np.zeros(PATHS)
    cuts=np.log1p(-np.array(THRESHOLDS)/100)
    outs={}
    for day in range(1,days+1):
        e_shock=np.sqrt(ewma)*e_rng.standard_normal(PATHS)
        total_e+=MU+e_shock
        ewma=LAM*ewma+(1-LAM)*e_shock**2
        g_shock=np.sqrt(garch)*g_rng.standard_normal(PATHS)
        total_g+=MU+g_shock/100
        garch=omega+alpha*g_shock**2+beta*garch
        if day in HORIZONS and day!=30:
            outs[day]={"ewma":(total_e[:,None]<=cuts).mean(axis=0),
                       "garch":(total_g[:,None]<=cuts).mean(axis=0)}
    assert np.isfinite(total_g).all() and np.isfinite(total_e).all()
    return outs


def ci_differences(rows,year,h):
    """Paired circular H-day block bootstrap intervals, strictly descriptive."""
    result={}
    rng=np.random.default_rng(SEED+year*100+h*11)
    n=len(rows)
    b=min(h,n)
    starts=rng.integers(0,n,size=(REPS,int(np.ceil(n/b))))
    indices=((starts[:,:,None]+np.arange(b)[None,None,:])%n).reshape(REPS,-1)[:,:n]
    for t in THRESHOLDS:
        actual=np.array([row[f"event_{t}"] for row in rows],dtype=float)
        loss={m:(np.array([row[f"{m}_p{t}"] for row in rows])-actual)**2 for m in MODELS}
        differences={}
        for m in ("markov","ewma","adaptive_gbm","garch"):
            for base in ("gbm","historical"):
                key=m+"_minus_"+base
                x=loss[m]-loss[base]
                low,high=np.quantile(x[indices].mean(axis=1),[.025,.975])
                differences[key]={"mean":float(x.mean()),"ci95":[float(low),float(high)],
                                  "bootstrap_block":b,"exploratory":True}
        result[str(t)]=differences
    return result


def validate_original_states(price,originals,threshold):
    """Catch any discrepancy with the notebook's exact calibrated regime definition."""
    dates=sorted(price)
    assert dates[0]=="2024-12-01" and dates[-1]=="2026-10-31"
    assert all((dt.date.fromisoformat(b)-dt.date.fromisoformat(a)).days==1 for a,b in zip(dates,dates[1:]))
    returns={date:float(np.log(price[date]/price[dates[i-1]])) for i,date in enumerate(dates) if i>0}
    states={}
    for i,date in enumerate(dates):
        if i>=14:
            v=np.array([returns[dates[j]] for j in range(i-13,i+1)])
            states[date]=int(np.std(v,ddof=1)>=threshold)
    for year,rows in originals.items():
        for row in rows:
            if states[row["origin"]]!=int(row["regime"]):
                raise AssertionError("Original Markov regime mismatch at "+row["origin"])
    print("PASS: Exact training-only regime threshold reproduces all 609 original 30-day origin states",flush=True)
    return dates,returns,states


def model_filter(dates,returns,price):
    """One-sided EWMA/GARCH states, before creating any new forecast outcomes."""
    omega,alpha,beta=GARCH_FIT
    e=EWMA_START
    g=GARCH_START
    daily={}
    for date in dates:
        if date<"2025-01-01":continue
        shock=returns[date]-MU
        e=LAM*e+(1-LAM)*shock*shock
        g=omega+alpha*(100*shock)**2+beta*g
        daily[date]={"ewma":float(e),"garch":float(g)}
    assert min(k for k in daily)=="2025-01-01"
    return daily


def score(rows,h,year,old_score,uncertainty):
    n=len(rows)
    out={}
    for t in THRESHOLDS:
        events=np.array([r[f"event_{t}"] for r in rows])
        models={}
        for m in MODELS:
            p=np.array([r[f"{m}_p{t}"] for r in rows],dtype=float)
            models[m]=dict(brier=float(((p-events)**2).mean()),
                           mean_probability=float(p.mean()),
                           min_probability=float(p.min()),
                           max_probability=float(p.max()),
                           probability_std=float(p.std(ddof=0)))
        out[str(t)]={"n":n,"events":int(events.sum()),"frequency":float(events.mean()),
                     "models":models,"differences":uncertainty[str(t)]}
        if h==30:
            # Original 2025/2026 event frequencies, model probabilities and scores
            # are a protected part of the approved research.
            for m in MODELS:
                expected=old_score[str(t)]["models"][m]["brier"]
                assert abs(models[m]["brier"]-expected)<1e-11,(year,m,t)
            assert int(events.sum())==old_score[str(t)]["events"]
            out[str(t)]=old_score[str(t)]
    return out


def generate():
    originals,old_scores,price=existing_and_price_sources()
    threshold,baseline=retrieve_calibration()
    regimes_by_state=markov_horizon_probabilities()
    dates,returns,regimes=validate_original_states(price,originals,threshold)
    filters=model_filter(dates,returns,price)
    for year,rows in originals.items():
        by_date={r["origin"]:r for r in rows}
        for r in rows:
            day=r["origin"]
            assert abs(float(r["ewma_nextvar"])-filters[day]["ewma"])<1e-12,day
            assert abs(float(r["garch_nextvar_pct2"])-filters[day]["garch"])<1e-7,day
    # Every scientific origin must have an observed close and trailing returns,
    # but model simulations must NOT access the future observed price.
    evidence={"horizons":list(HORIZONS),"status":"Additional horizons exploratory and retrospective; original 30-day evidence immutable",
              "calibration":"2022–2024 only; five models + historical calibration frequency",
              "thresholds":list(THRESHOLDS),"models":list(MODELS),"paths":{"markov":MARKOV_PATHS,"ewma":PATHS,"garch":PATHS},
              "yearEnd":{"2025":"2025-12-31","2026":"2026-10-31"},
              "scores":{},"years":{}}
    OUT.mkdir(parents=True,exist_ok=True)
    for year in (2025,2026):
        cut=dt.date(year,12,31) if year==2025 else dt.date(year,10,31)
        year_first=dt.date(year,1,1)
        year_days=(cut-year_first).days+1
        assert year_days==(365 if year==2025 else 304)
        original_by_date={r["origin"]:r for r in originals[year]}
        rows_for_h={h:[] for h in HORIZONS}
        max_origin=(cut-dt.timedelta(days=7))
        for idx in range((max_origin-year_first).days+1):
            origin=(year_first+dt.timedelta(days=idx))
            date=origin.isoformat()
            source_price=price[date]
            filt=filters[date]
            state=regimes[date]
            if idx%40==0: print(f"Forecasts {year}: {idx+1}/{(max_origin-year_first).days+1}",flush=True)
            prior=np.array([returns[(origin-dt.timedelta(days=i)).isoformat()] for i in range(29,-1,-1)])
            rolling=float(np.std(prior,ddof=1))
            assert rolling>0 and np.isfinite(rolling)
            available=[h for h in HORIZONS if origin+dt.timedelta(days=h)<=cut]
            projections=model_shocks(filt["ewma"],filt["garch"],max(available),
                        seed_e=(20251124 if year==2025 else 20261124)+idx*1009+101,
                        seed_g=(20251124 if year==2025 else 20261124)+idx*1009+211,
                        omega=GARCH_FIT[0],alpha=GARCH_FIT[1],beta=GARCH_FIT[2])
            # Keep published 2026 EWMA streams consistent with original 2026
            # simulation seed family at every origin. The original 2025 EWMA
            # 30d values are preserved, regardless of new stream choices.
            for h in available:
                target=(origin+dt.timedelta(days=h)).isoformat()
                end_price=price[target]
                loss=1-end_price/source_price
                row=dict(origin=date,target=target,btc_origin=source_price,btc_target=end_price,
                         realized_return=end_price/source_price-1,regime=state,
                         rolling30_sigma=rolling,ewma_nextvar=filt["ewma"],garch_nextvar_pct2=filt["garch"])
                for t in THRESHOLDS:
                    event=int(loss>=t/100)
                    row[f"event_{t}"]=event
                    for m in MODELS:
                        if h==30:
                            source=original_by_date.get(date)
                            assert source is not None
                            p=float(source[f"{m}_p{t}"])
                        elif m=="historical":p=float(baseline[h][THRESHOLDS.index(t)])
                        elif m=="gbm":
                            p=float(norm.cdf((math.log1p(-t/100)-MU*h)/(SIGMA*math.sqrt(h))))
                        elif m=="adaptive_gbm":
                            p=float(norm.cdf((math.log1p(-t/100)-MU*h)/(rolling*math.sqrt(h))))
                        elif m=="markov":
                            p=float(regimes_by_state[state][h][THRESHOLDS.index(t)])
                        else:p=float(projections[h][m][THRESHOLDS.index(t)])
                        assert 0<=p<=1
                        row[f"{m}_p{t}"]=p
                if h==30:
                    orig=original_by_date[date]
                    for f in FIELDS:
                        if f in ("origin","target"):assert row[f]==orig[f]
                        elif f in ("btc_origin","btc_target","rolling30_sigma","ewma_nextvar","garch_nextvar_pct2","realized_return"):
                            assert abs(float(row[f])-float(orig[f]))<2e-7,(date,f,row[f],orig[f])
                        else:assert row[f]==int(orig[f]) if f.startswith("event_") or f=="regime" else abs(float(row[f])-float(orig[f]))<1e-12
                    # Copy the original frozen full row, not a reconstructed copy.
                    row={f:(orig[f] if f in ("origin","target") else float(orig[f]) if f not in ("regime","event_10","event_20","event_35") else int(orig[f])) for f in FIELDS}
                rows_for_h[h].append(row)
        expected={2025:{7:358,14:351,30:335,60:305,90:275},
                  2026:{7:297,14:290,30:274,60:244,90:214}}[year]
        evidence["years"][str(year)]={}
        for h in HORIZONS:
            rows=rows_for_h[h]
            assert len(rows)==expected[h],(year,h,len(rows))
            assert rows[0]["origin"]==str(year_first)
            assert rows[-1]["target"]==str(cut)
            assert all((dt.date.fromisoformat(r["target"])-dt.date.fromisoformat(r["origin"])).days==h for r in rows)
            stat=score(rows,h,year,old_scores[year],ci_differences(rows,year,h))
            # Complete original 30-day per-origin data already exists in audited
            # web asset, so the new bundle references it rather than duplicating it.
            evidence["years"][str(year)][str(h)]={
                "horizon":h,"n":len(rows),"end":str(cut),
                "rows":None if h==30 else [[r[f] for f in FIELDS] for r in rows],
                "scores":stat,
                "originEnd":rows[-1]["origin"],
                "source":"protected_original_30d" if h==30 else "new_exploratory_calibration_only",
            }
            if h!=30:
                path=OUT/f"forecasts_{year}_{h}d.csv"
                with path.open("w",newline="",encoding="utf-8") as out:
                    writer=csv.DictWriter(out,fieldnames=FIELDS)
                    writer.writeheader()
                    writer.writerows(rows)
            print(f"{year} H={h}: N={len(rows)}, 10% events={stat['10']['events']}, "+
                  " / ".join(f"{m} {stat['10']['models'][m]['brier']:.6f}" for m in MODELS),flush=True)
    evidence["fields"]=list(FIELDS)
    evidence["regimeThreshold"]=threshold
    evidence["baselineByHorizon"]={str(k):list(map(float,v)) for k,v in baseline.items()}
    evidence["provenance"]="Official 2022–2024 Binance month hashes verified against phase3 source manifest; 2025 and 2026 closes checked against original research ledgers"
    output=ROOT/"docs/v5-evidence-horizons.js"
    output.write_text(
       "/* Audited 7,14,30,60,90-day retrospective loss forecasts. Additional horizons exploratory. */\n"+
       "window.CRL_HORIZON_EVIDENCE="+json.dumps(evidence,separators=(",",":"),allow_nan=False)+";\n",
       encoding="utf-8")
    summary={str(year):{str(h):evidence["years"][str(year)][str(h)]["scores"] for h in HORIZONS}
             for year in (2025,2026)}
    (OUT/"scores_by_year_and_horizon.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    lines=["# Multi-horizon evaluation: executed exploratory results","",
           "**Additional 7, 14, 60 and 90-day forecasts are retrospective exploratory analyses.** All original 2025/2026 30-day scores and probability ledgers were preserved and remain scientifically distinct.",
           "","| Year | Horizon | Origins | 10% events | GBM Brier | Markov Brier | EWMA Brier | Adaptive GBM Brier | GARCH Brier |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for year in (2025,2026):
        for h in HORIZONS:
            sc=summary[str(year)][str(h)]["10"]
            lines.append(f"| {year} | {h} | {sc['n']} | {sc['events']} | "+
                         " | ".join(f"{sc['models'][m]['brier']:.6f}" for m in ("gbm","markov","ewma","adaptive_gbm","garch"))+" |")
    lines.extend(["","## Interpretation","",
      "This is not evidence that the smallest descriptive Brier at a hand-picked horizon guarantees a better model.",
      "Paired bootstrap intervals are descriptive, with overlapping H-day terminal-outcome windows. The 2026 30-day Holm-adjusted primary inference remains unchanged.",
      "Calibration and fitted model parameters use 2022–2024. Observed prices after each origin are never used to estimate the origin forecast; they are used only to score the H-day outcome.",
      "The 2025 new-model forecasts and all added horizon forecasts are explicitly exploratory because earlier 2025 and 2026 outcomes were already inspected.",
      "No 2026 observations later than 31 October 2026 were used.",
      "","## Sources", "",
      "See research/phase5_horizons/EXPLORATORY_PROTOCOL.md, original notebook, research/phase3_2026, research/phase4_2025, and docs/v5-evidence-horizons.js.",
    ])
    (OUT/"FINDINGS.md").write_text("\n".join(lines)+"\n")
    print("PASS: Generated auditable multi-horizon evidence without changing any archived 30-day outputs",flush=True)


if __name__=="__main__":
    generate()
