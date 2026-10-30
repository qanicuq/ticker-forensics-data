"""Build paper.json: a snapshot of every paper-trading bot for the Command Center.

Reads only the bots' own public files. No secrets, no network calls except git clone.
Usage: python build_paper.py OUT_PATH [REPOS_DIR]
"""
import csv, json, os, re, subprocess, sys, tempfile
from datetime import datetime, timezone

OWNER = "qanicuq"
REPOS = ["trigger-alerts", "btc-bot", "btc-stoch200-paper", "wheel-bot", "spy-0dte-paper", "qld-50day-paper"]
GH = f"https://github.com/{OWNER}"


def fetch(base):
    for r in REPOS:
        d = os.path.join(base, r)
        if os.path.isdir(d):
            subprocess.run(["git", "-C", d, "pull", "-q", "--depth", "1"], check=True)
        else:
            subprocess.run(["git", "clone", "-q", "--depth", "1", f"{GH}/{r}.git", d], check=True)


def read(base, *p):
    with open(os.path.join(base, *p)) as f:
        return f.read()


def pct(value, start):
    return round((value / start - 1) * 100, 2)


def trigger_alerts(base):
    rep = read(base, "trigger-alerts", "REPORT.md")
    start = float(re.search(r"STARTING_CASH\s*=\s*([\d.]+)", read(base, "trigger-alerts", "common.py")).group(1))
    asof = re.search(r"# Report (\d{4}-\d\d-\d\d \d\d:\d\d)", rep).group(1)
    equity = float(re.search(r"Equity: \$([\d,.]+)", rep).group(1).replace(",", ""))
    pos = [{"t": m.group(1), "pct": float(m.group(2))}
           for m in re.finditer(r"^- (\S+) entry .*? P/L (-?[\d.]+)%", rep, re.M)]
    n = len(pos)
    return {"name": "Trigger Alerts", "value": equity, "start": start, "pct": pct(equity, start),
            "bench": None, "asof": asof + " NY",
            "sub": f"{n} trade{'s' if n != 1 else ''} open" if n else "No open trades",
            "link": f"{GH}/trigger-alerts/blob/main/REPORT.md"}, pos, asof + " NY"


def crypto(base):
    s = json.loads(read(base, "btc-bot", "paperbot", "out", "summary.json"))
    st = json.loads(read(base, "btc-bot", "paperbot", "state.json"))
    eq, start = s["equity"], st["starting_equity"]
    coins = sum(v["units"] * s["prices"][k] for k, v in st["sleeves"].items() if k in s["prices"])
    curve = [round(v, 2) for _, v in st.get("equity_curve", [])][-60:]
    status = "stopped by its safety rule" if s.get("stopped", {}).get("on") else f"{coins / eq:.0%} in coins"
    return {"name": "Crypto Paper Bot", "value": eq, "start": start, "pct": pct(eq, start), "bench": None,
            "asof": s["day"] + " close", "sub": f"BTC + ETH, {status}", "curve": curve,
            "link": f"{GH}/btc-bot/blob/main/paperbot/DASHBOARD.md"}, s


def stoch(base, crypto_summary):
    st = json.loads(read(base, "btc-stoch200-paper", "state.json"))
    price = crypto_summary["prices"]["BTCUSD"]
    start = 10000.0
    value = st["cash"] + st["btc"] * price
    bench = st["benchmark_cash"] + st["benchmark_btc"] * price
    flat = st["position"] == "flat" or st["btc"] == 0
    rows = list(csv.DictReader(open(os.path.join(base, "btc-stoch200-paper", "trades.csv"))))
    last = rows[-1]["time"][:10] if rows else "none yet"
    sub = ("All cash, waiting for a buy signal" if flat else "Holding BTC") + f" · last trade {last}"
    return {"name": "BTC Stoch200", "value": round(value, 2), "start": start, "pct": pct(value, start),
            "bench": pct(bench, start), "benchLabel": "holding BTC",
            "asof": f"BTC price at {crypto_summary['day']} close",
            "sub": sub, "link": f"{GH}/btc-stoch200-paper/blob/main/trades.csv"}


def wheel(base):
    md = read(base, "wheel-bot", "STATUS.md")
    asof = re.search(r"Updated (\d{4}-\d\d-\d\d)", md).group(1)
    rows = {m.group(1): (float(m.group(2).replace(",", "")), float(m.group(3)))
            for m in re.finditer(r"^\| ([\w ()]+?) \| \$([\d,.]+) \| (-?[\d.]+)% \|", md, re.M)}
    spy = next((v for k, v in rows.items() if k.startswith("hold SPY")), None)
    out = []
    for book, label in [("wheel_only", "Wheel Bot: wheel only"), ("core_wheel", "Wheel Bot: SPY core + wheel")]:
        if book not in rows:
            continue
        value, ret = rows[book]
        opts = len(re.findall(rf"^- {book} / \w+: .*short (put|call)", md, re.M))
        sub = f"{opts} option{'s' if opts != 1 else ''} sold, open" if opts else "No options open"
        if book == "core_wheel":
            sub = "Holds SPY shares · " + sub
        out.append({"name": label, "value": value, "start": round(value / (1 + ret / 100), -3), "pct": ret,
                    "bench": spy[1] if spy else None, "benchLabel": "holding SPY", "asof": asof,
                    "sub": sub, "link": f"{GH}/wheel-bot/blob/main/STATUS.md"})
    return out


def spy0dte(base):
    start = float(re.search(r"START_BALANCE[^=]*=\s*([\d.]+)", read(base, "spy-0dte-paper", "bot.py")).group(1))
    rows = list(csv.DictReader(open(os.path.join(base, "spy-0dte-paper", "trades.csv"))))
    bal = float(rows[-1]["balance"]) if rows else start
    traded = [r for r in rows if r.get("contracts") not in ("", "0", "0.0", None)]
    if rows:
        r = rows[-1]
        res = float(r["result"] or 0)
        sign = "+" if res > 0 else "−" if res < 0 else ""
        last = f"{r['date']}: {r['exit_reason'] or 'no trade'} ({sign}${abs(res):,.0f})"
    else:
        last = "no trades yet"
    n = len(traded)
    return {"name": "SPY 0DTE", "value": bal, "start": start, "pct": pct(bal, start), "bench": None,
            "asof": rows[-1]["date"] if rows else "", "sub": f"{n} trade{'s' if n != 1 else ''} · last {last}",
            "link": f"{GH}/spy-0dte-paper/blob/main/trades.csv"}


def qld50(base):
    start = 10000.0
    link = f"{GH}/qld-50day-paper/blob/main/trades.csv"
    eq_path = os.path.join(base, "qld-50day-paper", "equity.csv")
    if not os.path.exists(eq_path):
        return {"name": "QLD 50-day", "value": start, "start": start, "pct": 0.0, "bench": None,
                "asof": "not started", "sub": "Waiting for its first run after a market close", "link": link}
    rows = list(csv.DictReader(open(eq_path)))
    st = json.loads(read(base, "qld-50day-paper", "state.json"))
    value = float(rows[-1]["account_value"])
    bench = pct(float(rows[-1]["qld_close"]), float(rows[0]["qld_close"]))
    side = "Holding QLD" if st["holding"] else "All cash"
    if st.get("pending"):
        side += f" · {st['pending'].lower()} at next open"
    curve = [float(r["account_value"]) for r in rows][-60:]
    return {"name": "QLD 50-day", "value": value, "start": start, "pct": pct(value, start),
            "bench": bench, "benchLabel": "holding QLD", "asof": rows[-1]["date"] + " close",
            "sub": side, "curve": curve, "link": link}


def main():
    out = sys.argv[1]
    base = sys.argv[2] if len(sys.argv) > 2 else tempfile.mkdtemp()
    fetch(base)
    accounts, errors, positions, pos_asof = [], [], [], None
    try:
        ta, positions, pos_asof = trigger_alerts(base); accounts.append(ta)
    except Exception as e: errors.append(f"Trigger Alerts: {e}")
    cs = None
    try:
        c, cs = crypto(base); accounts.append(c)
    except Exception as e: errors.append(f"Crypto Paper Bot: {e}")
    try:
        if cs is None: raise RuntimeError("needs the crypto bot's BTC price")
        accounts.append(stoch(base, cs))
    except Exception as e: errors.append(f"BTC Stoch200: {e}")
    try: accounts.extend(wheel(base))
    except Exception as e: errors.append(f"Wheel Bot: {e}")
    try: accounts.append(spy0dte(base))
    except Exception as e: errors.append(f"SPY 0DTE: {e}")
    try: accounts.append(qld50(base))
    except Exception as e: errors.append(f"QLD 50-day: {e}")
    data = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "accounts": accounts, "positions": positions, "positions_asof": pos_asof, "errors": errors}
    with open(out, "w") as f:
        json.dump(data, f, indent=1)
    print(json.dumps(data, indent=1))


if __name__ == "__main__":
    main()
