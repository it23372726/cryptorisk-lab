#!/usr/bin/env python3
"""Check the *scientific* reproducibility of the frozen 2026 holdout.

The runner recomputes the full experiment, which overwrites results/ files.
The published baseline comes directly from the exact checked-out git commit,
not from the newly generated files. Exact agreement is required for sources,
dates, actual prices, labels, loss events and seeded analytical forecasts.
A tightly bounded numerical tolerance is allowed for the nonlinear GARCH
optimizer and for random-simulation probabilities at Monte Carlo resolution.

A raw 'git diff --exit-code' is UNSUITABLE for cross-machine floating-point
research: equivalent scipy/BLAS optimizations can differ in final decimals;
matplotlib PNG bytes may also differ despite identical scientific figures.
Never relax the independent Brier/event/provenance audit in check_results.py.
"""
from __future__ import annotations

import io
import json
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
RESULTS = pathlib.Path(__file__).resolve().parent / "results"
GIT = "research/phase3_2026/results"
THRESHOLDS = (10, 20, 35)
MODELS = ("historical", "gbm", "markov", "ewma", "adaptive_gbm", "garch")
PATHS = 20_000


def published(name: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "show", f"HEAD:{GIT}/{name}"],
            cwd=ROOT, text=True
        )
    except subprocess.CalledProcessError as exc:
        raise AssertionError(f"Committed scientific baseline missing: {name}") from exc


def refreshed(name: str) -> str:
    return (RESULTS / name).read_text(encoding="utf-8")


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def arrays_match(label, expected, observed, *, atol=0, rtol=0):
    expected = np.asarray(expected, dtype=float)
    observed = np.asarray(observed, dtype=float)
    check(expected.shape == observed.shape, f"{label}: different shape")
    check(np.isfinite(expected).all() and np.isfinite(observed).all(),
          f"{label}: non-finite values")
    diff = np.abs(expected - observed)
    if not np.allclose(expected, observed, atol=atol, rtol=rtol):
        index = int(np.argmax(diff))
        raise AssertionError(
            f"{label}: drift beyond tolerance; max absolute={diff.flat[index]:.9g}, "
            f"expected={expected.flat[index]:.12g}, observed={observed.flat[index]:.12g}, "
            f"atol={atol:.2g}, rtol={rtol:.2g}"
        )
    return float(np.max(diff))


def compare_ledger():
    original = pd.read_csv(io.StringIO(published("forecast_ledger_2026.csv")))
    rerun = pd.read_csv(RESULTS / "forecast_ledger_2026.csv")
    check(original.shape == rerun.shape == (274, 30),
          f"Ledger shape changed: committed={original.shape}, rerun={rerun.shape}")
    check(list(original.columns) == list(rerun.columns),
          "Ledger column order/schema changed")
    exact_fields = ["origin", "target", "regime"] + [f"event_{t}" for t in THRESHOLDS]
    for field in exact_fields:
        check(original[field].equals(rerun[field]),
              f"{field}: changed dates, regimes, event outcomes or identifiers")
    # Real BTC prices must not be accepted with any economically meaningful drift.
    for field in ("btc_origin", "btc_target"):
        arrays_match(field, original[field], rerun[field], atol=1e-8)
    arrays_match("realized_return", original["realized_return"],
                 rerun["realized_return"], atol=1e-10)
    arrays_match("rolling30_sigma", original["rolling30_sigma"],
                 rerun["rolling30_sigma"], atol=1e-9)
    arrays_match("ewma_nextvar", original["ewma_nextvar"],
                 rerun["ewma_nextvar"], atol=1e-9)
    max_garch_variance = arrays_match(
        "garch_nextvar_pct2", original["garch_nextvar_pct2"],
        rerun["garch_nextvar_pct2"], atol=1e-4, rtol=5e-5
    )
    max_probability = 0.0
    for t in THRESHOLDS:
        for model in MODELS:
            field = f"{model}_p{t}"
            # Exact analytical/frozen model forecasts and fixed-seed EWMA.
            # GARCH can move by a few Monte Carlo event counts when an
            # optimizer moves the variance state by a few parts per million.
            tolerance = {
                "historical": 1e-10,
                "gbm": 1e-10,
                "markov": 1e-10,
                "ewma": 1.0/PATHS,
                "adaptive_gbm": 1e-8,
                "garch": 4.0/PATHS,
            }[model]
            max_probability = max(max_probability, arrays_match(
                field, original[field], rerun[field], atol=tolerance
            ))
    print(f"PASS: 274 origins, all historical prices/events and six models reproduced; "
          f"max GARCH variance delta={max_garch_variance:.6g}, "
          f"max model probability delta={max_probability:.6g}", flush=True)


def compare_manifest():
    original = json.loads(published("archive_sha256_manifest.json"))
    rerun = json.loads(refreshed("archive_sha256_manifest.json"))
    check(original == rerun,
          "Official Binance archive provenance changed: hashes, archive periods or URL differ")
    check(len(original["archives"]) == 58, "Missing archive source in manifest")
    print("PASS: All 58 source-archive records (URLs, hashes, dates) match exactly", flush=True)


def compare_metrics():
    initial = json.loads(published("metrics_2026.json"))
    recomputed = json.loads(refreshed("metrics_2026.json"))
    check(initial.keys() == recomputed.keys(), "Metrics schema changed")
    fixed_keys = (
        "experiment", "protocol", "not_prospective",
        "no_parameter_tuning_on_2026", "evaluation_start",
        "evaluation_last_origin", "last_actual_close", "origins",
        "model_calibration", "horizon_days", "primary_threshold_pct",
        "secondary_thresholds_pct", "forecast_paths_each_origin",
        "bootstrap", "provenance_manifest", "limitations"
    )
    for field in fixed_keys:
        check(initial[field] == recomputed[field],
              f"Frozen experiment settings changed: {field}")
    fit, new_fit = initial["garch_fit"], recomputed["garch_fit"]
    check(fit.keys() == new_fit.keys(), "Fitted GARCH structure changed")
    for field in ("fit_converged", "n_train", "arch_version"):
        check(fit[field] == new_fit[field], f"GARCH fit provenance changed: {field}")
    for field in ("omega_pct2", "alpha", "beta", "persistence",
                  "calibration_mean_return", "loglikelihood",
                  "fit_next_variance_2025_01_01_pct2"):
        arrays_match("GARCH "+field, [fit[field]], [new_fit[field]],
                     atol=5e-4, rtol=1e-4)
    for threshold in THRESHOLDS:
        t = str(threshold)
        old, new = initial["scores"][t], recomputed["scores"][t]
        for field in ("n", "events"):
            check(old[field] == new[field],
                  f"{t}% observed event count or window count changed")
        arrays_match(f"{t}% actual event frequency", [old["frequency"]],
                     [new["frequency"]], atol=1e-12)
        check(old["models"].keys() == new["models"].keys(),
              f"{t}% model identities changed")
        for model in MODELS:
            for key in ("brier", "mean_probability", "min_probability",
                        "max_probability", "probability_std"):
                arrays_match(f"{t}% {model} {key}",
                             [old["models"][model][key]],
                             [new["models"][model][key]], atol=1e-5)
        check(old["differences"].keys() == new["differences"].keys(),
              f"{t}% paired model comparisons changed")
        for name, record in old["differences"].items():
            fresh = new["differences"][name]
            check(record["bootstrap_block"] == fresh["bootstrap_block"] == 30,
                  f"Changed resampling design: {name}")
            for field in ("mean", "ci95"):
                arrays_match(f"{t}% {name} {field}",
                             np.atleast_1d(record[field]), np.atleast_1d(fresh[field]),
                             atol=1e-5)
            arrays_match(f"{t}% {name} bootstrap p",
                         [record["two_sided_centered_bootstrap_p"]],
                         [fresh["two_sided_centered_bootstrap_p"]], atol=.01)
    check(initial["primary_holm_tests"].keys() ==
          recomputed["primary_holm_tests"].keys(), "Primary hypothesis names changed")
    for name, report in initial["primary_holm_tests"].items():
        fresh = recomputed["primary_holm_tests"][name]
        check(report["claim_supported"] == fresh["claim_supported"] and
              report["interpretation"] == fresh["interpretation"],
              f"Scientific conclusion changed for {name}")
        arrays_match(f"Holm adjusted p for {name}",
                     [report["holm_adjusted_p"]],
                     [fresh["holm_adjusted_p"]], atol=.01)
    old_ranks = sorted(MODELS,
                       key=lambda m: initial["scores"]["10"]["models"][m]["brier"])
    new_ranks = sorted(MODELS,
                       key=lambda m: recomputed["scores"]["10"]["models"][m]["brier"])
    check(old_ranks == new_ranks, "Primary Brier accuracy ranking changed")
    print("PASS: Model fit, all Brier statistics, block-bootstrap results and "
          "primary research claims reproduced within fixed scientific tolerances", flush=True)


def compare_report_and_figures():
    original = published("FINDINGS.md")
    rerun = refreshed("FINDINGS.md")
    headings = (
        "# Frozen 2026 retrospective replication: executed findings",
        "## Terminal-loss forecast Brier scores (lower is better)",
        "## Prespecified primary comparisons (10% event)",
        "## Interpretation and limitations",
    )
    for heading in headings:
        check(heading in original and heading in rerun,
              f"Missing scientific report section {heading}")
    check("No statistically established improvement" in rerun,
          "Unexpected omitted/changed negative finding")
    for fig in ("forecast_probability_timeline.png", "primary_brier_comparison.png"):
        check((RESULTS / fig).stat().st_size >= 10_000,
              f"Plot {fig} empty or missing")
        check(subprocess.run(["git","cat-file","-e",f"HEAD:{GIT}/{fig}"],
                             cwd=ROOT, capture_output=True).returncode == 0,
              f"Published figure {fig} missing")
    print("PASS: Scientific report, negative finding and both graphs preserved", flush=True)


def main():
    compare_manifest()
    compare_ledger()
    compare_metrics()
    compare_report_and_figures()
    print("PASS: Scientific reproducibility verified; harmless floating-point "
          "and PNG byte differences do not invalidate the experiment", flush=True)


if __name__ == "__main__":
    main()
