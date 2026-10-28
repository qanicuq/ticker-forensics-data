"""Diamond Screen: finds overlooked, cheap, financially sound US stocks using the
value-investing-library SKILL.md rules (Graham enterprising tests, forensic cash check,
equal-weight rank sum). Runs Mon/Wed/Fri after the close. Free data only:
SEC company facts (fundamentals) + yfinance (closing price and volume).

Output: screens/diamond_screen.md (easy to read) and screens/diamond_screen.json.
This finds CANDIDATES to research in Ticker Forensics. It is not a buy list.
"""
import json
import os
import re
import sys
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

EMAIL = os.environ.get("SEC_IDENTITY_EMAIL", "")
HEADERS = {"User-Agent": f"qanicuq {EMAIL}"}
OUT = Path("screens")
SHORTLIST_SIZE = 25

# ---- SKILL.md thresholds (section 3 and 7) ----
MAX_MARKET_CAP = 2_000_000_000    # neglected small and micro caps
MIN_AVG_VOLUME = 50_000           # shares/day, so a position can be sold (section 7 liquidity)
MAX_PE_AVG3 = 15                  # Graham: price <= 15 x 3-yr average earnings
MIN_CURRENT_RATIO = 1.5           # Graham enterprising
MAX_DEBT_TO_NCA = 1.10            # Graham enterprising: debt <= 110% of net current assets
LOSS_FREE_YEARS = 5               # Graham enterprising: no loss in 5 years


def sec_get(url, **kw):
    r = requests.get(url, headers=HEADERS, timeout=kw.pop("timeout", 60), **kw)
    r.raise_for_status()
    return r


# ---------- reading SEC company facts ----------
def _rows(facts, tag, unit):
    return facts.get("us-gaap", {}).get(tag, {}).get("units", {}).get(unit, [])


def annual(facts, tags, unit="USD"):
    """{fiscal-year-end: value} from 10-K full-year figures. Latest filing wins (restated
    numbers). Tags are tried in order; an earlier tag wins for the same year."""
    out = {}
    for tag in tags:
        best = {}
        for r in _rows(facts, tag, unit):
            if not str(r.get("form", "")).startswith("10-K") or "start" not in r:
                continue
            days = (date.fromisoformat(r["end"]) - date.fromisoformat(r["start"])).days
            if not 300 <= days <= 400:
                continue
            if r["end"] not in best or r["filed"] > best[r["end"]]["filed"]:
                best[r["end"]] = r
        for end, r in best.items():
            out.setdefault(end, r["val"])
    return dict(sorted(out.items()))


def instants(facts, tags, unit="USD", forms=("10-K", "10-Q")):
    """{date: value} for balance-sheet items. Latest filing wins."""
    out = {}
    for tag in tags:
        best = {}
        for r in _rows(facts, tag, unit):
            if "start" in r or not str(r.get("form", "")).startswith(forms):
                continue
            if r["end"] not in best or r["filed"] > best[r["end"]]["filed"]:
                best[r["end"]] = r
        for end, r in best.items():
            out.setdefault(end, r["val"])
    return dict(sorted(out.items()))


def ttm_earnings(facts, fy_end, fy_value):
    """Last-12-months earnings = last annual + this year-to-date - same period last year,
    from 10-Q filings. Returns the annual figure if no newer quarter is out yet."""
    fy = date.fromisoformat(fy_end)
    for tag in NET_INCOME:
        rows = [r for r in _rows(facts, tag, "USD") if str(r.get("form", "")).startswith("10-Q") and "start" in r]
        ytd = [r for r in rows if 0 < (date.fromisoformat(r["start"]) - fy).days <= 15]
        if not ytd:
            continue
        cur = max(ytd, key=lambda r: (r["end"], r["filed"]))
        c_start, c_end = date.fromisoformat(cur["start"]), date.fromisoformat(cur["end"])
        prior = [r for r in rows
                 if abs((date.fromisoformat(r["start"]) - (c_start - timedelta(days=365))).days) <= 15
                 and abs((date.fromisoformat(r["end"]) - (c_end - timedelta(days=365))).days) <= 15]
        if prior:
            p = max(prior, key=lambda r: r["filed"])
            return fy_value + cur["val"] - p["val"]
    return fy_value


def latest(series):
    return (list(series.items())[-1]) if series else (None, None)


def at_or_zero(series, d):
    return series.get(d, 0) or 0


REVENUE = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet",
           "RevenueFromContractWithCustomerIncludingAssessedTax"]
# continuing operations first, so a one-time gain from selling a business is not counted (SKILL.md section 5)
NET_INCOME = ["IncomeLossFromContinuingOperations", "NetIncomeLoss", "ProfitLoss"]
CFFO = ["NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]
DIVIDENDS = ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"]


def fundamentals(facts):
    """Everything the screen needs from one company's SEC facts, or a reason it was skipped."""
    ni = annual(facts, NET_INCOME)
    years = list(ni)[-LOSS_FREE_YEARS:]
    if len(years) < LOSS_FREE_YEARS:
        return None, "under 5 years of annual reports"
    # the 5 years must be consecutive and recent
    if (date.fromisoformat(years[-1]) - date.fromisoformat(years[0])).days > 365 * (LOSS_FREE_YEARS - 1) + 60:
        return None, "gap in annual reports"
    if (date.today() - date.fromisoformat(years[-1])).days > 550:
        return None, "no recent annual report"
    if any(ni[y] <= 0 for y in years):
        return None, "a loss in the last 5 years"

    ca_d, ca = latest(instants(facts, ["AssetsCurrent"]))
    cl = instants(facts, ["LiabilitiesCurrent"]).get(ca_d)
    if not ca or not cl:
        return None, "no current assets/liabilities (banks, insurers, REITs)"
    if (date.today() - date.fromisoformat(ca_d)).days > 400:
        return None, "balance sheet out of date"
    liab = instants(facts, ["Liabilities"]).get(ca_d)
    equity = instants(facts, ["StockholdersEquity",
                              "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]).get(ca_d)
    if liab is None:  # some filers only report "liabilities and equity"
        le = instants(facts, ["LiabilitiesAndStockholdersEquity"]).get(ca_d)
        liab = le - equity if (le is not None and equity is not None) else None
    if liab is None or equity is None:
        return None, "missing total liabilities or equity"

    debt = (at_or_zero(instants(facts, ["LongTermDebtNoncurrent", "LongTermDebt"]), ca_d)
            + at_or_zero(instants(facts, ["OperatingLeaseLiabilityNoncurrent"]), ca_d)   # leases count as debt (SKILL.md section 13)
            + at_or_zero(instants(facts, ["FinanceLeaseLiabilityNoncurrent"]), ca_d))
    nca = ca - cl
    current_ratio = ca / cl
    if current_ratio < MIN_CURRENT_RATIO:
        return None, "current ratio under 1.5"
    if nca <= 0 or debt > MAX_DEBT_TO_NCA * nca:
        return None, "debt over 110% of net current assets"

    goodwill = at_or_zero(instants(facts, ["Goodwill"]), ca_d)
    intang = at_or_zero(instants(facts, ["IntangibleAssetsNetExcludingGoodwill",
                                         "FiniteLivedIntangibleAssetsNet"]), ca_d)
    preferred = at_or_zero(instants(facts, ["PreferredStockValue"]), ca_d)

    cf = annual(facts, CFFO)
    rev = annual(facts, REVENUE)
    last3 = years[-3:]
    cffo3 = [cf.get(y) for y in last3]
    div = annual(facts, DIVIDENDS)

    # forensic flags (SKILL.md section 4, metrics 1, 5, 7)
    flags = []
    cffo_ratio = sum(cffo3) / sum(ni[y] for y in last3) if None not in cffo3 else None
    if cffo_ratio is None:
        flags.append("cash flow data missing")
    elif cffo_ratio < 0.8:
        flags.append(f"cash flow only {cffo_ratio:.0%} of earnings (3 yrs)")
    fy, fy0 = years[-1], years[-2]
    ttm = ttm_earnings(facts, fy, ni[fy])
    if ttm <= 0:
        flags.append("losing money over the last 12 months")
    elif ttm < 0.5 * ni[fy]:
        flags.append(f"last-12-month earnings down {1 - ttm / ni[fy]:.0%} from last annual report")
    if rev.get(fy) and rev.get(fy0):
        rev_g = rev[fy] / rev[fy0] - 1
        for name, tags in (("receivables", ["AccountsReceivableNetCurrent"]),
                           ("inventory", ["InventoryNet"])):
            s = instants(facts, tags, forms=("10-K",))
            if s.get(fy) and s.get(fy0):
                g = s[fy] / s[fy0] - 1
                if g > rev_g + 0.10:
                    flags.append(f"{name} {g:+.0%} vs sales {rev_g:+.0%}")

    dei = facts.get("dei", {}).get("EntityCommonStockSharesOutstanding", {}).get("units", {}).get("shares", [])
    dei = [r for r in dei if str(r.get("form", "")).startswith(("10-K", "10-Q"))]
    last = max(dei, key=lambda r: (r["end"], r["filed"])) if dei else None
    # a stale count usually means the company now reports each share class separately
    shares = last["val"] if last and (date.today() - date.fromisoformat(last["end"])).days <= 400 else None

    return {
        "fy_end": fy,
        "balance_date": ca_d,
        "net_income": {y: ni[y] for y in years},
        "ni_avg3": sum(ni[y] for y in last3) / 3,
        "ni_ttm": ttm,
        "revenue_last": rev.get(fy),
        "current_ratio": round(current_ratio, 2),
        "net_current_assets": nca,
        "debt_incl_leases": debt,
        "equity": equity,
        "tangible_book": equity - goodwill - intang,
        "ncav": ca - liab - preferred,
        "cffo_ratio": round(cffo_ratio, 2) if cffo_ratio is not None else None,
        "pays_dividend": bool(div.get(fy)),
        "shares": shares,
        "flags": flags,
    }, None


# ---------- prices ----------
def get_prices(tickers):
    """{ticker: (last close, last close date, avg daily volume over ~3 months)} from yfinance."""
    import yfinance as yf
    ny = datetime.now(ZoneInfo("America/New_York"))
    # today's bar only counts once the market has closed (4:00 PM; 4:15 for a safety margin)
    last_closed = str(ny.date() if (ny.hour, ny.minute) >= (16, 15) else ny.date() - timedelta(days=1))
    out = {}
    for i in range(0, len(tickers), 200):
        batch = tickers[i:i + 200]
        data = yf.download(batch, period="3mo", interval="1d", group_by="ticker",
                           auto_adjust=False, threads=True, progress=False)
        for t in batch:
            try:
                d = (data[t] if len(batch) > 1 else data).dropna(subset=["Close"])
                d = d[[str(x.date()) <= last_closed for x in d.index]]  # never use a day still trading
                if len(d) < 20:
                    continue
                out[t] = (float(d["Close"].iloc[-1]), str(d.index[-1].date()), float(d["Volume"].mean()))
            except Exception:
                continue
    return out


# ---------- new Form 10 filings (often spinoffs) ----------
def form10_filings(days=7):
    found = []
    for back in range(days):
        d = date.today() - timedelta(days=back)
        if d.weekday() >= 5:
            continue
        url = f"https://www.sec.gov/Archives/edgar/daily-index/{d.year}/QTR{(d.month - 1) // 3 + 1}/form.{d:%Y%m%d}.idx"
        try:
            text = sec_get(url, timeout=30).text
        except Exception:
            continue  # not published yet or holiday
        for line in text.splitlines():
            if line.startswith("10-12B ") or line.startswith("10-12G "):
                parts = re.split(r"\s{2,}", line.strip())
                if len(parts) >= 5:
                    found.append({"form": parts[0], "company": parts[1], "cik": parts[2],
                                  "filed": parts[3], "url": "https://www.sec.gov/Archives/" + parts[4]})
    return found


def rank(values, higher_is_better):
    """Rank 1 = best. Missing values rank last."""
    keyed = sorted(values.items(), key=lambda kv: (kv[1] is None, -(kv[1] or 0) if higher_is_better else (kv[1] or 0)))
    return {k: i + 1 for i, (k, _) in enumerate(keyed)}


def fmt_money(x):
    if x is None:
        return "n/a"
    for div, s in ((1e9, "B"), (1e6, "M")):
        if abs(x) >= div:
            return f"${x / div:.2f}{s}"
    return f"${x:,.0f}"


def main():
    if not EMAIL:
        sys.exit("SEC_IDENTITY_EMAIL secret is missing")
    run_time = datetime.now(timezone.utc)

    # 1. Universe: SEC's list of companies on major US exchanges (no OTC), common stock only
    lst = json.load(open("sec/company_tickers_exchange.json"))
    universe = {}
    for cik, name, ticker, exch in lst["data"]:
        if exch in ("Nasdaq", "NYSE", "CBOE") and "-" not in ticker and cik not in universe:
            universe[cik] = (ticker, name, exch)
    print(f"universe: {len(universe)} companies on major exchanges")

    # 2. Fundamentals from the SEC bulk company facts file (all filers, refreshed nightly)
    zpath = Path("companyfacts.zip")
    with sec_get("https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip", stream=True, timeout=300) as r:
        with open(zpath, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    print(f"downloaded company facts: {zpath.stat().st_size / 1e9:.2f} GB")

    passed, skipped = {}, {}
    with zipfile.ZipFile(zpath) as z:
        for cik, (ticker, name, exch) in universe.items():
            member = f"CIK{cik:010d}.json"
            try:
                facts = json.loads(z.read(member)).get("facts", {})
            except KeyError:
                skipped["no SEC company facts (often foreign filers)"] = skipped.get("no SEC company facts (often foreign filers)", 0) + 1
                continue
            if "us-gaap" not in facts:
                skipped["not US GAAP (foreign filer)"] = skipped.get("not US GAAP (foreign filer)", 0) + 1
                continue
            try:
                f, why = fundamentals(facts)
            except Exception as e:
                f, why = None, f"data error ({type(e).__name__})"
            if f:
                passed[ticker] = {"ticker": ticker, "name": name, "exchange": exch, "cik": cik, **f}
            else:
                skipped[why] = skipped.get(why, 0) + 1
    zpath.unlink()
    print(f"passed balance-sheet and earnings tests: {len(passed)}")

    # 3. Prices: closing price and volume for the survivors only
    prices = get_prices(sorted(passed))
    print(f"got prices for {len(prices)} of {len(passed)}")

    final, unsized = {}, []
    for t, f in passed.items():
        if not f["shares"]:
            unsized.append(t)
            continue
        if t not in prices:
            skipped["no price data"] = skipped.get("no price data", 0) + 1
            continue
        price, price_date, avg_vol = prices[t]
        mcap = price * f["shares"]
        pe_avg3 = mcap / f["ni_avg3"]
        if mcap > MAX_MARKET_CAP:
            why = "market cap over $2B"
        elif avg_vol < MIN_AVG_VOLUME:
            why = "average volume under 50K shares"
        elif pe_avg3 > MAX_PE_AVG3:
            why = "P/E over 15 on 3-yr average earnings"
        else:
            why = None
        if why:
            skipped[why] = skipped.get(why, 0) + 1
            continue
        ni = list(f["net_income"].values())
        pb = mcap / f["equity"] if f["equity"] > 0 else None
        ptb = mcap / f["tangible_book"] if f["tangible_book"] > 0 else None
        pe_last = mcap / ni[-1]
        tests = {  # Graham enterprising (SKILL.md section 3); first three are guaranteed by the gates
            "current ratio >= 1.5": True,
            "debt <= 110% of net current assets": True,
            "no loss in 5 years": True,
            "P/E <= 9 (latest year)": pe_last <= 9,
            "pays a dividend": f["pays_dividend"],
            "earnings above 4 years ago": ni[-1] > ni[0],
            "price < 120% of tangible book": ptb is not None and ptb < 1.2,
        }
        final[t] = {
            **f,
            "price": round(price, 2), "price_date": price_date, "avg_volume": round(avg_vol),
            "market_cap": round(mcap),
            "pe_avg3": round(pe_avg3, 1), "pe_last": round(pe_last, 1),
            "pb": round(pb, 2) if pb else None, "ptb": round(ptb, 2) if ptb else None,
            "graham_pe_x_pb": round(pe_avg3 * pb, 1) if pb else None,
            "ncav_to_mcap": round(f["ncav"] / mcap, 2),
            "net_net": f["ncav"] > 0 and mcap <= f["ncav"] * 2 / 3,
            "enterprising_tests": tests,
            "enterprising_passed": sum(tests.values()),
        }

    # 4. Equal-weight rank sum (SKILL.md section 11: keep scoring simple)
    ranks = [
        rank({t: v["pe_avg3"] for t, v in final.items()}, higher_is_better=False),
        rank({t: v["ptb"] for t, v in final.items()}, higher_is_better=False),
        rank({t: v["cffo_ratio"] for t, v in final.items()}, higher_is_better=True),
        rank({t: v["ncav_to_mcap"] for t, v in final.items()}, higher_is_better=True),
    ]
    for t in final:
        final[t]["rank_sum"] = sum(r[t] for r in ranks)
    ordered = sorted(final.values(), key=lambda v: v["rank_sum"])
    shortlist = ordered[:SHORTLIST_SIZE]

    form10 = form10_filings()

    # 5. What changed since the last run (read before it is overwritten)
    prev_path = OUT / "diamond_screen.json"
    prev = json.loads(prev_path.read_text()) if prev_path.exists() else None
    changes = []
    if prev:
        old = {v["ticker"]: v for v in prev["shortlist"]}
        now = {v["ticker"]: v for v in shortlist}
        added = [t for t in now if t not in old]
        dropped = [t for t in old if t not in now]
        kind = lambda flag: flag.split()[0]  # "inventory +14% vs ..." -> "inventory"
        new_flags = [f"{t} ({f})" for t in now if t in old
                     for f in now[t]["flags"] if kind(f) not in {kind(x) for x in old[t]["flags"]}]
        seen = {x["url"] for x in prev.get("form10_filings", [])}
        new_form10 = [x for x in form10 if x["url"] not in seen]
        if added:
            changes.append("New: " + ", ".join(added))
        if dropped:
            changes.append("Dropped: " + ", ".join(
                f"{t} ({'fell out of top 25' if t in final else 'no longer passes'})" for t in dropped))
        if new_flags:
            changes.append("New red flag: " + "; ".join(new_flags))
        if new_form10:
            changes.append(f"{len(new_form10)} new Form 10 filing(s): " + ", ".join(x["company"] for x in new_form10))
        prev_ny = datetime.fromisoformat(prev["run_utc"]).astimezone(ZoneInfo("America/New_York"))
        since = f"since {prev_ny:%A}'s run"
    else:
        since = "(first run)"

    # 6. Save
    OUT.mkdir(exist_ok=True)
    result = {
        "run_utc": run_time.isoformat(timespec="minutes"),
        "sources": "SEC EDGAR company facts (fundamentals), yfinance (closing price, volume), SEC exchange list",
        "universe": len(universe), "passed_all": len(final), "skipped_reasons": skipped,
        "shortlist": shortlist, "not_ranked_no_share_count": unsized, "all_passing": [v["ticker"] for v in ordered], "form10_filings": form10,
    }
    (OUT / "diamond_screen.json").write_text(json.dumps(result, indent=1, default=str))

    ny = run_time.astimezone(ZoneInfo("America/New_York"))
    lines = [
        "# Diamond Finder",
        "",
        f"Run: {ny:%a %b %d, %Y %I:%M %p} New York time. Prices are the last close from yfinance; "
        "fundamentals are from SEC filings. **These are stocks to research, not buys.** "
        "Run the interesting ones through Ticker Forensics.",
        "",
        f"**{len(final)} of {len(universe)}** companies passed every test. Top {len(shortlist)} below, best first.",
        "",
        f"## Changes {since}",
        "",
    ] + ([f"- {c}" for c in changes] or ["- No changes."]) + [
        "",
        "## How a stock gets on this list",
        "",
        "Must pass all of these (SKILL.md section 3): listed on NYSE, Nasdaq or Cboe; market cap under $2B; "
        "average volume over 50K shares a day; no loss in any of the last 5 years; current ratio of at least 1.5; "
        "long-term debt plus leases no more than 110% of net current assets; price no more than 15 times 3-year average earnings.",
        "",
        "Then ranked with equal weight on four things: cheapest on 3-year average earnings, cheapest against "
        "tangible book, cash flow best backing up earnings, and most liquid assets for the price.",
        "",
        "## Shortlist",
        "",
        "| # | Ticker | Company | Price | Mkt cap | P/E (3-yr avg) | P/B | P/E × P/B ≤ 22.5? | Graham tests passed | Net-net? | Red flags |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, v in enumerate(shortlist, 1):
        g = v["graham_pe_x_pb"]
        lines.append(
            f"| {i} | **{v['ticker']}** | {v['name']} | ${v['price']:.2f} | {fmt_money(v['market_cap'])} | "
            f"{v['pe_avg3']} | {v['pb'] if v['pb'] is not None else 'n/a'} | "
            f"{'Yes' if g is not None and g <= 22.5 else 'No'} ({g if g is not None else 'n/a'}) | "
            f"{v['enterprising_passed']}/7 | {'Yes' if v['net_net'] else 'No'} | "
            f"{'; '.join(v['flags']) or 'none'} |")
    lines += [
        "",
        "Graham tests = the 7 enterprising-investor tests in SKILL.md. Red flags are quick forensic checks "
        "(SKILL.md section 4); a flag means look harder, not automatically avoid.",
        "",
        "## Passed the earnings and balance-sheet tests but not ranked",
        "",
        "The SEC has no current company-wide share count for these (usually because they have two share classes), "
        "so their market cap and P/E can't be worked out reliably here. Check them by hand or in Ticker Forensics: "
        + (", ".join(sorted(unsized)) or "none") + ".",
        "",
        "## New Form 10 filings this week (often spinoffs, SKILL.md section 3)",
        "",
    ]
    if form10:
        lines += [f"- [{x['company']}]({x['url']}) — {x['form']}, filed {x['filed']}" for x in form10]
    else:
        lines.append("- None found in the last 7 days.")
    lines += [
        "",
        "## Why other companies were left out",
        "",
    ] + [f"- {why}: {n}" for why, n in sorted(skipped.items(), key=lambda kv: -kv[1])] + [
        "",
        "Known limits: banks, insurers and most REITs drop out because they don't report current assets "
        "(Graham's tests don't fit them). Foreign companies that file 20-F reports aren't covered. "
        "Market cap uses the SEC share count, which can be off for companies with more than one share class.",
    ]
    (OUT / "diamond_screen.md").write_text("\n".join(lines) + "\n")

    if changes:
        msg = f"Changes {since}: " + ". ".join(changes) + f". {len(final)} stocks pass. Tap to see the list."
    else:
        msg = f"No changes {since}. {len(final)} stocks still pass. Tap to see the list."
    Path("ntfy_message.txt").write_text(msg)
    print(f"done: {len(final)} passed, shortlist {len(shortlist)}, form10 {len(form10)}")


if __name__ == "__main__":
    main()
