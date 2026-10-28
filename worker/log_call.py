#!/usr/bin/env python3
"""Append one Ticker Forensics verdict to calls/log.csv in the data repo."""

import csv
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

HEADER = ["date", "ticker", "verdict", "confidence", "price", "entry", "target", "stop"]


def fail(reason):
    print(f"LOG_FAILED {reason}", flush=True)


def cell_text(value):
    """Empty cell for missing values. Never the words None or null, never a fake 0."""
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return ""
    text = str(value).strip()
    if text == "" or text.lower() in {"none", "null", "nan"}:
        return ""
    return text


def cell_price(value):
    text = cell_text(value)
    if text == "":
        return ""
    try:
        number = float(text)
    except ValueError:
        return ""
    if math.isnan(number) or math.isinf(number):
        return ""
    return f"{number:.2f}"


def cell_confidence(value):
    text = cell_text(value)
    if text == "":
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    if math.isnan(number) or math.isinf(number):
        return ""
    if number == int(number):
        return str(int(number))
    return str(number)


def present(mapping, key):
    """A value counts as missing when the key is absent, null, or blank."""
    if not isinstance(mapping, dict) or key not in mapping:
        return None
    value = mapping.get(key)
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def build_row(payload, ticker, day):
    quote = payload.get("quote") if isinstance(payload.get("quote"), dict) else {}
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    exit_plan = analysis.get("exitPlan") if isinstance(analysis.get("exitPlan"), dict) else {}

    # exitPlan wins. Fall back only when that field is missing.
    entry = present(exit_plan, "entry")
    if entry is None:
        entry = present(analysis, "entryPrice")
    target = present(exit_plan, "target")
    if target is None:
        target = present(analysis, "intrinsicValue")
    stop = present(exit_plan, "stop")
    verdict = cell_text(present(analysis, "verdict")).upper()
    # An AVOID call has no buy plan, so "hit target" would read as a win.
    if verdict == "AVOID":
        entry = target = stop = None

    return [
        day,
        ticker,
        verdict,
        cell_confidence(present(analysis, "confidence")),
        cell_price(present(quote, "price")),
        cell_price(entry),
        cell_price(target),
        cell_price(stop),
    ]


def merge_csv(text, new_row):
    """Replace any same-date, same-ticker row, then append the new one."""
    if text is None or text.strip() == "":
        rows = [list(HEADER)]
    else:
        rows = []
        for record in csv.reader(io.StringIO(text)):
            if any(cell.strip() for cell in record):
                rows.append(record)
        if not rows:
            rows = [list(HEADER)]
        elif [cell.strip() for cell in rows[0]] != HEADER:
            raise ValueError("unexpected header in calls/log.csv")
        else:
            kept = [rows[0]]
            for record in rows[1:]:
                row_date = record[0].strip() if record else ""
                row_ticker = record[1].strip().upper() if len(record) > 1 else ""
                if row_date == new_row[0] and row_ticker == new_row[1]:
                    continue
                kept.append(record)
            rows = kept
    rows.append(new_row)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows(rows)
    return buffer.getvalue()


REPO_URL = "https://github.com/qanicuq/ticker-forensics-data"
LOG_PATH = "calls/log.csv"


def git(args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def short_reason(proc, fallback):
    for line in (proc.stderr or proc.stdout or "").splitlines():
        if line.strip():
            return line.strip()[:180]
    return fallback


def once(new_row, ticker):
    """Clone, add the row, commit, push. Returns None, "conflict", or a reason."""
    folder = tempfile.mkdtemp(prefix="calls-")
    try:
        proc = git(["clone", "--depth", "1", REPO_URL, folder])
        if proc.returncode != 0:
            return short_reason(proc, "could not download the data repo")
        path = os.path.join(folder, LOG_PATH)
        text = ""
        if os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        updated = merge_csv(text, new_row)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(updated)
        who = ["-c", "user.name=Ticker Forensics worker", "-c", "user.email=noreply@github.com"]
        git(["add", LOG_PATH], cwd=folder)
        proc = git([*who, "commit", "-m", f"calls: log {ticker} [skip ci]"], cwd=folder)
        if proc.returncode != 0:
            return None if "nothing to commit" in (proc.stdout + proc.stderr) else short_reason(proc, "commit failed")
        proc = git(["push", "origin", "HEAD"], cwd=folder)
        if proc.returncode == 0:
            return None
        text = proc.stdout + proc.stderr
        if "rejected" in text or "fetch first" in text or "non-fast-forward" in text:
            return "conflict"
        return short_reason(proc, "upload failed")
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def main():
    if len(sys.argv) != 3:
        fail("need a FINAL.json path and a ticker")
        return
    path = sys.argv[1]
    ticker = sys.argv[2].strip().upper()
    if not ticker:
        fail("missing ticker")
        return
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as exc:
        fail(f"could not read FINAL.json: {exc}")
        return
    if not isinstance(payload, dict):
        fail("FINAL.json is not an object")
        return
    day = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    new_row = build_row(payload, ticker, day)
    try:
        result = once(new_row, ticker)
        # One retry only, and only when someone else pushed first.
        if result == "conflict":
            result = once(new_row, ticker)
            if result == "conflict":
                result = "upload conflict after one retry"
        if result:
            fail(result)
            return
    except Exception as exc:
        fail(str(exc))
        return
    print(f"LOGGED {ticker}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fail(str(exc))
    sys.exit(0)
