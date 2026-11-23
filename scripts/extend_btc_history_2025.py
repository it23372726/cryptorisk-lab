"""Extend bundled BTC/USDT chart history with VERIFIED Binance spot 1D OHLCV candles.

Reads official monthly ZIP/CSV archives from data.binance.vision.
2025 spot archive timestamps use MICROSECONDS (Binance public-data docs).
The original pre-origin December 2024 OHLCV and the research forecast origin
are retained exactly. This script NEVER modifies the scientific notebook.

Outputs:
  docs/btc-historical.json
  docs/v2-history.js (for standalone file:// operation)
  docs/btc-2025-sources.json (per-archive SHA-256 provenance)

Usage: python scripts/extend_btc_history_2025.py
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import pathlib
import time
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BASE = "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1d"
FIRST = dt.date(2024, 12, 1)
ORIGIN = dt.date(2024, 12, 31)
END = dt.date(2025, 12, 31)


def fetch_verified_archive(month: int):
    month_id = f"2025-{month:02d}"
    url = f"{BASE}/BTCUSDT-1d-{month_id}.zip"
    last_error = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "CryptoRiskLabResearch/2.0"}
            )
            with urllib.request.urlopen(req, timeout=45) as response:
                payload = response.read()
            if not payload.startswith(b"PK"):
                raise ValueError(f"Not a ZIP archive: {url}")
            sha = hashlib.sha256(payload).hexdigest()
            with zipfile.ZipFile(io.BytesIO(payload)) as zf:
                names = [name for name in zf.namelist() if name.endswith(".csv")]
                if len(names) != 1:
                    raise ValueError(f"Unexpected ZIP CSV entries: {names}")
                csv_text = zf.read(names[0]).decode("utf-8-sig")
            records = []
            for row in csv.reader(io.StringIO(csv_text)):
                if not row or not row[0].isdigit():
                    continue
                if len(row) < 6:
                    raise ValueError(f"Malformed kline row for {month_id}")
                raw_time = int(row[0])
                # January 2025 onward spot archive timestamps are microseconds.
                if raw_time < 10**15:
                    raise ValueError(f"Expected microseconds, got {raw_time}")
                date = dt.datetime.fromtimestamp(
                    raw_time / 1_000_000, dt.timezone.utc
                ).date()
                if date.strftime("%Y-%m") != month_id:
                    raise ValueError(f"Unexpected UTC date {date} in {month_id}")
                candle = {
                    "date": date.isoformat(),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                }
                validate_candle(candle)
                records.append(candle)
            expected = (
                dt.date(2026, 1, 1) - dt.date(2025, 12, 1)
            ).days if month == 12 else (
                dt.date(2025, month + 1, 1) - dt.date(2025, month, 1)
            ).days
            if len(records) != expected:
                raise ValueError(
                    f"{month_id}: expected {expected} daily candles, got {len(records)}"
                )
            return records, {"month": month_id, "url": url, "sha256": sha, "candles": len(records)}
        except Exception as exc:
            last_error = exc
            if attempt != 2:
                time.sleep(2 + attempt * 2)
    raise RuntimeError(f"Could not verify Binance {month_id} archive: {last_error}") from last_error


def validate_candle(c):
    v = [c[k] for k in ("open", "high", "low", "close", "volume")]
    if not all(isinstance(x, (int, float)) and 0 < x < 1e9 for x in v):
        raise ValueError(f"Invalid/unsafe OHLCV row {c}")
    if not (c["low"] <= min(c["open"], c["close"]) and
            max(c["open"], c["close"]) <= c["high"]):
        raise ValueError(f"Invalid OHLC ordering: {c}")


def build():
    old = json.loads((DOCS / "btc-historical.json").read_text(encoding="utf-8"))
    original = {r["date"]: r for r in old["candles"]}
    origin_row = original.get("2024-12-31")
    if not origin_row or abs(origin_row["close"] - 93576) > 0.001:
        raise ValueError("Frozen notebook forecast origin mismatch")
    december = [
        original[(dt.date(2024, 12, 1) + dt.timedelta(days=i)).isoformat()]
        for i in range(31)
    ]
    observed_2025 = []
    archive_meta = []
    for month in range(1, 13):
        records, source = fetch_verified_archive(month)
        archive_meta.append(source)
        observed_2025.extend(records)
        print(f"Verified {source['month']}: {len(records)} candles; SHA-256 {source['sha256'][:12]}", flush=True)

    # Sanity-check that the official archive matches existing January API OHLC.
    for record in observed_2025[:31]:
        previous = original.get(record["date"])
        if not previous:
            raise ValueError(f"Existing January observation absent: {record['date']}")
        for key in ("open", "high", "low", "close"):
            if abs(previous[key] - record[key]) > .011:
                raise ValueError(
                    f"Existing historical dataset contradicts Binance monthly archive "
                    f"{record['date']} {key}: old={previous[key]}, archive={record[key]}"
                )
    complete = december + observed_2025
    expected_days = (END - FIRST).days + 1
    if len(complete) != expected_days or len(observed_2025) != 365:
        raise ValueError(f"Full-year length error: {len(complete)}")
    for offset, candle in enumerate(complete):
        if candle["date"] != (FIRST + dt.timedelta(days=offset)).isoformat():
            raise ValueError(f"Gap, duplicate or misordered daily data at {candle['date']}")
        validate_candle(candle)
    if complete[30]["date"] != ORIGIN.isoformat() or complete[30]["close"] != 93576:
        raise ValueError("Frozen forecast origin moved")

    history = {
        "source": "Binance spot BTCUSDT 1d UTC OHLCV; December 2024 previously verified API candles, Jan-Dec 2025 verified monthly public CSV archives; observed market prices, not simulated",
        "retrieved": dt.datetime.now(dt.timezone.utc).date().isoformat(),
        "period": "2024-12-01 to 2025-12-31",
        "forecast_origin": ORIGIN.isoformat(),
        "candles": complete,
    }
    source_manifest = {
        "dataset": "Binance spot BTCUSDT, 1d UTC",
        "range": history["period"],
        "forecast_origin": history["forecast_origin"],
        "count": len(complete),
        "timestamp_unit_2025": "microseconds",
        "archives": archive_meta,
        "notes": "The 2024-12-31 forecast origin is fixed. These 2025 observations are retrospective only and must not enter simulation calibration or initial states.",
    }

    output = DOCS / "btc-historical.json"
    output.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    (DOCS / "v2-history.js").write_text(
        "/* Verifiable observed Binance BTC/USDT UTC 1D OHLCV; 2024-12-01 to 2025-12-31. */\n"
        "window.CRL_HISTORY = " + json.dumps(history, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    (DOCS / "btc-2025-sources.json").write_text(
        json.dumps(source_manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"PASS: {len(complete)} continuous authentic daily candles, "
        "2024-12-01 to 2025-12-31, frozen 93576 origin preserved",
        flush=True,
    )


if __name__ == "__main__":
    build()
