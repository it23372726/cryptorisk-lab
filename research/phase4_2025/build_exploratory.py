#!/usr/bin/env python3
"""Post-hoc 2025 Adaptive GBM and Gaussian GARCH research extension.

Preserves docs/v2-validation-data.json (original notebook evidence).
Reuses 2026 extension's EXACT frozen GARCH coefficients, variance, drift,
30-day rolling sigma rule and 20,000 paths. An exploratory retrospective
calculation, NOT an independently pre-registered 2025 experiment.

Run:
  python research/phase4_2025/build_exploratory.py --generate
  python research/phase4_2025/build_exploratory.py --verify
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
HISTORY = ROOT / "docs" / "btc-historical.json"
ORIGINAL = ROOT / "docs" / "v2-validation-data.json"
GARCH_METRICS = ROOT / "research" / "phase3_2026" / "results" / "metrics_2026.json"
RESULT_JSON = ROOT / "docs" / "v4-exploratory-2025-data.json"
RESULT_JS = ROOT / "docs" / "v4-exploratory-2025-data.js"
RESULT_REPORT = ROOT / "research" / "phase4_2025" / "FINDINGS.md"

MU = 0.0006149477738712015
SIGMA = 0.028459921644738977
THRESHOLDS = (10, 20, 35)
HORIZON = 30
PATHS = 20_000
SEED = 20261124 + 202500000
BLOCK_REPS = 3000
BLOCK_DAYS = 30


def source_data():
    original = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    research = json.loads(GARCH_METRICS.read_text(encoding="utf-8"))
    rows = original["rows"]
    candles = history["candles"]
    assert len(rows) == 335 and len(candles) == 396
    assert rows[0]["date"] == "2025-01-01" and rows[-1]["date"] == "2025-12-01"
    assert candles[0]["date"] == "2024-12-01" and candles[30]["date"] == "2024-12-31"
    assert candles[30]["close"] == 93576
    assert candles[-1]["date"] == "2025-12-31"
    dates = [dt.date.fromisoformat(c["date"]) for c in candles]
    assert all((dates[i+1]-dates[i]).days == 1 for i in range(395))
    closes = np.array([float(c["close"]) for c in candles], dtype=np.float64)
    assert np.isfinite(closes).all() and (closes > 0).all()
    returns = np.diff(np.log(closes))
    by_date = {c["date"]: i for i,c in enumerate(candles)}
    for r in rows:
        i, j = by_date[r["date"]], by_date[r["end"]]
        assert j-i == 30 and i >= 31
        assert np.isclose(closes[i], r["price"], atol=.011, rtol=0)
        assert np.isclose(closes[j], r["future"], atol=.011, rtol=0)
        assert r["events"] == [int(1-closes[j]/closes[i] >= t/100) for t in THRESHOLDS]
    assert [sum(r["events"][j] for r in rows) for j in range(3)] == [62, 8, 0]

    garch = research["garch_fit"]
    assert garch["n_train"] == 1095 and garch["fit_converged"] is True
    assert garch["arch_version"] == "7.2.0"
    assert abs(garch["calibration_mean_return"] - MU) < 1e-15
    assert np.isclose(garch["omega_pct2"], 1.7429241072532673, atol=1e-13)
    assert np.isclose(garch["alpha"], 0.1689729613867537, atol=1e-13)
    assert np.isclose(garch["beta"], 0.6255015699659665, atol=1e-13)
    assert np.isclose(garch["fit_next_variance_2025_01_01_pct2"], 5.547208876802669, atol=1e-13)
    assert 0 < garch["alpha"] + garch["beta"] < 1
    print("PASS: Audited original 335 × 30-day outcomes, real BTC candles and frozen Gaussian GARCH parameters", flush=True)
    return rows, closes, returns, by_date, garch


def conditional_garch_states(returns, garch):
    """At index i (day 2025-01-01 onwards), h is the variance for day i+1."""
    h = float(garch["fit_next_variance_2025_01_01_pct2"])
    result = {}
    for candle_index in range(31, 396):
        # returns[k-1] is the observed close-to-close return on day k.
        eps = 100 * (float(returns[candle_index-1])-MU)
        h = float(garch["omega_pct2"] + garch["alpha"] * eps * eps + garch["beta"] * h)
        if not (0 < h < 1e6 and np.isfinite(h)):
            raise AssertionError("Non-finite post-origin GARCH variance")
        result[candle_index] = h
    return result


def normal_cdf(z: float) -> float:
    return math.erfc(-z/math.sqrt(2))/2


def garch_probabilities(variance: float, garch: dict, seed: int):
    rng = np.random.default_rng(seed)
    v = np.full(PATHS, variance, dtype=np.float64)
    terminal = np.zeros(PATHS, dtype=np.float64)
    for _ in range(HORIZON):
        z = rng.standard_normal(PATHS)
        eps = np.sqrt(v) * z  # percentage-unit innovation
        terminal += MU + eps/100
        v = garch["omega_pct2"] + garch["alpha"] * eps**2 + garch["beta"] * v
    if not (np.isfinite(terminal).all() and np.isfinite(v).all() and np.all(v>0)):
        raise AssertionError("Unstable Gaussian GARCH Monte Carlo forecast")
    p = [(terminal <= math.log1p(-t/100)).mean() for t in THRESHOLDS]
    if not (0 <= p[2] <= p[1] <= p[0] <= 1):
        raise AssertionError("GARCH terminal-loss probability ordering incorrect")
    return [float(x) for x in p]


def block_indices(n: int):
    rng = np.random.default_rng(20261124)
    blocks = int(np.ceil(n/BLOCK_DAYS))
    starts = rng.integers(0,n,size=(BLOCK_REPS,blocks))
    return ((starts[:,:,None] + np.arange(BLOCK_DAYS)[None,None,:])%n).reshape(BLOCK_REPS,-1)[:,:n]


def historical_scores(original, additions):
    source = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    assert original == source["rows"]
    idx = block_indices(len(original))
    result = {}
    for j,t in enumerate(THRESHOLDS):
        actual = np.array([r["events"][j] for r in original],dtype=np.float64)
        models = {}
        differences = {}
        for model in ("adaptive_gbm", "garch"):
            p = np.array([row["p"][model][j] for row in additions],dtype=float)
            loss = (p-actual)**2
            models[model] = {
                "mean": float(p.mean()), "brier": float(loss.mean()),
                "min": float(p.min()), "max": float(p.max()),
                "sd": float(p.std(ddof=0)),
            }
            for baseline in ("gbm", "markov", "historical"):
                prior = np.array([r["p"][baseline][j] for r in original],dtype=np.float64)
                diff = loss-(prior-actual)**2
                bs=diff[idx].mean(axis=1)
                lower,upper=np.quantile(bs,[.025,.975])
                differences[f"{model}_minus_{baseline}"] = {
                    "mean":float(diff.mean()),"ci95":[float(lower),float(upper)],
                    "block_days":BLOCK_DAYS,"replications":BLOCK_REPS,
                    "inference":"Exploratory descriptive interval only; 2025 was previously examined",
                }
        result[str(t)]={"observed":float(actual.mean()),"events":int(actual.sum()),
                        "n":int(len(actual)),"models":models,"differences":differences}
    return result


def generate():
    rows, closes, returns, by_date, garch = source_data()
    states = conditional_garch_states(returns,garch)
    additions=[]
    for j,row in enumerate(rows):
        i=by_date[row["date"]]
        last30=returns[i-30:i]
        assert len(last30)==30 and np.isfinite(last30).all()
        sigma=float(np.std(last30,ddof=1))
        assert 0 < sigma < 1
        adaptive = [normal_cdf((math.log1p(-t/100)-MU*30) /
                               (sigma*math.sqrt(HORIZON))) for t in THRESHOLDS]
        garch_p=garch_probabilities(states[i],garch,SEED+j*1009+211)
        assert all(0<=v<=1 for v in adaptive)
        assert adaptive[0]>=adaptive[1]>=adaptive[2]
        additions.append({
            "date": row["date"], "rolling_sigma":sigma,
            "garch_nextvar_pct2":states[i],
            "p":{"adaptive_gbm":adaptive,"garch":garch_p},
        })
        if j%45==0 or j==334:
            print(f"Generated {j+1}/335 post-hoc 2025 candidates without lookahead",flush=True)
    scores=historical_scores(rows,additions)
    result={
        "meta":{
            "dataset":"2025 retrospective exploratory extension; original 335×30-day notebook unchanged",
            "period":"2025-01-01 to 2025-12-01",
            "first_target":"2025-01-31","last_target":"2025-12-31",
            "origins":335,"horizon":HORIZON,"thresholds":list(THRESHOLDS),
            "models":["adaptive_gbm","garch"],
            "status":"EXPLORATORY POST-HOC: 2025 outcomes examined before these model additions",
            "not_independent_holdout":True,"not_prospective":True,
            "training":"2022-01-01 through 2024-12-31 frozen original/2026 research",
            "base_source":"docs/v2-validation-data.json",
            "candles_source":"docs/btc-historical.json (verified Binance BTCUSDT UTC daily)",
            "garch_fit_source":"research/phase3_2026/results/metrics_2026.json",
            "garch_fit":garch,
            "mc_paths_per_date":PATHS,"seed_formula":"20261124 + 202500000 + index*1009 + 211",
            "rolling_window":30,"rolling_ddof":1,
            "mean":MU,"sigma_frozen":SIGMA,
            "uncertainty":"Paired circular 30-origin-block bootstrap, 3000 replicates, descriptive only",
        },
        "rows":additions,"scores":scores,
    }
    payload=json.dumps(result,indent=2,allow_nan=False)+"\n"
    RESULT_JSON.write_text(payload,encoding="utf-8")
    RESULT_JS.write_text(
        "/* 2025 ex-post exploratory Adaptive GBM/GARCH research; original notebook values unchanged. */\n"
        "window.CRL_EXPLORATORY_2025="+json.dumps(result,separators=(",",":"),allow_nan=False)+";\n",
        encoding="utf-8")
    lines=[
        "# Exploratory 2025 five-model retrospective comparison",
        "",
        "**Status: post-hoc/exploratory, not independent confirmation.**",
        "",
        "The original notebook and 335 2025 GBM/Markov/EWMA forecasts are preserved exactly. "
        "This add-on applies the later fixed 2026-model definitions to the already-inspected 2025 period. "
        "It cannot be used as new confirmatory 2025 evidence or to select winning parameters.",
        "",
        "Training: frozen 2022–2024; 30-day terminal loss, 335 2025 origins; "
        "Adaptive GBM analytic normal CDF using 30 observed prior returns; "
        "GARCH frozen Gaussian MLE, 20,000 seeded paths/origin; no future-data leakage.",
        "",
        "| Model | ≥10% Brier | ≥20% Brier | ≥35% Brier |",
        "|---|---:|---:|---:|"
    ]
    prior=json.loads(ORIGINAL.read_text())
    for model in ("historical","gbm","markov","ewma"):
        vals=[prior["scores"][str(t)]["models"][model]["brier"] for t in THRESHOLDS]
        lines.append(f"| {model.replace('_',' ').title()} · original | "+" | ".join(f"{x:.6f}" for x in vals)+" |")
    for model in ("adaptive_gbm","garch"):
        vals=[scores[str(t)]["models"][model]["brier"] for t in THRESHOLDS]
        lines.append(f"| {model.replace('_',' ').title()} · post-hoc exploratory | "+" | ".join(f"{x:.6f}" for x in vals)+" |")
    lines += [
        "",f"Actual loss events: ≥10%: {scores['10']['events']}/335; ≥20%: {scores['20']['events']}/335; ≥35%: {scores['35']['events']}/335.",
        "",
        "## Exploratory paired block-bootstrap Brier differences, primary 10% event",
        "",
        "Negative difference favors the new model. These 95% intervals describe sampling uncertainty "
        "in a *previously inspected* year; they do not establish independent statistical superiority.",
        "",
        "| Candidate vs original GBM | Mean Brier difference | Exploratory 95% interval |",
        "|---|---:|---|"
    ]
    for model in ("adaptive_gbm","garch"):
        d=scores["10"]["differences"][f"{model}_minus_gbm"]
        lines.append(f"| {model.replace('_',' ').title()} | {d['mean']:+.6f} | [{d['ci95'][0]:+.6f}, {d['ci95'][1]:+.6f}] |")
    lines += [
        "",
        "## Generalization and limitations",
        "",
        "The separated 2026 holdout evaluated the same 2022–2024 frozen models and found **no statistically "
        "established improvement** from Adaptive GBM or GARCH over constant GBM on the ≥10% metric.",
        "The two study years are different market samples with different loss frequencies, "
        "so raw Brier levels across years cannot be interpreted as model-performance changes without context.",
        "The 335 rolling 30-day windows are strongly overlapping; there were no ≥35% events.",
        "Gaussian shocks can misrepresent fat-tailed BTC outcomes.",
        "",
        "## Verified sources, AI disclosure",
        "",
        "- research/phase4_2025/EXPLORATORY_PROTOCOL.md",
        "- docs/v4-exploratory-2025-data.json (new candidates only)",
        "- docs/v2-validation-data.json (unchanged original research)",
        "- research/phase3_2026/results/metrics_2026.json (GARCH fixed fit)",
        "- docs/btc-historical.json (verified Binance observed BTCUSDT daily OHLC)",
        "- Bollerslev 1986: https://doi.org/10.1016/0304-4076(86)90063-1",
        "- Gneiting and Raftery 2007: https://doi.org/10.1198/016214506000001437",
        "",
        "ChatGPT assisted in methodology and implementation; all new numeric results are generated by this "
        "seeded research script and independently audited against the original published evidence.",
    ]
    RESULT_REPORT.write_text("\n".join(lines)+"\n",encoding="utf-8")
    verify()
    print("PASS: Generated two origin-specific exploratory model forecasts for all 335 dates and three thresholds",flush=True)


def verify():
    rows, closes, returns, by_date, garch=source_data()
    result=json.loads(RESULT_JSON.read_text(encoding="utf-8"))
    assert result["meta"]["origins"]==335
    assert result["meta"]["not_independent_holdout"] is True
    assert result["meta"]["garch_fit"] == garch
    assert "2025 outcomes examined" in result["meta"]["status"]
    assert len(result["rows"])==335
    states=conditional_garch_states(returns,garch)
    for i,(a,b) in enumerate(zip(result["rows"],rows)):
        assert a["date"] == b["date"]
        k=by_date[b["date"]]
        sigma=float(np.std(returns[k-30:k],ddof=1))
        assert math.isclose(a["rolling_sigma"],sigma,abs_tol=1e-13,rel_tol=0)
        assert math.isclose(a["garch_nextvar_pct2"],states[k],abs_tol=1e-11,rel_tol=0)
        adaptive=[normal_cdf((math.log1p(-t/100)-MU*30) /
                             (sigma*math.sqrt(30))) for t in THRESHOLDS]
        np.testing.assert_allclose(adaptive,a["p"]["adaptive_gbm"],rtol=0,atol=1e-12)
        for model in ("adaptive_gbm","garch"):
            p=a["p"][model]
            assert len(p)==3 and 0<=p[2]<=p[1]<=p[0]<=1
    scores=historical_scores(rows,result["rows"])
    for t in THRESHOLDS:
        for m in ("adaptive_gbm","garch"):
            for key in ("mean","brier","min","max","sd"):
                assert math.isclose(scores[str(t)]["models"][m][key],
                                    result["scores"][str(t)]["models"][m][key],
                                    rel_tol=0,abs_tol=1e-12)
        assert result["scores"][str(t)]["events"] == [62,8,0][THRESHOLDS.index(t)]
    js=RESULT_JS.read_text(encoding="utf-8")
    assert "window.CRL_EXPLORATORY_2025=" in js
    j=json.loads(js.split("window.CRL_EXPLORATORY_2025=")[1].strip().rstrip(";"))
    assert j==result
    assert "post-hoc/exploratory" in RESULT_REPORT.read_text()
    print("PASS: Independent replay of all 335 rolling sigmas, GARCH states, 2025 Brier scores and exact website data",flush=True)


def main():
    parser=argparse.ArgumentParser()
    choices=parser.add_mutually_exclusive_group(required=True)
    choices.add_argument("--generate",action="store_true")
    choices.add_argument("--verify",action="store_true")
    args=parser.parse_args()
    if args.generate:generate()
    else:verify()


if __name__=="__main__":main()
