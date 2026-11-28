"""Daily check. Pushes to ntfy only when something changes, plus a Monday summary.
Needs FRED_API_KEY and NTFY_TOPIC environment variables."""
import json
import os
import sys

import pandas as pd
import requests

import signals as sg

STATE = "state.json"
CONFIG = "config.json"
PRIORITY = {0: "3", 1: "3", 2: "4", 3: "5"}
TAGS = {0: "white_check_mark", 1: "eyes", 2: "warning", 3: "rotating_light"}
# Oldest a reading may be before the bot calls it a data problem
MAX_AGE_DAYS = {"DGS10": 7, "DTB3": 7, "DBAA": 7, "ICSA": 14}
MAX_AGE_MONTHS = {"SAHMREALTIME": 2, "PAYEMS": 2}


def today_ny():
    return pd.Timestamp.now(tz="America/New_York").tz_localize(None).normalize()


def describe(r, s, cfg):
    row, on = r.iloc[-1], s.iloc[-1]
    mark = lambda k: "ON " if on[k] else "off"
    return "\n".join([
        f"[{mark('curve')}] Yield curve (10-yr minus 3-mo): {row['curve']:+.2f} pts. Danger: below 0 now or in the last 12 months",
        f"[{mark('credit')}] Credit spread (Baa bonds minus 10-yr): {row['spread']:.2f} pts, up {row['spread_rise']:.2f} from its 12-month low. Danger: up {cfg['spread_x']:.2f}",
        f"[{mark('claims')}] Jobless claims (4-week avg): {row['claims4']:,.0f}, {row['claims_rise']:.0%} above its 52-week low. Danger: {cfg['claims_y']:.0%}",
        f"[{mark('sahm')}] Sahm Rule: {row['sahm']:.2f}. Danger: {sg.SAHM_LINE:.2f}",
        f"[{mark('jobs')}] Jobs, 3-month avg change: {row['jobs3']:+,.0f}. Danger: below 0",
    ])


def stale(raw, today):
    bad = []
    for sid, days in MAX_AGE_DAYS.items():
        last = raw[sid].index[-1]
        if (today - last).days > days:
            bad.append(f"{sid} last {last:%Y-%m-%d}")
    for sid, months in MAX_AGE_MONTHS.items():
        last = raw[sid].index[-1] if sid != "PAYEMS" else raw["PAYEMS_VINTAGES"]["date"].max()
        if (today.year - last.year) * 12 + today.month - last.month > months:
            bad.append(f"{sid} last {last:%Y-%m}")
    return bad


def push(title, body, priority, tags):
    r = requests.post(f"https://ntfy.sh/{os.environ['NTFY_TOPIC']}", data=body.encode("utf-8"),
                      headers={"Title": title, "Priority": priority, "Tags": tags}, timeout=30)
    r.raise_for_status()


def main(force_summary=False):
    import fred
    cfg = json.load(open(CONFIG))
    today = today_ny()
    raw = fred.fetch_all()
    r = sg.readings(raw, today)
    if r.iloc[-1][["curve", "spread"]].isna().any():
        r = r.iloc[:-1]          # first day(s) of a month: no daily rates yet, so judge last month
    s = sg.signals(r, cfg["spread_x"], cfg["claims_y"], cfg["persist"])
    level = int(s["level"].iloc[-1])
    names = ["curve", "credit", "claims", "sahm", "jobs"]
    now = {k: bool(s[k].iloc[-1]) for k in names}
    if r.iloc[-1][["curve", "spread_rise", "claims_rise", "sahm", "jobs3"]].isna().any():
        raise RuntimeError("a reading is missing for this month:\n" + r.iloc[-1].to_string())

    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    text = describe(r, s, cfg)
    sent = []

    if state and (state.get("level") != level or state.get("signals") != now):
        changed = [k for k in names if state.get("signals", {}).get(k) != now[k]]
        push(f"Recession Alert: {sg.LEVELS[level]}",
             f"Changed: {', '.join(changed) or 'level'}\n\n{text}", PRIORITY[level], TAGS[level])
        sent.append("change")

    problems = stale(raw, today)
    if problems and not state.get("data_problem"):
        push("Recession Alert: DATA PROBLEM", "Old data, so the alert may be wrong:\n" + "\n".join(problems), "4", "x")
        sent.append("data problem")
    if not problems and state.get("data_problem"):
        push("Recession Alert: data fixed", "All data is up to date again.", "3", "white_check_mark")
        sent.append("data fixed")

    is_monday = today.dayofweek == 0 and state.get("last_summary") != str(today.date())
    if force_summary or is_monday or not state:
        push(f"Recession Alert weekly: {sg.LEVELS[level]}", text, PRIORITY[min(level, 1)], TAGS[level])
        state["last_summary"] = str(today.date())
        sent.append("summary")

    state.update({"level": level, "signals": now, "data_problem": bool(problems)})
    json.dump(state, open(STATE, "w"), indent=1)
    print(f"{today.date()} level {sg.LEVELS[level]}; pushes sent: {sent or 'none'}\n{text}")


if __name__ == "__main__":
    main(force_summary="--summary" in sys.argv)
