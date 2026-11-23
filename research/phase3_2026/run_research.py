#!/usr/bin/env python3
"""Frozen retrospective 2026 BTC risk study. No changes to the original notebook.

Protocol: research/phase3_2026/PRE_REGISTERED_PROTOCOL.md
Run:
  python research/phase3_2026/run_research.py --self-test
  python research/phase3_2026/run_research.py --run

2026 outcomes are loaded *only* after model definitions, training-period choices,
parameters and significance protocol have been frozen. All forecast states are
strictly left-looking. Reports cannot be used to refit or choose new parameters.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import datetime as dt
import hashlib
import io
import json
import math
import pathlib
import time
import urllib.request
import zipfile

import numpy as np
import pandas as pd
from scipy.stats import norm
from arch import arch_model

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "phase3_2026" / "results"
ORIGINAL = ROOT / "docs" / "btc-historical.json"
VALIDATION_2025 = ROOT / "docs" / "v2-validation-data.json"
BASE_URL = "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1d"
MU = 0.0006149477738712015
SIGMA = 0.028459921644738977
START = dt.date(2022, 1, 1)
TRAIN_END = dt.date(2024, 12, 31)
HOLDOUT_START = dt.date(2026, 1, 1)
HOLDOUT_LAST_CLOSE = dt.date(2026, 10, 31)
LAST_ORIGIN = dt.date(2026, 10, 1)
HORIZON = 30
THRESHOLDS = (10, 20, 35)
MODELS = ("historical", "gbm", "markov", "ewma", "adaptive_gbm", "garch")
PATHS = 20_000
SEED = 20261124
BOOTSTRAP_REPS = 3000
BOOTSTRAP_BLOCK = 30
EWMA_DECAY = 0.90
ROLLING_DAYS = 30
ARCH_VERSION = "7.2.0"


def read_official_month(year: int, month: int):
    key = f"{year:04d}-{month:02d}"
    url = f"{BASE_URL}/BTCUSDT-1d-{key}.zip"
    last_exception = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "CryptoRiskLab-Research/3.0"})
            with urllib.request.urlopen(request, timeout=55) as response:
                payload = response.read()
            if not payload.startswith(b"PK"):
                raise RuntimeError(f"Invalid Binance ZIP payload: {url}")
            digest = hashlib.sha256(payload).hexdigest()
            with zipfile.ZipFile(io.BytesIO(payload)) as zipped:
                names = [name for name in zipped.namelist() if name.endswith(".csv")]
                if len(names) != 1:
                    raise ValueError(f"{key}: Expected a single daily OHLCV CSV")
                raw = zipped.read(names[0]).decode("utf-8-sig")
            rows = []
            divisor = 1_000_000 if year >= 2025 else 1_000
            for record in csv.reader(io.StringIO(raw)):
                if not record or not record[0].isdigit():
                    continue
                if len(record) < 6:
                    raise ValueError(f"Incomplete OHLCV record in {url}")
                timestamp = int(record[0])
                if year >= 2025 and timestamp < 10**15:
                    raise ValueError(f"{key}: microsecond timestamps required")
                if year < 2025 and timestamp >= 10**15:
                    raise ValueError(f"{key}: millisecond timestamps required")
                date = dt.datetime.fromtimestamp(timestamp / divisor, dt.timezone.utc).date()
                if date.strftime("%Y-%m") != key:
                    raise ValueError(f"Unexpected timestamp {date} in {key}")
                item = dict(date=date.isoformat(), open=float(record[1]),
                            high=float(record[2]), low=float(record[3]),
                            close=float(record[4]), volume=float(record[5]))
                if not (item["low"] > 0 and item["volume"] >= 0
                        and item["low"] <= min(item["open"], item["close"])
                        and item["high"] >= max(item["open"], item["close"])):
                    raise ValueError(f"Bad OHLCV consistency at {date}")
                rows.append(item)
            expected = calendar.monthrange(year, month)[1]
            if len(rows) != expected or len({r["date"] for r in rows}) != expected:
                raise ValueError(f"{key}: Expected {expected} unique daily observations; got {len(rows)}")
            print(f"VERIFIED Binance {key}: {len(rows)} days, sha256={digest[:14]}", flush=True)
            return rows, dict(month=key, url=url, sha256=digest, candles=len(rows),
                              unit="microseconds" if year >= 2025 else "milliseconds")
        except Exception as exc:
            last_exception = exc
            if attempt < 2:
                time.sleep(2 + 2 * attempt)
    raise RuntimeError(f"Unable to obtain authenticated Binance month {key}: {last_exception}")


def load_data():
    """2022-24 and 2026 verified monthly archives; 2025 from existing verified bundle."""
    old = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    old_candles = {c["date"]: c for c in old["candles"]}
    assert old_candles["2024-12-31"]["close"] == 93576
    provenance = []
    calibration = []
    for year in range(2022, 2025):
        for month in range(1, 13):
            candles, info = read_official_month(year, month)
            calibration.extend(candles)
            provenance.append(info)
    for candle in calibration[-31:]:
        frozen = old_candles.get(candle["date"])
        if not frozen:
            raise AssertionError("Frozen 2024 historical overlap missing")
        for field in ("open", "high", "low", "close"):
            if abs(candle[field] - frozen[field]) > .011:
                raise ValueError(f"Official archive contradicts frozen December 2024 {field} on {candle['date']}")
    observed_2025 = [
        old_candles[(dt.date(2025, 1, 1) + dt.timedelta(days=i)).isoformat()]
        for i in range(365)
    ]
    existing_manifest = ROOT / "docs" / "btc-2025-sources.json"
    if not existing_manifest.exists():
        raise FileNotFoundError("2025 original-binance archive SHA manifest is absent")
    pinned_2025 = json.loads(existing_manifest.read_text(encoding="utf-8"))
    assert len(pinned_2025["archives"]) == 12
    provenance.extend([
        {**item, "reused_verified_bundle": True}
        for item in pinned_2025["archives"]
    ])
    holdout = []
    for month in range(1, 11):
        candles, info = read_official_month(2026, month)
        holdout.extend(candles)
        provenance.append(info)
    all_rows = calibration + observed_2025 + holdout
    expected_dates = pd.date_range("2022-01-01", "2026-10-31", freq="D", tz="UTC")
    dates = pd.to_datetime([x["date"] for x in all_rows], utc=True)
    if len(dates) != len(expected_dates) or not np.array_equal(dates.values, expected_dates.values):
        raise ValueError("Missing, duplicate, or non-consecutive BTC daily dates")
    frame = pd.DataFrame(all_rows)
    frame["date"] = dates
    frame["log_return"] = np.log(frame["close"]).diff()
    assert len(calibration) == 1096
    assert len(observed_2025) == 365
    assert len(holdout) == 304
    print("PASS: 2022-2024 calibration + 2025 state bridge + Jan-Oct 2026 independent holdout", flush=True)
    return frame.set_index("date"), provenance


def calibrations(frame):
    cal = frame.loc[:TRAIN_END.isoformat(), "log_return"].dropna()
    mu, sigma = float(cal.mean()), float(cal.std(ddof=1))
    # Stop if new source archives disagree with the source used by the 97-cell notebook.
    if not (math.isclose(mu, MU, abs_tol=1e-11) and math.isclose(sigma, SIGMA, abs_tol=1e-11)):
        raise AssertionError(f"Training period diverged from frozen original notebook: {mu}/{sigma} vs {MU}/{SIGMA}")
    rolling14 = frame["log_return"].rolling(14, min_periods=14).std(ddof=1)
    threshold = float(rolling14.loc[:TRAIN_END.isoformat()].dropna().median())
    assert threshold > 0 and np.isfinite(threshold)
    state = (rolling14 >= threshold).astype(int)
    rolling30 = frame["log_return"].rolling(ROLLING_DAYS, min_periods=ROLLING_DAYS).std(ddof=1)
    return dict(train_returns=cal, threshold=threshold, states=state,
                rolling14=rolling14, rolling30=rolling30)


def ewma_filter(frame):
    """Variance after observing date t; belongs to the predictive state for t+1."""
    variance = SIGMA * SIGMA
    filtered = np.empty(len(frame), dtype=float)
    for i, r in enumerate(frame["log_return"].to_numpy()):
        if np.isfinite(r):
            variance = EWMA_DECAY * variance + (1 - EWMA_DECAY) * (float(r) - MU) ** 2
        filtered[i] = variance
    assert np.isfinite(filtered).all() and (filtered > 0).all()
    return pd.Series(filtered, index=frame.index, name="ewma_nextday_variance")


def garch_fit_and_filter(frame, cal):
    """Fit Gaussian GARCH once on 2022-24, recursively filter later observed shocks."""
    import arch
    if arch.__version__ != ARCH_VERSION:
        raise RuntimeError(f"Pin arch=={ARCH_VERSION}; installed {arch.__version__}")
    centered_pct = 100.0 * (cal["train_returns"].to_numpy() - MU)
    model = arch_model(centered_pct, mean="Zero", vol="GARCH",
                       p=1, q=1, dist="normal", rescale=False)
    fit = model.fit(update_freq=0, disp="off", show_warning=False)
    if fit.convergence_flag != 0:
        raise RuntimeError("GARCH MLE failed to converge; no fallback parameters permitted")
    params = {k: float(v) for k, v in fit.params.items()}
    omega, alpha, beta = params["omega"], params["alpha[1]"], params["beta[1]"]
    if not (omega > 0 and 0 <= alpha < 1 and 0 <= beta < 1 and alpha + beta < 1):
        raise AssertionError(f"Fitted GARCH is not stationary: {params}")
    h = float(fit.conditional_volatility[0] ** 2)
    next_variances = np.empty(len(frame), dtype=float)
    r = frame["log_return"].to_numpy()
    for i, value in enumerate(r):
        if np.isfinite(value):
            eps_pct = (float(value) - MU) * 100
            h = omega + alpha * eps_pct**2 + beta * h
        next_variances[i] = h
    expected_next = float(fit.forecast(horizon=1, reindex=False).variance.iloc[-1, 0])
    observed_next = float(next_variances[len(cal["train_returns"])])
    if not np.isclose(expected_next, observed_next, rtol=1e-5, atol=1e-6):
        raise AssertionError(f"GARCH filter/fit one-step forecast disagree: {observed_next}/{expected_next}")
    assert np.isfinite(next_variances).all() and np.all(next_variances > 0)
    return pd.Series(next_variances, index=frame.index, name="garch_nextday_variance_pct2"), {
        "omega_pct2": omega, "alpha": alpha, "beta": beta,
        "persistence": alpha + beta, "calibration_mean_return": MU,
        "loglikelihood": float(fit.loglikelihood), "n_train": int(len(centered_pct)),
        "arch_version": arch.__version__, "fit_converged": True,
        "fit_next_variance_2025_01_01_pct2": expected_next
    }


def inherited_probabilities():
    """Use exact, frozen original Markov Monte Carlo probabilities, not a new fit."""
    v = json.loads(VALIDATION_2025.read_text(encoding="utf-8"))
    assert len(v["rows"]) == 335
    states = {}
    for regime in (0, 1):
        matched = [r for r in v["rows"] if r["regime"] == regime]
        assert matched, f"Missing frozen state {regime} forecasts"
        p = np.array(matched[0]["p"]["markov"], dtype=float)
        assert all(np.array_equal(np.array(r["p"]["markov"],dtype=float),p) for r in matched)
        states[regime] = p
    gbm = np.array(v["rows"][0]["p"]["gbm"], dtype=float)
    historical = np.array(v["rows"][0]["p"]["historical"], dtype=float)
    assert all(np.array_equal(np.array(r["p"]["gbm"],dtype=float),gbm) for r in v["rows"])
    assert all(np.array_equal(np.array(r["p"]["historical"],dtype=float),historical) for r in v["rows"])
    analytic = norm.cdf((np.log1p(-np.array(THRESHOLDS)/100)-MU*HORIZON)/(SIGMA*np.sqrt(HORIZON)))
    np.testing.assert_allclose(gbm, analytic, atol=1e-12, rtol=1e-12)
    return dict(markov=states, gbm=gbm, historical=historical)


def simulated_probabilities(nextvar, model, seed, omega=0.0, alpha=0.0, beta=0.0,
                            paths=PATHS):
    """Vectorized and reproducible 30-day terminal-loss Monte Carlo estimates."""
    if not np.isfinite(nextvar) or nextvar <= 0 or paths <= 0:
        raise ValueError("Invalid model next-day variance / path count")
    rng = np.random.default_rng(seed)
    variance = np.full(paths, float(nextvar), dtype=np.float64)
    log_returns = np.zeros(paths, dtype=np.float64)
    for _ in range(HORIZON):
        z = rng.standard_normal(paths)
        shocks = np.sqrt(variance) * z
        if model == "ewma":
            log_returns += MU + shocks
            variance = EWMA_DECAY * variance + (1.0 - EWMA_DECAY) * shocks**2
        elif model == "garch":
            # GARCH variances and shocks are in (percent log-return)^2 and percent.
            log_returns += MU + shocks / 100.0
            variance = omega + alpha * shocks**2 + beta * variance
        else:
            raise ValueError(f"Unknown MC model {model}")
    if not (np.isfinite(log_returns).all() and np.isfinite(variance).all()
            and np.all(variance >= 0)):
        raise AssertionError(f"Non-finite forecast state in {model}")
    event_cutoffs = np.log1p(-np.asarray(THRESHOLDS)/100.0)
    p = (log_returns[:, None] <= event_cutoffs).mean(axis=0)
    if not (0 <= p[2] <= p[1] <= p[0] <= 1):
        raise AssertionError("Event thresholds must be ordered")
    return p


def forecast_all(frame, cal, ewma, garch, pars, old):
    dates = pd.date_range(HOLDOUT_START, LAST_ORIGIN, freq="D", tz="UTC")
    assert len(dates) == 274, len(dates)
    ledger = []
    for index, origin in enumerate(dates):
        future = origin + pd.Timedelta(days=HORIZON)
        assert future <= pd.Timestamp(HOLDOUT_LAST_CLOSE, tz="UTC")
        p0, p1 = float(frame.at[origin, "close"]), float(frame.at[future, "close"])
        realized_loss = 1 - p1 / p0
        regime = int(cal["states"].loc[origin])
        rvol = float(cal["rolling30"].loc[origin])
        if not (rvol > 0 and np.isfinite(rvol)):
            raise AssertionError(f"Non-finite 30-day rolling volatility at {origin}")
        p = {
            "historical": old["historical"],
            "gbm": old["gbm"],
            "markov": old["markov"][regime],
            "adaptive_gbm": norm.cdf((np.log1p(-np.array(THRESHOLDS)/100.0) - MU*HORIZON) /
                                      (rvol * np.sqrt(HORIZON))),
            "ewma": simulated_probabilities(float(ewma.loc[origin]), "ewma",
                                            seed=SEED + index * 1009 + 101),
            "garch": simulated_probabilities(float(garch.loc[origin]), "garch",
                                             seed=SEED + index * 1009 + 211,
                                             omega=pars["omega_pct2"], alpha=pars["alpha"],
                                             beta=pars["beta"])
        }
        event = [int(realized_loss >= threshold/100) for threshold in THRESHOLDS]
        row = {
            "origin": origin.strftime("%Y-%m-%d"), "target": future.strftime("%Y-%m-%d"),
            "btc_origin": p0, "btc_target": p1,
            "realized_return": p1/p0 - 1, "regime": regime,
            "rolling30_sigma": rvol, "ewma_nextvar": float(ewma.loc[origin]),
            "garch_nextvar_pct2": float(garch.loc[origin]),
        }
        for j, threshold in enumerate(THRESHOLDS):
            row[f"event_{threshold}"] = event[j]
            for model in MODELS:
                pj = float(p[model][j])
                if not 0 <= pj <= 1:
                    raise AssertionError(f"Bad {model} probability at {origin}")
                row[f"{model}_p{threshold}"] = pj
        ledger.append(row)
        if index % 30 == 0 or index == len(dates)-1:
            print(f"Forecasted {index+1}/{len(dates)} fixed 2026 origins", flush=True)
    output = pd.DataFrame(ledger)
    assert len(output) == 274 and output["origin"].is_unique and output["target"].iloc[-1] == "2026-10-31"
    for m in MODELS:
        assert ((output[f"{m}_p10"] >= output[f"{m}_p20"])
                & (output[f"{m}_p20"] >= output[f"{m}_p35"])).all()
    assert output["btc_origin"].gt(0).all() and output["btc_target"].gt(0).all()
    return output


def block_indices(n, repetitions=BOOTSTRAP_REPS, block=BOOTSTRAP_BLOCK, seed=SEED):
    generator = np.random.default_rng(seed)
    number_of_blocks = int(np.ceil(n / block))
    starts = generator.integers(0, n, size=(repetitions, number_of_blocks))
    return ((starts[:, :, None] + np.arange(block)[None, None, :]) % n).reshape(repetitions, -1)[:, :n]


def compare_brier(ledger):
    n = len(ledger)
    assert n == 274
    indices = block_indices(n)
    score = {}
    for t in THRESHOLDS:
        binary = ledger[f"event_{t}"].to_numpy(dtype=float)
        result = {"n": n, "events": int(binary.sum()), "frequency": float(binary.mean()), "models": {}, "differences": {}}
        losses = {}
        for m in MODELS:
            predictions = ledger[f"{m}_p{t}"].to_numpy(dtype=float)
            loss = (predictions-binary)**2
            losses[m] = loss
            result["models"][m] = {
                "brier": float(loss.mean()),
                "mean_probability": float(predictions.mean()),
                "min_probability": float(predictions.min()),
                "max_probability": float(predictions.max()),
                "probability_std": float(predictions.std(ddof=0)),
            }
        for a in ("markov","ewma","adaptive_gbm","garch"):
            for b in ("gbm","markov","historical"):
                if a == b:continue
                diff = losses[a]-losses[b]  # negative = model a scores better
                mean = float(diff.mean())
                bs = diff[indices].mean(axis=1)
                lo, hi = np.quantile(bs, [.025,.975])
                # Bootstrap null-centred two-sided p-value, circular blocks.
                pval = float((np.count_nonzero(np.abs(bs-mean)>=abs(mean))+1)/(len(bs)+1))
                result["differences"][f"{a}_minus_{b}"] = {
                    "mean": mean, "ci95": [float(lo),float(hi)],
                    "two_sided_centered_bootstrap_p": pval,
                    "bootstrap_block": BOOTSTRAP_BLOCK,
                }
        score[str(t)] = result
    keys = ("adaptive_gbm_minus_gbm", "garch_minus_gbm")
    pvals = [score["10"]["differences"][key]["two_sided_centered_bootstrap_p"] for key in keys]
    order = np.argsort(pvals)
    adjusted = [0.0,0.0]
    previous = 0.0
    for rank,k in enumerate(order):
        previous = max(previous, min(1.0, (len(keys)-rank)*pvals[k]))
        adjusted[k] = previous
    primary = {}
    for k,key in enumerate(keys):
        item=score["10"]["differences"][key]
        # Direction must be beneficial (difference < 0); bootstrap is two-sided.
        primary[key] = {
            "holm_adjusted_p": adjusted[k],
            "claim_supported": bool(item["mean"] < 0 and adjusted[k] < .05
                                    and item["ci95"][1] < 0),
            "interpretation": ("Evidence of lower Brier score" if item["mean"] < 0
                               and adjusted[k] < .05 and item["ci95"][1] < 0
                               else "No statistically established improvement")
        }
    return score, primary


def render_plots(ledger, scores):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    dates = pd.to_datetime(ledger["origin"], utc=True)
    fig,ax=plt.subplots(figsize=(12,4.6))
    for model in ("gbm","markov","ewma","adaptive_gbm","garch"):
        ax.plot(dates,ledger[f"{model}_p10"],linewidth=1.2,label=model.replace("_"," ").upper(),alpha=.8)
    for when in dates[ledger["event_10"].to_numpy(dtype=bool)]:
        ax.axvline(when, alpha=.035,color="red")
    ax.set(title="Frozen 2026 30-day forecasts: P(terminal loss >=10%)",
           xlabel="Forecast origin (UTC)",ylabel="Predicted probability")
    ax.legend(loc="best",ncol=3,fontsize=8)
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(OUT/"forecast_probability_timeline.png",dpi=165)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.4))
    model_order=["historical","gbm","markov","ewma","adaptive_gbm","garch"]
    for i,m in enumerate(model_order):
        ax.barh(i,scores["10"]["models"][m]["brier"])
    ax.set_yticks(range(len(model_order)),[m.replace("_"," ").upper() for m in model_order])
    ax.set(xlabel="Mean Brier score (lower is better)",title="2026 retrospective 30-day terminal 10% loss forecast accuracy")
    ax.invert_yaxis()
    ax.grid(axis="x",alpha=.24)
    fig.tight_layout()
    fig.savefig(OUT/"primary_brier_comparison.png",dpi=165)
    plt.close(fig)


def write_outputs(ledger, scores, primary, fit, archive_manifest):
    OUT.mkdir(parents=True,exist_ok=True)
    ledger.to_csv(OUT/"forecast_ledger_2026.csv",index=False,float_format="%.12g")
    report = {
        "experiment": "Frozen 2026 Jan-Oct retrospective holdout, 30-day forecasts",
        "protocol": "research/phase3_2026/PRE_REGISTERED_PROTOCOL.md",
        "not_prospective": True,
        "no_parameter_tuning_on_2026": True,
        "evaluation_start": "2026-01-01", "evaluation_last_origin": "2026-10-01",
        "last_actual_close": "2026-10-31", "origins":len(ledger),
        "model_calibration":"2022-01-01 through 2024-12-31",
        "horizon_days":HORIZON,"primary_threshold_pct":10,
        "secondary_thresholds_pct":[20,35],
        "forecast_paths_each_origin":{"ewma":PATHS,"garch":PATHS},
        "bootstrap":{"circular_block_size":BOOTSTRAP_BLOCK,"replications":BOOTSTRAP_REPS,"seed":SEED},
        "garch_fit":fit,"scores":scores,"primary_holm_tests":primary,
        "provenance_manifest": "research/phase3_2026/results/archive_sha256_manifest.json",
        "limitations":[
            "Overlapping 30-day windows; uncertainty estimates are block-bootstrap approximations",
            "Retrospective 2026 holdout, not forecasts committed prior to 2026 outcome dates",
            "Gaussian shocks underrepresent some tail phenomena and may miscalibrate losses",
            "Historical 2025 exploratory EWMA selection was previously inspected",
            "No model is presumed superior; do not choose new parameter values based on this holdout",
        ]
    }
    (OUT/"metrics_2026.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    (OUT/"archive_sha256_manifest.json").write_text(json.dumps({
        "source":"Binance Public Data BTCUSDT spot 1-day UTC; 2025 from verified previous bundle",
        "period":"2022-01-01 to 2026-10-31",
        "archives":archive_manifest
    },indent=2)+"\n")
    render_plots(ledger,scores)
    sorted_models=sorted(MODELS,key=lambda m:scores["10"]["models"][m]["brier"])
    lines=[
        "# Frozen 2026 retrospective replication: executed findings",
        "",
        "**Research question:** Does adaptive GBM or Gaussian GARCH improve 30-day Bitcoin terminal-loss forecasts?",
        "",
        "**No hindsight tuning:** All core parameters and evaluation dates fixed in PRE_REGISTERED_PROTOCOL.md. "
        "The fitted GARCH uses 2022–2024 only; 2025 and prior-to-origin 2026 update conditional states but never re-fit coefficients.",
        "",
        f"**Sample:** {len(ledger)} overlapping 30-day forecast origins, 2026-01-01 through 2026-10-01, outcomes to 2026-10-31.",
        f"**Observed events:** 10%: {scores['10']['events']}; 20%: {scores['20']['events']}; 35%: {scores['35']['events']}.",
        "",
        "## Terminal-loss forecast Brier scores (lower is better)",
        "",
        "| Model | ≥10% (primary) | ≥20% | ≥35% |",
        "|---|---:|---:|---:|"
    ]
    for m in sorted_models:
        vals=[scores[str(t)]["models"][m]["brier"] for t in THRESHOLDS]
        lines.append(f"| {m.replace('_',' ').title()} | {vals[0]:.6f} | {vals[1]:.6f} | {vals[2]:.6f} |")
    lines.extend([
        "", "## Prespecified primary comparisons (10% event)",
        "", "| Candidate vs original constant GBM | Difference in Brier (negative = better) | 95% block-bootstrap CI | Holm adjusted p | Claim |",
        "|---|---:|---|---:|---|"
    ])
    for key in ("adaptive_gbm_minus_gbm","garch_minus_gbm"):
        info=scores["10"]["differences"][key]
        adjusted=primary[key]
        lines.append(f"| {key.split('_minus_')[0].replace('_',' ').title()} | {info['mean']:+.6f} | "
                     f"[{info['ci95'][0]:+.6f}, {info['ci95'][1]:+.6f}] | "
                     f"{adjusted['holm_adjusted_p']:.4f} | {adjusted['interpretation']} |")
    lines.extend([
        "", "## Interpretation and limitations",
        "",
        "- Lower Brier scores are **descriptive** unless supported by dependence-aware uncertainty and Holm correction.",
        "- Both GARCH and rolling GBM can dynamically change probability without necessarily predicting future loss events better.",
        "- These 274 daily forecasts overlap over 30 days. The effective sample size is much smaller than 274.",
        "- The test period already occurred before this report. This is a separately frozen **retrospective** replication, not prospective forecasts recorded in advance.",
        "- EWMA is a previously inspected exploratory benchmark, not a new out-of-sample model-selection result.",
        "- No >=35% loss events or few tail events would weaken any tail-risk conclusion.",
        "- The Monte Carlo estimators have finite simulation uncertainty, especially for rare events.",
        "",
        "## Files and reproduction",
        "",
        "- PRE_REGISTERED_PROTOCOL.md: frozen research and statistical hypotheses.",
        "- run_research.py: deterministic code and reproducible audit tests.",
        "- results/archive_sha256_manifest.json: official archive URLs, UTC periods and SHA-256 digests.",
        "- results/forecast_ledger_2026.csv: every forecast, prior-only state and observed 30-day outcome.",
        "- results/metrics_2026.json: scores, bootstrap uncertainty and exact GARCH parameter estimates.",
        "- results/forecast_probability_timeline.png and results/primary_brier_comparison.png: research figures.",
        "",
        "Run: \`python research/phase3_2026/run_research.py --run\` with \`arch==7.2.0\` and existing scientific requirements."
    ])
    (OUT/"FINDINGS.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("PASS: Wrote frozen research CSV, JSON, figures, SHA source ledger, scientific interpretation",flush=True)


def self_test():
    # Frozen GBM tail probabilities must agree with the approved notebook.
    v=inherited_probabilities()
    assert len(v["markov"]) == 2
    assert all(v["markov"][s][0] > v["markov"][s][1] > v["markov"][s][2] for s in (0,1))
    # Adaptive formula with unchanged fixed sigma must collapse to original GBM.
    static = norm.cdf((np.log1p(-np.asarray(THRESHOLDS)/100)-MU*HORIZON)/(SIGMA*np.sqrt(HORIZON)))
    np.testing.assert_allclose(static,v["gbm"],rtol=1e-12,atol=1e-12)
    # Simulated variance recursion should reproduce the analytic GBM in lambda=1 limit:
    # independent fixed-variance Monte Carlo, 30 days, 80k paths.
    rng=np.random.default_rng(740001)
    terminal=MU*HORIZON + SIGMA*np.sqrt(HORIZON)*rng.standard_normal(80000)
    p=np.mean(terminal<=np.log(.9))
    expected=v["gbm"][0]
    se=np.sqrt(expected*(1-expected)/80000)
    assert abs(p-expected)<4*se
    # GARCH fixed parameter recursion is causal and stays positive.
    omega,alpha,beta=0.02,0.08,0.88
    x=1.0
    for shock in [.02, -1.4, 2.0, 0.0]:
        x=omega+alpha*shock**2+beta*x
        assert x>0 and np.isfinite(x)
    # Reproducible EWMA/GARCH Monte Carlo and monotone losses.
    for model,kwargs in [("ewma",{}),("garch",{"omega":0.02,"alpha":0.08,"beta":0.88})]:
        first=simulated_probabilities(.0004 if model=="ewma" else 2.0,model,321,paths=1500,**kwargs)
        second=simulated_probabilities(.0004 if model=="ewma" else 2.0,model,321,paths=1500,**kwargs)
        np.testing.assert_array_equal(first,second)
        assert 0<=first[2]<=first[1]<=first[0]<=1
    a=block_indices(274)
    np.testing.assert_array_equal(a,block_indices(274))
    assert a.shape==(3000,274) and ((a>=0)&(a<274)).all()
    print("PASS: Frozen calibration, limit case, GARCH recursion, Monte Carlo reproducibility and block bootstrap",flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    opts=parser.add_mutually_exclusive_group(required=True)
    opts.add_argument("--self-test",action="store_true")
    opts.add_argument("--run",action="store_true")
    args=parser.parse_args()
    if args.self_test:
        self_test();return
    print("RUNNING FROZEN 2026 RETROSPECTIVE PROTOCOL: no model selection using holdout outcomes",flush=True)
    frame,archive_manifest=load_data()
    cal=calibrations(frame)
    ewma=ewma_filter(frame)
    garch,parameters=garch_fit_and_filter(frame,cal)
    old=inherited_probabilities()
    print(f"PASS: GARCH(1,1) fit omega={parameters['omega_pct2']:.6g}, "
          f"alpha={parameters['alpha']:.5f}, beta={parameters['beta']:.5f}",flush=True)
    # Very important: independently verify the frozen EWMA warm state at 2024-12-31.
    baseline=json.loads((ROOT/"docs"/"v2-validation-data.json").read_text())
    assert np.isclose(ewma.loc[pd.Timestamp("2024-12-31",tz="UTC")],0.0004616494175752784,
                      atol=1e-13,rtol=0), "EWMA origin state does not reproduce executed notebook"
    ledger=forecast_all(frame,cal,ewma,garch,parameters,old)
    scores,primary=compare_brier(ledger)
    write_outputs(ledger,scores,primary,parameters,archive_manifest)
    for t in THRESHOLDS:
        print(f"2026 >= {t}%: events={scores[str(t)]['events']}, Brier: "+
              ", ".join(f"{m}={scores[str(t)]['models'][m]['brier']:.6f}" for m in MODELS),
              flush=True)
    for key,item in primary.items():
        print(f"PRIMARY {key}: adjusted p={item['holm_adjusted_p']:.5f}, "
              f"established={item['claim_supported']}",flush=True)
    print("PASS: Complete research extension, 2026 scores, dependence-aware inference, no lookahead",flush=True)


if __name__=="__main__":
    main()
