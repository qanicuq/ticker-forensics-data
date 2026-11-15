"""Honest forward test of the Diamond Finder ranking (SKILL.md section 11, "Testing a screen honestly").

Why forward and not a historical back-test: free price data leaves out delisted and bankrupt
companies, which makes "buy the cheap ones" screens look far better than they were (Chan).
Paper-trading forward has no such bias and uses only what was known on each date.

How it works:
- On the first run of each month, it "buys" two equal-weight paper baskets of 20 stocks
  (SKILL.md section 10: 20-30 for mechanical cheap-stock baskets) at that run's last close:
  the top 20 by the NEW ranking and the top 20 by the OLD ranking (before 2026-11-15).
- Each basket is held 12 months, then dropped. Nothing is rebalanced in between.
- Costs: an assumed 0.5% per side (bid/ask spread; stock commissions are $0) is taken off
  when a basket is bought and again when it is sold.
- A stock that stops trading counts as worth $0 from then on (conservative; check by hand,
  an acquisition may have paid cash).
- Compared with two simple baselines: IWN (small-cap value ETF) and SPY (S&P 500 ETF).

Output: screens/paper_track.json (the baskets) and screens/paper_track.md (month-by-month results).
"""
import json
from datetime import date
from pathlib import Path

OUT = Path("screens")
STATE = OUT / "paper_track.json"
BASKET_SIZE = 20
HOLD_MONTHS = 12
COST_PER_SIDE = 0.005
BASELINES = ["IWN", "SPY"]
VERSIONS_TRIED = 2  # old and new ranking; add 1 every time the ranking rules change


def get_closes(tickers, start):
    """Daily closes adjusted for splits and dividends, as a DataFrame (dates x tickers)."""
    import yfinance as yf
    data = yf.download(sorted(set(tickers)), start=start, interval="1d", auto_adjust=True,
                       group_by="column", threads=True, progress=False)
    closes = data["Close"]
    if not hasattr(closes, "columns"):  # one ticker only
        closes = closes.to_frame(sorted(set(tickers))[0])
    return closes


def month_add(d, months):
    m = d.month - 1 + months
    return date(d.year + m // 12, m % 12 + 1, 1)


def basket_values(closes, cohort):
    """Daily value of 1 dollar put equally into the cohort's stocks (buy and hold), plus stocks that stopped trading."""
    import pandas as pd
    start = pd.Timestamp(cohort["start"])
    end = pd.Timestamp(month_add(date.fromisoformat(cohort["start"]), HOLD_MONTHS))
    window = closes[(closes.index >= start) & (closes.index < end)]
    last_day = closes.index[-1]
    parts, stopped = [], []
    for t in cohort["tickers"]:
        s = window[t].dropna() if t in window else pd.Series(dtype=float)
        if s.empty:
            stopped.append(t)
            parts.append(pd.Series(0.0, index=window.index))
            continue
        rel = (window[t] / s.iloc[0]).ffill()
        if (last_day - s.index[-1]).days > 7 and s.index[-1] < end - pd.Timedelta(days=7):
            rel[rel.index > s.index[-1]] = 0.0  # stopped trading: count as $0
            stopped.append(t)
        parts.append(rel.fillna(0.0))
    value = sum(parts) / len(parts) * (1 - COST_PER_SIDE)
    if last_day >= end - pd.Timedelta(days=1):  # basket finished its 12 months: pay the selling cost on the last day
        value.iloc[-1] *= (1 - COST_PER_SIDE)
    return value, stopped


def monthly_returns(values):
    """{'YYYY-MM': return} from a daily value series that starts at 1 - cost."""
    out, prev = {}, 1.0
    for month, v in values.groupby(values.index.strftime("%Y-%m")):
        out[month] = v.iloc[-1] / prev - 1
        prev = v.iloc[-1]
    return out


def main():
    screen = json.loads((OUT / "diamond_screen.json").read_text())
    state = json.loads(STATE.read_text()) if STATE.exists() else {"cohorts": []}
    price_date = screen["shortlist"][0]["price_date"] if screen["shortlist"] else None

    # 1. New baskets on the first run of each month
    if price_date and not any(c["start"][:7] == price_date[:7] for c in state["cohorts"]):
        for method, order in (("new", screen["all_passing"]), ("old", screen.get("old_method_order", []))):
            if order:
                state["cohorts"].append({"start": price_date, "method": method, "tickers": order[:BASKET_SIZE]})
    state.update(versions_tried=VERSIONS_TRIED, cost_per_side=COST_PER_SIDE, basket_size=BASKET_SIZE, hold_months=HOLD_MONTHS)
    STATE.write_text(json.dumps(state, indent=1))
    if not state["cohorts"]:
        print("paper track: no baskets yet")
        return

    # 2. Month-by-month results
    first = min(c["start"] for c in state["cohorts"])
    closes = get_closes([t for c in state["cohorts"] for t in c["tickers"]] + BASELINES, first)
    results, stopped_all = {}, set()
    for method in ("new", "old"):
        per_month = {}
        for c in (c for c in state["cohorts"] if c["method"] == method):
            value, stopped = basket_values(closes, c)
            stopped_all.update(stopped)
            for m, r in monthly_returns(value).items():
                per_month.setdefault(m, []).append(r)
        results[method] = {m: sum(rs) / len(rs) for m, rs in per_month.items()}  # equal weight across open baskets
    for b in BASELINES:
        s = closes[b].dropna()
        results[b] = monthly_returns(s / s.iloc[0])

    months = sorted(set().union(*[set(r) for r in results.values()]))
    cols = ["new", "old"] + BASELINES
    total = {k: 1.0 for k in cols}
    rows = []
    for m in months:
        cells = []
        for k in cols:
            r = results[k].get(m)
            if r is not None:
                total[k] *= 1 + r
            cells.append(f"{r:+.1%}" if r is not None else "—")
        label = m + (" (so far)" if m == months[-1] else "")
        rows.append(f"| {label} | " + " | ".join(cells) + " |")

    lines = [
        "# Diamond Finder: honest forward test",
        "",
        f"Updated with closes through {closes.index[-1].date()}. Paper money only. "
        f"{len([c for c in state['cohorts'] if c['method'] == 'new'])} monthly basket(s) per method so far.",
        "",
        "Each month, two paper baskets of the top 20 stocks are bought at that run's closing prices: one by the "
        "**new ranking** (clean stocks first, price-to-cash-flow factor; from 2026-11-15) and one by the **old ranking** "
        "(before 2026-11-15). Each is held 12 months. Costs of 0.5% per buy and per sell are taken off (assumed bid/ask spread; "
        "stock commissions are $0). A stock that stops trading counts as $0 until checked by hand. "
        "Baselines: IWN (small-cap value ETF) and SPY (S&P 500 ETF).",
        "",
        "| Month | New ranking | Old ranking | IWN | SPY |",
        "|---|---|---|---|---|",
    ] + rows + [
        "| **Total so far** | " + " | ".join(f"**{total[k] - 1:+.1%}**" for k in cols) + " |",
        "",
        "## How to read this",
        "",
        f"- **Versions tried: {VERSIONS_TRIED}** (old and new ranking). With more than one version, the better-looking "
        "one is partly ahead by luck, so discount its lead.",
        "- Judge only after at least 12 months, and only against IWN. A few months, or one good year, proves little "
        "(SKILL.md: about 30 years of results are needed to be 95% sure).",
        "- These are equal-weight baskets, so there is no bet sizing to test here.",
        "- This is a test of the screen, not a buy list. Real trading would also need the full research in Ticker Forensics.",
    ]
    if stopped_all:
        lines += ["", "**Stopped trading (counted as $0, check what happened):** " + ", ".join(sorted(stopped_all))]
    (OUT / "paper_track.md").write_text("\n".join(lines) + "\n")
    print(f"paper track: {len(state['cohorts'])} baskets, months {months[0]}..{months[-1]}")


if __name__ == "__main__":
    main()
