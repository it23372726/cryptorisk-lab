#!/usr/bin/env python3
"""2025 exploratory five-model comparison. Original 2025 values are NEVER replaced.

Extends the frozen executed 2025 notebook table by adding two models whose
specifications and GARCH fit were frozen in the distinct 2026 experiment.
No claims of blind/confirmatory 2025 superiority are permitted.

Run from repository root: python research/phase4_2025/run_exploratory.py
"""
from __future__ import annotations
import csv
import datetime as dt
import io
import json
import math
import pathlib
import numpy as np
from scipy.stats import norm

ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/"research"/"phase4_2025"/"results"
CORE=ROOT/"docs"/"v2-validation-data.json"
HISTORY=ROOT/"docs"/"btc-historical.json"
FIT=ROOT/"research"/"phase3_2026"/"results"/"metrics_2026.json"
THRESHOLDS=(10,20,35)
MODELS=("historical","gbm","markov","ewma","adaptive_gbm","garch")
MU=0.0006149477738712015
SIGMA=0.028459921644738977
N=20_000
HORIZON=30
SEED=20251124
BLOCK=30
BOOTSTRAPS=3000


def garch_probabilities(var_pct2,omega,alpha,beta,seed):
    rng=np.random.default_rng(seed)
    var=np.full(N,var_pct2,dtype=np.float64)
    terminal=np.zeros(N,dtype=np.float64)
    for day in range(HORIZON):
        shock=np.sqrt(var)*rng.standard_normal(N)
        terminal+=MU+shock/100
        var=omega+alpha*shock**2+beta*var
    assert np.all(np.isfinite(terminal)) and np.all(var>0)
    cuts=np.log1p(-np.array(THRESHOLDS)/100.0)
    p=np.mean(terminal[:,None]<=cuts,axis=0)
    assert 0<=p[2]<=p[1]<=p[0]<=1
    return p


def bootstrap_differences(rows,threshold,losses):
    n=len(rows)
    rng=np.random.default_rng(SEED+threshold)
    starts=rng.integers(0,n,size=(BOOTSTRAPS,int(np.ceil(n/BLOCK))))
    ix=((starts[:,:,None]+np.arange(BLOCK)[None,None,:])%n).reshape(BOOTSTRAPS,-1)[:,:n]
    pairs={}
    for m in ("markov","ewma","adaptive_gbm","garch"):
        for baseline in ("gbm","historical"):
            delta=losses[m]-losses[baseline]
            sims=delta[ix].mean(axis=1)
            lo,hi=np.quantile(sims,[.025,.975])
            center=float(delta.mean())
            null_p=float((np.count_nonzero(np.abs(sims-center)>=abs(center))+1)/(BOOTSTRAPS+1))
            pairs[m+"_minus_"+baseline]={
                "mean":center, "ci95":[float(lo),float(hi)],
                "two_sided_centered_bootstrap_p":null_p,
                "bootstrap_block":BLOCK,"exploratory":True
            }
    return pairs


def main():
    v=json.loads(CORE.read_text())
    actual=json.loads(HISTORY.read_text())
    fit=json.loads(FIT.read_text())["garch_fit"]
    assert len(v["rows"])==335 and len(actual["candles"])==396
    assert actual["candles"][0]["date"]=="2024-12-01"
    assert actual["candles"][30]["date"]=="2024-12-31" and actual["candles"][30]["close"]==93576
    assert actual["candles"][-1]["date"]=="2025-12-31"
    omega,alpha,beta=(fit["omega_pct2"],fit["alpha"],fit["beta"])
    assert (omega,alpha,beta)==(1.7429241072532673,0.1689729613867537,0.6255015699659665)
    assert fit["n_train"]==1095 and fit["fit_converged"] and alpha+beta<1
    initial=float(fit["fit_next_variance_2025_01_01_pct2"])
    assert abs(initial-5.547208876802669)<1e-12
    candles=actual["candles"]
    dates=[c["date"] for c in candles]
    observed={c["date"]:float(c["close"]) for c in candles}
    for i,date in enumerate(dates):
        assert date==(dt.date(2024,12,1)+dt.timedelta(days=i)).isoformat()
    logret=[float("nan")]+[math.log(float(candles[i]["close"])/float(candles[i-1]["close"])) for i in range(1,len(candles))]
    # At 2024-12-31 the fitted GARCH one-day-ahead variance for 2025-01-01
    # is known; 2025 origin day's return is included before making its forecast.
    garch_nextvar=initial
    extended=[]
    for i,original in enumerate(v["rows"]):
        date=original["date"]
        assert date==(dt.date(2025,1,1)+dt.timedelta(days=i)).isoformat()
        day=31+i
        assert dates[day]==date
        assert abs(observed[date]-float(original["price"]))<.001
        assert original["end"]==(dt.date.fromisoformat(date)+dt.timedelta(days=30)).isoformat()
        assert abs(observed[original["end"]]-float(original["future"]))<.001
        eps_pct=(logret[day]-MU)*100
        garch_nextvar=omega+alpha*eps_pct**2+beta*garch_nextvar
        # The previous 30 observed *returns* are available at this origin.
        rolling=float(np.std(logret[day-29:day+1],ddof=1))
        assert math.isfinite(rolling) and rolling>0 and garch_nextvar>0
        cut=np.log1p(-np.array(THRESHOLDS)/100)
        adaptive=norm.cdf((cut-MU*HORIZON)/(rolling*np.sqrt(HORIZON)))
        garch=garch_probabilities(garch_nextvar,omega,alpha,beta,SEED+i*1009+211)
        orig_p=original["p"]
        assert list(sorted(orig_p))==list(sorted(("historical","gbm","markov","ewma")))
        row={
            "origin":date,"target":original["end"],
            "btc_origin":float(original["price"]),"btc_target":float(original["future"]),
            "realized_return":float(original["future"])/float(original["price"])-1,
            "regime":int(original["regime"]),
            "rolling30_sigma":rolling,"ewma_nextvar":float(original["variance"]),
            "garch_nextvar_pct2":float(garch_nextvar)
        }
        for j,t in enumerate(THRESHOLDS):
            event=int(original["events"][j])
            assert event==int((1-row["btc_target"]/row["btc_origin"])>=t/100)
            row[f"event_{t}"]=event
            for m in MODELS:
                probability=float(adaptive[j] if m=="adaptive_gbm" else garch[j] if m=="garch"
                                  else orig_p[m][j])
                assert 0<=probability<=1
                row[f"{m}_p{t}"]=probability
        extended.append(row)
        if i%56==0:print("Added exploratory 2025 forecasts: "+str(i+1)+"/335",flush=True)
    assert len(extended)==335
    for m in ("gbm","markov","ewma","historical"):
        for i,original in enumerate(v["rows"]):
            assert all(extended[i][f"{m}_p{t}"]==original["p"][m][j] for j,t in enumerate(THRESHOLDS))
    stats={}
    for t in THRESHOLDS:
        event=np.asarray([r[f"event_{t}"] for r in extended])
        loss={}
        model_stats={}
        for m in MODELS:
            p=np.array([r[f"{m}_p{t}"] for r in extended],dtype=float)
            loss[m]=(p-event)**2
            model_stats[m]=dict(brier=float(loss[m].mean()),
                                mean_probability=float(p.mean()),
                                min_probability=float(p.min()),
                                max_probability=float(p.max()),
                                probability_std=float(p.std(ddof=0)))
            if m in ("gbm","markov","ewma","historical"):
                # Guarantee every original notebook Brier score is preserved.
                assert abs(model_stats[m]["brier"]-v["scores"][str(t)]["models"][m]["brier"])<1e-12
        stats[str(t)]=dict(n=335,events=int(event.sum()),frequency=float(event.mean()),
                           models=model_stats,
                           differences=bootstrap_differences(extended,t,loss))
    results={
        "study":"2025 post-hoc exploratory five-model extension",
        "status":"exploratory after 2025 outcomes already inspected; NOT new confirmatory holdout",
        "origins":335,"horizon":30,"originFirst":"2025-01-01",
        "originLast":"2025-12-01","lastActual":"2025-12-31",
        "pathsPerGarchOrigin":N,
        "adaptiveWindow":30,"fixed2022to2024Mean":MU,
        "garchFit":fit,"scores":stats,
        "original2025ScoresPreserved":True,
        "sources":["docs/v2-validation-data.json","docs/btc-historical.json",
                   "research/phase3_2026/results/metrics_2026.json"],
        "caveats":[
            "Adaptive GBM and GARCH were added after 2025 results were viewed; exploratory only.",
            "Original GBM, Markov, EWMA and historical-frequency probabilities and outcomes are unchanged.",
            "2025 origins overlap in 30-day windows; bootstrap bounds are descriptive.",
            "All added model states use observed price returns only through the origin; simulations never see future returns.",
            "GARCH fitted coefficients were frozen from 2022–2024, not refitted on 2025.",
            "2026 confirmatory-protocol retrospective results and inference remain untouched."
        ]
    }
    OUT.mkdir(exist_ok=True,parents=True)
    keys=list(extended[0])
    with (OUT/"forecast_ledger_2025_extended.csv").open("w",encoding="utf-8",newline="") as o:
        w=csv.DictWriter(o,fieldnames=keys);w.writeheader();w.writerows(extended)
    (OUT/"metrics_2025_extended.json").write_text(json.dumps(results,indent=2,allow_nan=False)+"\n")
    # The website consumes the exact stored CSV data; do not recompute probabilities in JS.
    payload={ "source":"2025 exploratory extension; original notebook predictions preserved exactly",
      "originStart":"2025-01-01","originEnd":"2025-12-01","finalObserved":"2025-12-31",
      "horizon":30,"n":335,"columns":keys,
      "records":[[r[k] for k in keys] for r in extended],
      "scores":stats,"garch":fit,"exploratory":True,
      "sources":results["sources"],"caveats":results["caveats"]
    }
    (ROOT/"docs"/"v4-evidence-2025.js").write_text(
        "/* 2025 post-hoc exploratory extension: unchanged original 3-model scores. */\n"+
        "window.CRL_EVIDENCE_2025="+json.dumps(payload,separators=(",",":"),allow_nan=False)+";\n",
        encoding="utf-8")
    lines=[
      "# Five-model 2025 extension · exploratory, post-hoc",
      "",
      "**This is NOT an independent new blind 2025 evaluation.** The original three-model notebook predictions and historical baseline were preserved exactly. Added Adaptive GBM/GARCH comparisons were specified after seeing the 2025 results and the separate 2026 research.",
      "",
      "**Forecast origins:** 335 dates, 2025-01-01 through 2025-12-01. Same real BTC/USDT closes, same 30-day terminal loss events as original notebook.",
      "",
      "| Model | ≥10% Brier | ≥20% Brier | ≥35% Brier |",
      "|---|---:|---:|---:|"
    ]
    for m in sorted(MODELS,key=lambda m:stats["10"]["models"][m]["brier"]):
        lines.append("| "+m.replace("_"," ").title()+" | "+" | ".join(
          f"{stats[str(t)]['models'][m]['brier']:.6f}" for t in THRESHOLDS)+" |")
    lines.extend(["","## Interpretation","",
      "Lower descriptive Brier is better, but candidate selection after viewing 2025 makes superiority claims from 2025 exploratory. The separate 2026 evaluation retains its original frozen protocol and findings, including its conclusion that new models did not establish statistical improvement over GBM.",
      "",
      "The data files contain every origin's input state, archived probability, observed price and actual loss event. Both added models use no 2025 prices after the forecast origin to initialize a forecast.",
      "",
      "## Reproduction",
      "",
      "Run: \`python research/phase4_2025/run_exploratory.py\` in the pinned scientific environment from \`research/phase3_2026/requirements-lock.txt\`.",
      "Audit: \`python research/phase4_2025/verify_extension.py\`.",
      "",
      "Methods: \`research/phase4_2025/EXPLORATORY_PROTOCOL.md\`; original 2025 notebook: \`notebook/cryptorisk-lab.ipynb\`."
    ])
    (OUT/"FINDINGS.md").write_text("\n".join(lines)+"\n")
    for t in THRESHOLDS:
        print(f"2025 >= {t}%: "+", ".join(m+"="+f'{stats[str(t)]["models"][m]["brier"]:.6f}' for m in MODELS),flush=True)
    print("PASS: 335 authentic 2025 five-model origins, original model predictions unchanged; exploratory research extension",flush=True)


if __name__=="__main__":
    main()
