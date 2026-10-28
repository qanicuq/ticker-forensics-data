#!/usr/bin/env python3
"""Score past Ticker Forensics calls against later prices and against SPY."""

import math
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

LOG_PATH = "calls/log.csv"
OUT_PATH = "calls/scorecard.md"
HORIZONS = (30, 90, 180)
VERDICT_ORDER = ("BUY", "WATCH", "AVOID")
HIT_RESULTS = ("hit target", "hit stop", "neither yet")


def ny_today():
    return datetime.now(ZoneInfo("America/New_York")).date()


def write_none():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        handle.write("No calls logged yet.\n")


def number_or_none(value):
    """Blank stays blank. A blank is not zero."""
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def parse_date(value):
    text = str(value).strip()
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def pct(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{value * 100:.1f}%"


def price_text(value):
    if value is None:
        return "—"
    return f"{value:.2f}"


def plain(value):
    if value is None:
        return "—"
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return "—"
    return text


def mean(values):
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


def closes_from_download(frame):
    if frame is None or len(frame) == 0:
        return None
    columns = frame.columns
    if isinstance(columns, pd.MultiIndex):
        series = None
        for level in range(columns.nlevels):
            if "Close" in columns.get_level_values(level):
                series = frame.xs("Close", axis=1, level=level)
                break
        if series is None:
            return None
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]
    else:
        if "Close" not in frame.columns:
            return None
        series = frame["Close"]
    series = pd.to_numeric(series, errors="coerce").dropna()
    if series.empty:
        return None
    index = pd.to_datetime(series.index)
    if getattr(index, "tz", None) is not None:
        index = index.tz_localize(None)
    series = series.copy()
    series.index = pd.DatetimeIndex(index).normalize()
    series = series[~series.index.duplicated(keep="last")].sort_index()
    if series.empty:
        return None
    return series


def download_closes(ticker, start):
    try:
        frame = yf.download(ticker, start=start, auto_adjust=True, progress=False)
    except Exception:
        return None
    return closes_from_download(frame)


def first_bar(series, day, after):
    """First close after `day` (start price) or on/after `day` (a later check)."""
    if series is None or series.empty:
        return None, None
    stamp = pd.Timestamp(day)
    picked = series[series.index > stamp] if after else series[series.index >= stamp]
    if picked.empty:
        return None, None
    return picked.index[0], float(picked.iloc[0])


def period_return(series, call_date, days, start_price):
    if series is None or start_price is None or start_price == 0:
        return None
    horizon = call_date + timedelta(days=days)
    _when, end_price = first_bar(series, horizon, after=False)
    if end_price is None or end_price == 0:
        return None
    return end_price / start_price - 1.0


def path_result(series, start_day, target, stop):
    # Checked before prices on purpose: a blank target or stop is n/a, not zero.
    if target is None or stop is None:
        return "n/a"
    if series is None or start_day is None:
        return "no price data"
    later = series[series.index > pd.Timestamp(start_day)]
    for close in later:
        price = float(close)
        at_target = price >= target
        at_stop = price <= stop
        # One close can clear both only when target is at or below the stop.
        # The steps don't say which wins; target is checked first.
        if at_target:
            return "hit target"
        if at_stop:
            return "hit stop"
    return "neither yet"


def show_return(kind, value):
    if kind == "no price data":
        return "no price data"
    if value is None:
        return "not yet"
    return pct(value)


def grade(verdict, vs90):
    name = (verdict or "").strip().upper()
    if name == "WATCH" or name not in ("BUY", "AVOID"):
        return "n/a"
    if vs90 is None:
        return "—"
    if name == "BUY":
        return "yes" if vs90 > 0 else "no"
    return "yes" if vs90 < 0 else "no"


def md_table(headers, rows):
    head = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join([head, rule, *body])


def load_calls():
    if not os.path.exists(LOG_PATH):
        return None
    try:
        frame = pd.read_csv(LOG_PATH, dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError:
        return None
    if frame.empty:
        return None
    frame.columns = [str(column).strip() for column in frame.columns]
    needed = {"date", "ticker", "verdict", "confidence", "price", "entry", "target", "stop"}
    missing = needed.difference(frame.columns)
    if missing:
        raise SystemExit(f"calls/log.csv is missing columns: {', '.join(sorted(missing))}")
    return frame


def build_results(frame):
    parsed = []
    for raw in frame.to_dict("records"):
        parsed.append(
            {
                "date": parse_date(raw.get("date", "")),
                "date_text": str(raw.get("date", "")).strip(),
                "ticker": str(raw.get("ticker", "")).strip().upper(),
                "verdict": str(raw.get("verdict", "")).strip().upper(),
                "confidence": str(raw.get("confidence", "")).strip(),
                "target": number_or_none(raw.get("target")),
                "stop": number_or_none(raw.get("stop")),
            }
        )
    dates = [row["date"] for row in parsed if row["date"] is not None]
    if not dates:
        results = []
        for row in parsed:
            results.append(
                {
                    **row,
                    "kind": "no price data",
                    "start": None,
                    "rets": {days: None for days in HORIZONS},
                    "spy_rets": {days: None for days in HORIZONS},
                    "vs90": None,
                    "path": "n/a" if row["target"] is None or row["stop"] is None else "no price data",
                    "right": grade(row["verdict"], None),
                }
            )
        return results
    start = (min(dates) - timedelta(days=5)).isoformat()
    cache = {}

    def closes(ticker):
        if ticker not in cache:
            cache[ticker] = download_closes(ticker, start)
        return cache[ticker]

    # SPY once, even if nobody called the ticker SPY.
    closes("SPY")
    for row in parsed:
        if row["ticker"]:
            closes(row["ticker"])

    spy = cache.get("SPY")
    if spy is None:
        # Fail loudly so the workflow sends the ntfy alert instead of committing a blank card.
        raise SystemExit("Could not download SPY prices from Yahoo Finance.")
    results = []
    for row in parsed:
        series = cache.get(row["ticker"]) if row["ticker"] else None
        call_date = row["date"]
        if series is None or call_date is None:
            kind = "no price data"
            start_day = None
            start_price = None
        else:
            start_ts, start_price = first_bar(series, call_date, after=True)
            if start_price is None:
                kind = "waiting"
                start_day = None
            else:
                kind = "ok"
                start_day = start_ts.date()
        rets = {}
        spy_rets = {}
        for days in HORIZONS:
            if kind == "no price data":
                rets[days] = None
                spy_rets[days] = None
            else:
                rets[days] = period_return(series, call_date, days, start_price)
                spy_rets[days] = period_return(spy, call_date, days, first_bar(spy, call_date, after=True)[1] if spy is not None else None)
        vs90 = None
        if rets[90] is not None and spy_rets[90] is not None:
            vs90 = rets[90] - spy_rets[90]
        if row["target"] is None or row["stop"] is None:
            path = "n/a"
        elif kind == "no price data":
            path = "no price data"
        elif start_day is None:
            path = "not yet"
        else:
            path = path_result(series, start_day, row["target"], row["stop"])
        results.append(
            {
                **row,
                "kind": kind,
                "start": start_price,
                "rets": rets,
                "spy_rets": spy_rets,
                "vs90": vs90,
                "path": path,
                "right": grade(row["verdict"], vs90),
            }
        )
    return results


def count_sentence(results):
    scored = sum(1 for row in results if row["rets"][90] is not None)
    if scored == 1:
        sentence = "1 call has 90-day results."
    else:
        sentence = f"{scored} calls have 90-day results."
    if scored < 10:
        sentence += " Too early to judge — need at least 10 calls with 90-day results."
    return sentence


def hit_percents(rows):
    pool = [row for row in rows if row["path"] in HIT_RESULTS]
    if not pool:
        return "—", "—"
    hits = sum(1 for row in pool if row["path"] == "hit target")
    stops = sum(1 for row in pool if row["path"] == "hit stop")
    return pct(hits / len(pool)), pct(stops / len(pool))


def right_percent(rows):
    graded = [row for row in rows if row["verdict"] in ("BUY", "AVOID") and row["vs90"] is not None]
    if not graded:
        return "—"
    correct = sum(1 for row in graded if row["right"] == "yes")
    return pct(correct / len(graded))


def verdict_table(results):
    headers = [
        "Verdict",
        "calls",
        "scored at 90 days",
        "average 90-day return",
        "average SPY 90-day return",
        "average vs SPY",
        "% right",
        "% hit target",
        "% hit stop",
    ]
    body = []
    for verdict in VERDICT_ORDER:
        rows = [row for row in results if row["verdict"] == verdict]
        scored = [row for row in rows if row["rets"][90] is not None]
        hit_target, hit_stop = hit_percents(rows)
        right = "n/a" if verdict == "WATCH" else right_percent(rows)
        body.append(
            [
                verdict,
                len(rows),
                len(scored),
                pct(mean([row["rets"][90] for row in scored])),
                pct(mean([row["spy_rets"][90] for row in scored if row["spy_rets"][90] is not None])),
                pct(mean([row["vs90"] for row in scored if row["vs90"] is not None])),
                right,
                hit_target,
                hit_stop,
            ]
        )
    return md_table(headers, body)


def month_table(results):
    headers = [
        "Month",
        "calls",
        "average 90-day return",
        "average SPY 90-day return",
        "average vs SPY",
        "% right (BUY and AVOID only)",
    ]
    months = sorted({row["date"].strftime("%Y-%m") for row in results if row["date"] is not None})
    body = []
    for month in months:
        rows = [row for row in results if row["date"] is not None and row["date"].strftime("%Y-%m") == month]
        scored = [row for row in rows if row["rets"][90] is not None]
        body.append(
            [
                month,
                len(rows),
                pct(mean([row["rets"][90] for row in scored])),
                pct(mean([row["spy_rets"][90] for row in scored if row["spy_rets"][90] is not None])),
                pct(mean([row["vs90"] for row in scored if row["vs90"] is not None])),
                right_percent(rows),
            ]
        )
    return md_table(headers, body)


def call_table(results):
    headers = [
        "date",
        "ticker",
        "verdict",
        "confidence",
        "start price",
        "30-day",
        "90-day",
        "180-day",
        "vs SPY (90-day)",
        "target/stop result",
        "right?",
    ]
    ordered = sorted(results, key=lambda row: row["date"].isoformat() if row["date"] else "", reverse=True)
    body = []
    for row in ordered:
        if row["kind"] == "no price data":
            vs_text = "no price data"
        elif row["vs90"] is None:
            # Stock result not in yet, or SPY's matching result is missing.
            vs_text = "not yet" if row["rets"][90] is None else "—"
        else:
            vs_text = pct(row["vs90"])
        body.append(
            [
                row["date_text"] or "—",
                plain(row["ticker"]),
                plain(row["verdict"]),
                plain(row["confidence"]),
                "no price data" if row["kind"] == "no price data" else ("not yet" if row["start"] is None else price_text(row["start"])),
                show_return(row["kind"], row["rets"][30]),
                show_return(row["kind"], row["rets"][90]),
                show_return(row["kind"], row["rets"][180]),
                vs_text,
                row["path"],
                row["right"],
            ]
        )
    return md_table(headers, body)


def render(results):
    lines = [
        "# Ticker Forensics — Past Calls Report Card",
        f"Made {ny_today().isoformat()}.",
        "",
        count_sentence(results),
        "",
        "## By verdict",
        verdict_table(results),
        "",
        "## Month by month",
        month_table(results),
        "",
        "## Every call",
        call_table(results),
        "",
    ]
    return "\n".join(lines)


def main():
    frame = load_calls()
    if frame is None:
        write_none()
        return
    results = build_results(frame)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        handle.write(render(results))


if __name__ == "__main__":
    main()
