"""History test. Picks the two danger lines on OLDER years only (1968-1999),
then judges them on NEWER years (2000-today) that were not used to pick them."""
import itertools
import json
import sys

import pandas as pd

import signals as sg

TRAIN = ("1968-01-01", "1999-12-01")
TEST_START = "2000-01-01"
SPREAD_X = [0.50, 0.75, 1.00]          # credit spread rise above its 12-month low (percentage points)
CLAIMS_Y = [0.15, 0.20, 0.25, 0.30]    # claims 4-week average this far above its 52-week low
PERSIST = [1, 2]                       # months a signal must last
LOOKAHEAD = 24                         # an early warning counts if a recession starts within 24 months


def recession_starts(usrec):
    return [d for d, prev in zip(usrec.index[1:], usrec.values[:-1]) if prev == 0 and usrec[d] == 1]


def episodes(flag):
    """(start, end) of every run of True months."""
    out, start = [], None
    for d, v in flag.items():
        if v and start is None:
            start = d
        if not v and start is not None:
            out.append((start, prev)); start = None
        prev = d
    if start is not None:
        out.append((start, prev))
    return out


def months_between(a, b):
    return (b.year - a.year) * 12 + b.month - a.month


def judge(on, usrec, lo, hi, kind):
    """kind 'early': warning should come 1-24 months BEFORE a recession starts.
       kind 'here':  should come between 3 months before and 6 months after the start."""
    on = on[(on.index >= lo) & (on.index <= hi)]
    last_known = usrec.index[-1]
    starts = [s for s in recession_starts(usrec) if lo <= s <= hi]
    res = {"recessions": [], "false_alarms": [], "too_early_to_judge": []}
    for s in starts:
        win = on[(on.index >= s - pd.DateOffset(months=LOOKAHEAD if kind == "early" else 3))
                 & (on.index <= (s - pd.DateOffset(months=1) if kind == "early" else s + pd.DateOffset(months=6)))]
        first = win[win].index.min() if win.any() else None
        res["recessions"].append({
            "start": s.strftime("%Y-%m"),
            "caught": first is not None,
            "months_before_start": months_between(first, s) if first is not None else None})
    for a, b in episodes(on):
        if usrec.get(a, 0) == 1:
            continue                                   # started inside a recession
        if kind == "early":
            ok = any(0 <= months_between(a, s) <= LOOKAHEAD for s in recession_starts(usrec))
            undecided = months_between(a, last_known) < LOOKAHEAD
        else:
            near = usrec[(usrec.index >= a - pd.DateOffset(months=12)) & (usrec.index <= a + pd.DateOffset(months=12))]
            ok = bool((near == 1).any())
            undecided = months_between(a, last_known) < 12
        item = {"from": a.strftime("%Y-%m"), "to": b.strftime("%Y-%m"), "months": months_between(a, b) + 1}
        if not ok:
            res["too_early_to_judge" if undecided else "false_alarms"].append(item)
    res["caught"] = sum(r["caught"] for r in res["recessions"])
    res["false_count"] = len(res["false_alarms"])
    res["false_months"] = sum(f["months"] for f in res["false_alarms"])
    return res


def score(j):
    return (j["caught"] - j["false_count"], -j["false_months"], j["caught"])


def run(raw, as_of):
    usrec = raw["USREC"]
    last_month = min(usrec.index[-1], pd.Timestamp(as_of).normalize().replace(day=1))
    usrec = usrec[usrec.index <= last_month]
    r = sg.readings(raw, as_of)
    r = r[r.index <= last_month]
    test = (pd.Timestamp(TEST_START), last_month)
    train = (pd.Timestamp(TRAIN[0]), pd.Timestamp(TRAIN[1]))

    grid = []
    for x, y, p in itertools.product(SPREAD_X, CLAIMS_Y, PERSIST):
        s = sg.signals(r, x, y, p)
        grid.append({"spread_x": x, "claims_y": y, "persist": p, "s": s,
                     "train": judge(s["level"] >= 2, usrec, *train, "early"),
                     "test": judge(s["level"] >= 2, usrec, *test, "early")})
    best = max(grid, key=lambda g: score(g["train"]))
    s = best["s"]

    base = sg.signals(r, best["spread_x"], best["claims_y"], 1)["curve"]   # baseline: yield curve alone
    out = {
        "as_of": str(pd.Timestamp(as_of).date()),
        "data_through": last_month.strftime("%Y-%m"),
        "versions_tried": len(grid),
        "chosen": {"spread_x": best["spread_x"], "claims_y": best["claims_y"], "persist": best["persist"]},
        "payroll_real_time_from": raw["PAYEMS_VINTAGES"]["rs"].min().strftime("%Y-%m-%d"),
        "train": {"warning": best["train"],
                  "watch": judge(s["level"] >= 1, usrec, *train, "early"),
                  "recession_signal": judge(s["level"] == 3, usrec, *train, "here"),
                  "baseline_curve_only": judge(base, usrec, *train, "early")},
        "test": {"warning": best["test"],
                 "watch": judge(s["level"] >= 1, usrec, *test, "early"),
                 "recession_signal": judge(s["level"] == 3, usrec, *test, "here"),
                 "baseline_curve_only": judge(base, usrec, *test, "early")},
        "all_versions_on_test": [
            {"spread_x": g["spread_x"], "claims_y": g["claims_y"], "persist": g["persist"],
             "train_caught": g["train"]["caught"], "train_false": g["train"]["false_count"],
             "test_caught": g["test"]["caught"], "test_false": g["test"]["false_count"],
             "test_undecided": len(g["test"]["too_early_to_judge"])} for g in grid],
    }
    on = s[["curve", "credit", "claims", "sahm", "jobs"]].add_suffix("_on")
    monthly = r.join(on).join(s["level"]).join(usrec.rename("in_recession"))
    monthly.index.name = "month"
    return out, monthly


def write_report(out, monthly):
    def line(j):
        hits = ", ".join(f"{x['start']} ({x['months_before_start']} mo early)" if x["caught"] and x["months_before_start"] is not None
                         else f"{x['start']} (MISSED)" for x in j["recessions"]) or "none"
        fa = ", ".join(f"{f['from']} to {f['to']}" for f in j["false_alarms"]) or "none"
        und = ", ".join(f"{f['from']} to {f['to']}" for f in j["too_early_to_judge"]) or "none"
        return f"- Recessions: {hits}\n- False alarms ({j['false_count']}): {fa}\n- Too early to judge: {und}\n"

    def here_line(j):
        hits = ", ".join(f"{x['start']} (" + (f"{-x['months_before_start']} mo after start" if x["months_before_start"] < 0
                         else f"{x['months_before_start']} mo before start") + ")" if x["caught"] else f"{x['start']} (MISSED)"
                         for x in j["recessions"]) or "none"
        fa = ", ".join(f"{f['from']} to {f['to']}" for f in j["false_alarms"]) or "none"
        return f"- Recessions: {hits}\n- False alarms ({j['false_count']}): {fa}\n"

    c = out["chosen"]
    md = [f"# Recession Alert history test\n\nRun {out['as_of']}, data through {out['data_through']}. "
          f"Settings picked on {TRAIN[0][:4]}-{TRAIN[1][:4]} only; judged on {TEST_START[:4]}-{out['data_through'][:4]}.\n",
          f"**Chosen settings:** credit spread up {c['spread_x']:.2f} pts from its 12-month low; "
          f"jobless claims {c['claims_y']:.0%} above their 52-week low; signal must last {c['persist']} month(s).\n",
          f"**Versions tried:** {out['versions_tried']}. Real-time payroll data starts {out['payroll_real_time_from']}.\n"]
    for name, key in [("NEWER years (the real test)", "test"), ("OLDER years (used to pick settings)", "train")]:
        t = out[key]
        md += [f"\n## {name}\n", "\n### WARNING (2+ early signals)\n", line(t["warning"]),
               "\n### Baseline: yield curve alone\n", line(t["baseline_curve_only"]),
               "\n### WATCH (1+ early signal)\n", line(t["watch"]),
               "\n### RECESSION SIGNAL (Sahm Rule or falling jobs)\n", here_line(t["recession_signal"])]
    md.append("\n## All versions on the newer years\n\n| spread | claims | months | old caught | old false | new caught | new false | new undecided |\n|---|---|---|---|---|---|---|---|\n")
    for g in out["all_versions_on_test"]:
        md.append(f"| {g['spread_x']:.2f} | {g['claims_y']:.0%} | {g['persist']} | {g['train_caught']} | {g['train_false']} | "
                  f"{g['test_caught']} | {g['test_false']} | {g['test_undecided']} |\n")
    md.append("\n## Every change of alert level since 2000\n\n| month | level | in recession |\n|---|---|---|\n")
    m = monthly[monthly.index >= TEST_START]
    prev = None
    for d, row in m.iterrows():
        if row["level"] != prev:
            md.append(f"| {d:%Y-%m} | {sg.LEVELS[int(row['level'])]} | {'yes' if row['in_recession'] == 1 else 'no'} |\n")
            prev = row["level"]
    return "".join(md)


if __name__ == "__main__":
    import fred
    as_of = sys.argv[1] if len(sys.argv) > 1 else pd.Timestamp.today().strftime("%Y-%m-%d")
    raw = fred.fetch_all(with_recessions=True)
    out, monthly = run(raw, as_of)
    import os
    os.makedirs("results", exist_ok=True)
    with open("results/backtest.json", "w") as f:
        json.dump(out, f, indent=1)
    monthly.round(4).to_csv("results/monthly.csv")
    with open("results/RESULTS.md", "w") as f:
        f.write(write_report(out, monthly))
    print(json.dumps({k: out[k] for k in ["data_through", "chosen", "versions_tried", "payroll_real_time_from"]}, indent=1))
