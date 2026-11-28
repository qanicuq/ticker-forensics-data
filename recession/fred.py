"""Download data from FRED (St. Louis Fed). Needs the FRED_API_KEY environment variable."""
import os
import time

import pandas as pd
import requests

API = "https://api.stlouisfed.org/fred/series/observations"


def _get(params):
    params = {**params, "api_key": os.environ["FRED_API_KEY"], "file_type": "json"}
    for attempt in range(3):
        try:
            r = requests.get(API, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))


def series(series_id):
    """Latest (revised) values of one series, as a pandas Series indexed by date."""
    obs = _get({"series_id": series_id})["observations"]
    s = pd.Series(
        {pd.Timestamp(o["date"]): float(o["value"]) for o in obs if o["value"] not in (".", "")},
        name=series_id,
    ).sort_index()
    if s.empty:
        raise RuntimeError(f"{series_id}: FRED returned no data")
    return s


def vintages(series_id):
    """Every value a series has ever shown (ALFRED). Columns: date, rs, re, value.
    rs/re = first and last day that value was the published one."""
    rows, offset = [], 0
    while True:
        obs = _get({"series_id": series_id, "realtime_start": "1776-07-04",
                    "realtime_end": "9999-12-31", "limit": 100000, "offset": offset})["observations"]
        rows += obs
        if len(obs) < 100000:
            break
        offset += 100000
    df = pd.DataFrame(rows)
    df = df[~df["value"].isin([".", ""])].copy()
    df["date"] = pd.to_datetime(df["date"])
    df["rs"] = pd.to_datetime(df["realtime_start"])
    df["re"] = pd.to_datetime(df["realtime_end"].replace("9999-12-31", "2200-01-01"))
    df["value"] = df["value"].astype(float)
    if df.empty:
        raise RuntimeError(f"{series_id}: ALFRED returned no data")
    return df[["date", "rs", "re", "value"]].reset_index(drop=True)


def fetch_all(with_recessions=False):
    raw = {sid: series(sid) for sid in
           ["GS10", "TB3MS", "BAA", "DGS10", "DTB3", "DBAA", "ICSA", "SAHMREALTIME"]}
    raw["PAYEMS_VINTAGES"] = vintages("PAYEMS")
    if with_recessions:
        raw["USREC"] = series("USREC")
    return raw
