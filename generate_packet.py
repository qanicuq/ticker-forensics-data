#!/usr/bin/env python3
"""Generate compact Ticker Forensics data packet for one ticker."""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

TICKER = sys.argv[1].upper() if len(sys.argv) > 1 else "AAPL"
OUT_DIR = Path("packets")
OUT_DIR.mkdir(exist_ok=True)
OUT_PATH = OUT_DIR / f"{TICKER}.json"

packet = {
    "ticker": TICKER,
    "generated_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "price_source": "yfinance (unofficial)",
    "fundamentals": {},
    "filings": [],
    "technicals": {},
    "macro": {},
    "crypto": None,
    "fx": None,
    "cross_check": {"matches": [], "mismatches": []},
    "errors": [],
    "notes": [],
}

def round2(v):
    try:
        return round(float(v), 2) if v is not None and not pd.isna(v) else None
    except Exception:
        return None

def pct_diff(a, b):
    if a is None or b is None or b == 0:
        return None
    return abs(a - b) / abs(b) * 100

# ---------- 1. edgartools ----------
try:
    from edgar import Company, set_identity
    email = os.environ.get("SEC_IDENTITY_EMAIL", "user@example.com")
    set_identity(f"qanicuq <{email}>")
    company = Company(TICKER)
    financials = company.get_financials()
    packet["fundamentals"] = {
        "revenue": round2(financials.get_revenue()),
        "net_income": round2(financials.get_net_income()),
        "eps": round2(financials.get_eps()) if hasattr(financials, "get_eps") else None,
        "total_debt": round2(financials.get_total_debt()) if hasattr(financials, "get_total_debt") else None,
        "cash": round2(financials.get_cash()) if hasattr(financials, "get_cash") else None,
        "free_cash_flow": round2(financials.get_free_cash_flow()) if hasattr(financials, "get_free_cash_flow") else None,
        "shares_outstanding": round2(financials.get_shares_outstanding()) if hasattr(financials, "get_shares_outstanding") else None,
        "note": "latest available from 10-K/10-Q via edgartools",
    }
    filings = company.get_filings()[:5]
    packet["filings"] = [
        {
            "form": f.form,
            "date": str(f.filing_date),
            "url": f.filing_url if hasattr(f, "filing_url") else f"https://www.sec.gov/Archives/edgar/data/{f.cik}/{f.accession_number.replace('-', '')}/{f.accession_number}-index.html",
        }
        for f in filings
    ]
except Exception as e:
    packet["errors"].append(f"edgartools: {type(e).__name__}: {str(e)[:120]}")

# ---------- 2. Price + technicals (direct yfinance + pandas-ta) ----------
prices = None
last_close = None
yf_market_cap = None
yf_pe = None
yf_revenue_4q = None
company_name = TICKER
try:
    import yfinance as yf
    end = datetime.utcnow().date()
    start = end - timedelta(days=365)
    raw = yf.download(TICKER, start=str(start), end=str(end), progress=False, auto_adjust=True)
    if raw is not None and not raw.empty:
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        prices = raw.reset_index()
        prices.columns = [str(c).lower() for c in prices.columns]
        prices = prices.dropna(subset=["close"]).reset_index(drop=True)  # yfinance can return a blank last row
        last_close = float(prices["close"].iloc[-1])
        packet["cross_check"]["matches"].append({"field": "last_price", "source": "yfinance", "value": round2(last_close)})
    t = yf.Ticker(TICKER)
    info = t.info or {}
    company_name = info.get("shortName") or info.get("longName") or TICKER
    yf_market_cap = round2(info.get("marketCap"))
    yf_pe = round2(info.get("trailingPE"))
    # foreign filers (ADRs) report in their home currency; the engine converts to US dollars with this rate
    fin_cur = info.get("financialCurrency")
    if fin_cur and fin_cur != "USD":
        try:
            fx_close = yf.Ticker(f"{fin_cur}USD=X").history(period="5d")["Close"].dropna()
            packet["fx"] = {"currency": fin_cur, "usd_per_unit": round(float(fx_close.iloc[-1]), 6),
                            "date": str(fx_close.index[-1].date()), "source": "yfinance"}
        except Exception as e:
            packet["errors"].append(f"fx: no {fin_cur}USD rate: {type(e).__name__}")
    try:
        q_income = t.quarterly_income_stmt
        if q_income is not None and not q_income.empty:
            rev_row = next((r for r in q_income.index if str(r).lower() == "total revenue"), None)
            if rev_row:
                yf_revenue_4q = [round2(v) for v in q_income.loc[rev_row].dropna().head(4).tolist()]
    except Exception:
        pass
except Exception as e:
    packet["errors"].append(f"yfinance: {type(e).__name__}: {str(e)[:120]}")

# Technicals with pandas-ta-classic
try:
    if prices is not None and len(prices) > 200:
        import pandas_ta_classic as ta
        df = prices.copy()
        df.columns = [c.lower() for c in df.columns]
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        df.ta.sma(length=200, append=True)
        df.ta.ema(length=20, append=True)
        df.ta.atr(length=14, append=True)
        df.ta.bbands(length=20, std=2, append=True)
        last = df.iloc[-1]
        high52 = float(df["high"].max())
        low52 = float(df["low"].min())
        close = float(last["close"])
        packet["technicals"] = {
            "rsi_14": round2(last.get("RSI_14")),
            "macd": round2(last.get("MACD_12_26_9")),
            "macd_signal": round2(last.get("MACDs_12_26_9")),
            "sma_20": round2(last.get("SMA_20")),
            "sma_50": round2(last.get("SMA_50")),
            "sma_200": round2(last.get("SMA_200")),
            "ema_20": round2(last.get("EMA_20")),
            "atr_14": round2(last.get("ATRr_14")),
            "bb_upper": round2(last.get("BBU_20_2.0")),
            "bb_middle": round2(last.get("BBM_20_2.0")),
            "bb_lower": round2(last.get("BBL_20_2.0")),
            "high_52w": round2(high52),
            "low_52w": round2(low52),
            "pct_from_52w_high": round2((close / high52 - 1) * 100),
            "pct_from_52w_low": round2((close / low52 - 1) * 100),
        }
        packet["technicals"]["note"] = "computed with pandas-ta-classic (maintained fork)"
except Exception as e:
    packet["errors"].append(f"pandas-ta: {type(e).__name__}: {str(e)[:120]}")
    if prices is not None:
        try:
            close = prices["close"]
            packet["technicals"] = {
                "sma_20": round2(close.rolling(20).mean().iloc[-1]),
                "sma_50": round2(close.rolling(50).mean().iloc[-1]),
                "sma_200": round2(close.rolling(200).mean().iloc[-1]),
                "note": "plain pandas fallback",
            }
        except Exception as e2:
            packet["errors"].append(f"plain-pandas fallback: {type(e2).__name__}")

# ---------- 3. Cross-check yfinance vs SEC filings ----------
# Uses the SEC XBRL "company facts" data (the same filings edgartools reads).
def sec_facts():
    from edgar import Company
    cik = int(Company(TICKER).cik)
    email = os.environ.get("SEC_IDENTITY_EMAIL", "user@example.com")
    import requests
    r = requests.get(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json",
        headers={"User-Agent": f"qanicuq {email}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["facts"]

def foreign_annual_form():
    """'20-F' or '40-F' when the company files as a foreign private issuer (no 10-Q figures), else None."""
    from edgar import Company
    import requests
    cik = int(Company(TICKER).cik)
    email = os.environ.get("SEC_IDENTITY_EMAIL", "user@example.com")
    r = requests.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers={"User-Agent": f"qanicuq {email}"}, timeout=30)
    r.raise_for_status()
    forms = r.json().get("filings", {}).get("recent", {}).get("form", [])
    annual = next((f for f in forms if f in ("10-K", "20-F", "40-F")), None)
    return annual if annual in ("20-F", "40-F") else None

FOREIGN_FORM = None
try:
    FOREIGN_FORM = foreign_annual_form()
except Exception as e:
    packet["errors"].append(f"sec submissions: {type(e).__name__}: {str(e)[:120]}")
if FOREIGN_FORM:
    packet["foreign_filer"] = FOREIGN_FORM
    packet["fundamentals"]["note"] = f"latest available via edgartools from the {FOREIGN_FORM}; may be in the company's own currency, not USD"
    packet["notes"].append(f"Foreign company: files a {FOREIGN_FORM} each year and 6-K reports in between, with no quarterly SEC figures, so only market cap and the annual report's figures can be checked (no P/E or 12-month revenue check).")

def days(e):
    return (pd.Timestamp(e["end"]) - pd.Timestamp(e["start"])).days

def last_4_quarters(entries):
    """Return the 4 most recent quarterly values, deriving Q4 = annual - Q1 - Q2 - Q3."""
    by_period = {}
    for e in entries:
        if "start" not in e:
            continue
        key = (e["start"], e["end"])
        if key not in by_period or e["filed"] > by_period[key]["filed"]:
            by_period[key] = e
    quarters = {k: v["val"] for k, v in by_period.items() if 80 <= days(v) <= 100}
    for (start, end), e in by_period.items():
        if 350 <= days(e) <= 380:
            inside = [v for (qs, qe), v in quarters.items() if qs >= start and qe < end]
            if len(inside) == 3 and not any(qe == end for (_, qe) in quarters):
                quarters[(end, end)] = e["val"] - sum(inside)
    ordered = sorted(quarters.items(), key=lambda kv: kv[0][1])[-4:]
    if len(ordered) < 4:
        return None
    span = (pd.Timestamp(ordered[-1][0][1]) - pd.Timestamp(ordered[0][0][1])).days
    if span > 300:  # gap in the quarters, don't trust the sum
        return None
    return [v for _, v in ordered]

def pick_revenue_tag(gaap):
    tags = [  # "Revenues" (the income statement's total) wins a tie: the contract-revenue tag can leave out
        "Revenues",  # regulated, lease or hedging revenue (e.g. OGE, NFG), which made revenue look 6-29% off
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
    ]
    present = [t for t in tags if t in gaap and "USD" in gaap[t]["units"]]
    if not present:
        return None
    return max(present, key=lambda t: max(e["end"] for e in gaap[t]["units"]["USD"]))

sec_market_cap = sec_pe = sec_rev_sum = None
facts = None
try:
    facts = sec_facts()
    gaap = facts.get("us-gaap", {})
    # share count: the cover-page figure, else the balance-sheet one; either is used only if it is under ~13 months
    # old (some filers stopped filing it in this form, e.g. Nike's last one is from 2015, which made market cap 74% off)
    total_shares, stale_end = None, None
    for src in (facts.get("dei", {}).get("EntityCommonStockSharesOutstanding", {}),
                gaap.get("CommonStockSharesOutstanding", {})):
        shares = src.get("units", {}).get("shares", [])
        if not shares:
            continue
        latest_accn = max(shares, key=lambda e: (e["filed"], e["end"]))["accn"]
        latest = [e for e in shares if e["accn"] == latest_accn]
        latest_end = max(e["end"] for e in latest)
        if (datetime.utcnow() - datetime.fromisoformat(latest_end)).days > 400:
            stale_end = stale_end or latest_end
            continue
        total_shares = sum(e["val"] for e in latest if e["end"] == latest_end)  # sums share classes
        break
    if total_shares is None:
        # companies with two share classes (e.g. Nike) now file the cover-page count per class, which SEC's
        # company-facts feed leaves out; the diluted weighted-average count from the newest 10-Q/10-K covers all classes
        wavg = [e for e in (gaap.get("WeightedAverageNumberOfDilutedSharesOutstanding")
                            or facts.get("ifrs-full", {}).get("AdjustedWeightedAverageShares") or {}).get("units", {}).get("shares", [])
                if "start" in e and str(e.get("form", "")).startswith(("10-Q", "10-K", "20-F", "40-F"))]
        if wavg:
            newest = max(wavg, key=lambda e: (e["end"], -days(e), e["filed"]))  # newest period, shortest span
            if (datetime.utcnow() - datetime.fromisoformat(newest["end"])).days <= 400:
                total_shares = newest["val"]
                packet["sec_shares_basis"] = (f"diluted weighted-average shares for the period ending {newest['end']} "
                                              f"(no undivided shares-outstanding figure filed since {stale_end or 'never'})")
    if total_shares is None:
        packet["errors"].append(f"sec facts: newest SEC share count is from {stale_end}, too old to check market cap"
                                if stale_end else "sec facts: no shares-outstanding figure filed")
    elif last_close:
        sec_market_cap = round2(total_shares * last_close)
    if FOREIGN_FORM:  # no 10-Q figures: the quarterly P/E and 12-month revenue checks don't apply
        raise StopIteration
    eps = last_4_quarters(gaap.get("EarningsPerShareDiluted", {}).get("units", {}).get("USD/shares", []))
    if eps and last_close and sum(eps) > 0:
        sec_pe = round2(last_close / sum(eps))
    elif eps and sum(eps) <= 0:
        sec_pe = "negative"
    elif not eps:
        packet["errors"].append("sec facts: fewer than 4 quarters of diluted EPS")
    rev_tag = pick_revenue_tag(gaap)
    if rev_tag:
        rev = last_4_quarters(gaap[rev_tag]["units"]["USD"])
        if rev:
            sec_rev_sum = round2(sum(rev))
except StopIteration:
    pass
except Exception as e:
    packet["errors"].append(f"sec facts: {type(e).__name__}: {str(e)[:120]}")

def compare_field(field, yf_val, sec_val, threshold):
    if yf_val is None or sec_val is None:
        packet["errors"].append(f"cross_check missing {field}: yfinance={yf_val}, sec={sec_val}")
        return
    diff = pct_diff(yf_val, sec_val)
    if diff is None:
        packet["errors"].append(f"cross_check cannot compute {field}")
        return
    entry = {"field": field, "yfinance": yf_val, "sec": sec_val, "pct_diff": round2(diff)}
    if field == "market_cap" and packet.get("sec_shares_basis"):
        entry["basis"] = "SEC share count: " + packet["sec_shares_basis"]
    if diff > threshold:
        packet["cross_check"]["mismatches"].append(entry)
    else:
        packet["cross_check"]["matches"].append(entry)

if FOREIGN_FORM:
    compare_field("market_cap", yf_market_cap, sec_market_cap, 5)
else:
    compare_field("market_cap", yf_market_cap, sec_market_cap, 5)
    if sec_pe == "negative":
        packet["cross_check"]["matches"].append({"field": "pe", "note": "last 4 quarters EPS negative, P/E not meaningful", "yfinance": yf_pe})
    else:
        compare_field("pe", yf_pe, sec_pe, 2)
    if yf_revenue_4q is not None and len(yf_revenue_4q) < 4:
        packet["errors"].append(f"yfinance returned only {len(yf_revenue_4q)} quarters of revenue")
        yf_rev_sum = None
    else:
        yf_rev_sum = round2(sum(yf_revenue_4q)) if yf_revenue_4q else None
    compare_field("revenue_4q_sum", yf_rev_sum, sec_rev_sum, 2)

# ---------- 3b. Governance, special situations and annual SEC figures ----------
# Walk-away signals from Financial Shenanigans §4.1 and special situations from Greenblatt §4.
WALK_AWAY_ITEMS = {"4.01": "Auditor changed (8-K item 4.01)", "4.02": "Prior financial statements can't be relied on (8-K item 4.02, restatement)"}
WATCH_ITEMS = {"5.02": "Director or officer departure/appointment (8-K item 5.02)", "1.03": "Bankruptcy or receivership (8-K item 1.03)", "2.01": "Acquisition or sale of assets completed (8-K item 2.01)", "2.06": "Material impairment (8-K item 2.06)", "3.01": "Delisting notice or listing-rule failure (8-K item 3.01)"}
SPECIAL_FORMS = {"10-12B": "Spinoff registration (Form 10)", "10-12G": "Spinoff/registration (Form 10)", "SC 13D": "Activist or 5%+ holder with intent (13D)", "SC 13D/A": "13D amendment", "SC TO-T": "Tender offer by a third party", "SC TO-I": "Issuer tender offer (buyback)", "SC 14D9": "Response to a tender offer", "DEFM14A": "Merger proxy", "S-4": "Merger/exchange registration", "PREM14A": "Preliminary merger proxy"}
DILUTION_FORMS = {"S-1", "S-3", "S-3ASR", "424B5", "424B4", "424B3", "F-3"}

def sec_get(url):
    import requests
    email = os.environ.get("SEC_IDENTITY_EMAIL", "user@example.com")
    r = requests.get(url, headers={"User-Agent": f"qanicuq {email}"}, timeout=30)
    r.raise_for_status()
    return r.json()

FINANCE_ROLES = ("chief financial officer", "chief accounting officer", "principal accounting officer",
                 "principal financial officer", "controller")
LEAVING = ("resign", "retire", "depart", "step down", "stepping down", "will leave", "leaving", "terminat", "separat",
           "transition", "step away", "stepping away", "succeed", "successor", "replace", "cease")
CHANGE = LEAVING + ("appoint", "elect", "named", "promot", "successor")

def classify_502(html_text):
    """Item 5.02 covers officer/director changes AND pay plans. Read the item's own text (not its standard heading,
    which always says "departure ... appointment ... compensatory") and return (kind, first telling sentence)."""
    import re, html as _h
    t = re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", html_text)))
    low = t.lower()
    starts = [m.end() for m in re.finditer(r"item\s*5\.02", low)]
    if not starts:
        return "unclear", ""
    # the item's own heading ("Item 5.02 Departure of Directors ...") marks where its text starts; later mentions are
    # cross-references such as "described in Item 5.02 above"
    heads = [i for i in starts if "departure" in low[i:i + 40]]
    body = low[(heads or starts)[0]:]
    nxt = re.search(r"item\s*\d\.\d\d|signature", body)  # the item ends at the next item or the signatures
    if nxt:
        body = body[:nxt.start()]
    body = re.sub(r"^[^a-z]*departure of directors.*?compensatory arrangements of certain officers\.?", "", body).strip()
    # a finance role within ~300 characters before (or 100 after) a leaving word; not sentence splits, which
    # break on "Inc." and similar
    for m in re.finditer(r"\b(?:" + "|".join(re.escape(w) for w in LEAVING) + ")", body):
        win = body[max(0, m.start() - 300):m.end() + 100]
        if any(r in win for r in FINANCE_ROLES) or re.search(r"\b(?:cfo|cao)\b", win):
            return "finance officer departure", body[max(0, m.start() - 200):m.end() + 80].strip()
    m = re.search(r"\b(?:" + "|".join(re.escape(w) for w in CHANGE) + ")", body)
    if m:
        return "officer or director change", body[max(0, m.start() - 150):m.end() + 80].strip()
    return "pay plan only", body[:220]

def classify_recent_502(gov, today=None):
    """Read each item-5.02 8-K from the last 183 days (at most 8) and label what it is."""
    import requests
    email = os.environ.get("SEC_IDENTITY_EMAIL", "user@example.com")
    cutoff = str((today or datetime.utcnow().date()) - timedelta(days=183))
    n = 0
    for w in gov.get("watch") or []:
        if "item 5.02" not in w.get("issue", "") or w.get("date", "") < cutoff or n >= 8:
            continue
        n += 1
        try:
            r = requests.get(w["url"], headers={"User-Agent": f"qanicuq {email}"}, timeout=30)
            r.raise_for_status()
            w["kind"], w["sentence"] = classify_502(r.text)
        except Exception as e:
            w["kind"], w["sentence"] = "unread", f"could not read the filing ({type(e).__name__})"

def governance_from_submissions(sub, today=None):
    """Return (governance dict, display filings list) from a data.sec.gov submissions JSON."""
    rec = sub.get("filings", {}).get("recent", {})
    forms, dates, items, accns, docs = (rec.get(k, []) for k in ("form", "filingDate", "items", "accessionNumber", "primaryDocument"))
    cik = int(sub.get("cik", 0) or 0)
    today = today or datetime.utcnow().date()
    cutoff = str(today - timedelta(days=730))
    gov = {"window": "last 24 months", "walk_away": [], "watch": [], "special_situations": [], "dilution_filings": [], "amendments": []}
    shown = []
    for i, form in enumerate(forms):
        date = dates[i] if i < len(dates) else ""
        accn = accns[i] if i < len(accns) else ""
        doc = docs[i] if i < len(docs) else ""
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accn.replace('-', '')}/{doc}" if accn and doc else ""
        if form in ("10-K", "10-Q", "8-K", "20-F", "40-F", "6-K", "10-K/A", "10-Q/A", "DEF 14A") and len(shown) < 5:
            shown.append({"form": form, "date": date, "url": url})
        if date < cutoff:
            continue
        entry = {"form": form, "date": date, "url": url}
        if form.startswith("NT 10-K") or form.startswith("NT 10-Q") or form.startswith("NT 20-F"):
            gov["walk_away"].append({**entry, "issue": f"Late filing notice ({form})"})
        if form in ("10-K/A", "10-Q/A"):
            gov["amendments"].append({**entry, "issue": f"Amended report ({form}); check whether it restates numbers or only adds Part III"})
        if form.startswith("8-K"):
            its = [x.strip() for x in str(items[i] if i < len(items) else "").split(",") if x.strip()]
            for it in its:
                if it in WALK_AWAY_ITEMS:
                    gov["walk_away"].append({**entry, "issue": WALK_AWAY_ITEMS[it]})
                elif it in WATCH_ITEMS:
                    gov["watch"].append({**entry, "issue": WATCH_ITEMS[it]})
        if form in SPECIAL_FORMS:
            gov["special_situations"].append({**entry, "issue": SPECIAL_FORMS[form]})
        if form in DILUTION_FORMS:
            gov["dilution_filings"].append(entry)
    for k in ("watch", "special_situations", "dilution_filings", "amendments"):
        gov[k] = gov[k][:12]
    return gov, shown

ANNUAL_TAGS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "acquisitions": ["PaymentsToAcquireBusinessesNetOfCashAcquired"],
    # extra lines for settling a Webull-vs-SEC mismatch (the cloud helper can't reach the SEC, so they travel here)
    "revenue_total": ["Revenues"],
    "revenue_contract": ["RevenueFromContractWithCustomerExcludingAssessedTax", "RevenueFromContractWithCustomerIncludingAssessedTax"],
    "gross_profit": ["GrossProfit"],
    "operating_expenses": ["OperatingExpenses", "CostsAndExpenses"],
    "sga": ["SellingGeneralAndAdministrativeExpense"],
    "research_development": ["ResearchAndDevelopmentExpense"],
    "restructuring": ["RestructuringCharges"],
    "impairment": ["GoodwillImpairmentLoss", "AssetImpairmentCharges"],
    "interest_expense": ["InterestExpense", "InterestExpenseNonoperating"],
    "pretax_income": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                      "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"],
}

# foreign filers using international accounting rules (IFRS) tag their 20-F/40-F figures with these names instead
IFRS_TAGS = {
    "revenue": ["Revenue", "RevenueFromContractsWithCustomers"],
    "operating_income": ["ProfitLossFromOperatingActivities"],
    "net_income": ["ProfitLossAttributableToOwnersOfParent", "ProfitLoss"],
    "cfo": ["CashFlowsFromUsedInOperatingActivities"],
    "capex": ["PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities", "PurchaseOfPropertyPlantAndEquipment"],
    "acquisitions": ["CashFlowsUsedInObtainingControlOfSubsidiariesOrOtherBusinessesClassifiedAsInvestingActivities"],
    "revenue_total": ["Revenue"],
    "revenue_contract": ["RevenueFromContractsWithCustomers"],
    "gross_profit": ["GrossProfit"],
    "operating_expenses": [],
    "sga": ["SellingGeneralAndAdministrativeExpense"],
    "research_development": ["ResearchAndDevelopmentExpense"],
    "restructuring": [],
    "impairment": ["ImpairmentLossRecognisedInProfitOrLoss"],
    "interest_expense": ["FinanceCosts", "InterestExpense"],
    "pretax_income": ["ProfitLossBeforeTax"],
}
ANNUAL_FORMS = ("10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A")

def report_currency(tax, tags):
    """The currency the company reports its revenue in (USD, EUR, INR, ...): the unit with the newest annual figure."""
    best = None
    for tag in tags:
        for unit, entries in tax.get(tag, {}).get("units", {}).items():
            ends = [e["end"] for e in entries if e.get("form") in ANNUAL_FORMS and "start" in e]
            if ends and (best is None or max(ends) > best[1]):
                best = (unit, max(ends))
    return best[0] if best else None

def annual_series(gaap, tags, years=5, unit="USD"):
    """Fiscal-year values from 10-K/20-F/40-F filings: {fy_end: value}, newest first, using the tag with the latest data."""
    best = {}
    for tag in tags:
        units = gaap.get(tag, {}).get("units", {}).get(unit, [])
        vals = {}
        for e in units:
            if e.get("form") not in ANNUAL_FORMS or "start" not in e:
                continue
            if not 350 <= days(e) <= 380:
                continue
            if e["end"] not in vals or e["filed"] > vals[e["end"]]["filed"]:
                vals[e["end"]] = e
        if vals and (not best or max(vals) > max(best)):
            best = vals
    return {end: round2(best[end]["val"]) for end in sorted(best, reverse=True)[:years]}

try:
    from edgar import Company as _Co
    _cik = int(_Co(TICKER).cik)
    packet["cik"] = _cik  # lets the worker link straight to the SEC figures when sources disagree
    gov, shown = governance_from_submissions(sec_get(f"https://data.sec.gov/submissions/CIK{_cik:010d}.json"))
    classify_recent_502(gov)
    packet["governance"] = gov
    if shown:
        packet["filings"] = shown  # 10-K/10-Q/8-K first, instead of the newest five of any form (often Form 4s)
except Exception as e:
    packet["errors"].append(f"sec submissions: {type(e).__name__}: {str(e)[:120]}")

try:
    tax_name, tags_map = "us-gaap", ANNUAL_TAGS
    if facts and FOREIGN_FORM and not report_currency(facts.get("us-gaap", {}), ANNUAL_TAGS["revenue"]):
        tax_name, tags_map = "ifrs-full", IFRS_TAGS
    gaap_all = facts.get(tax_name, {}) if facts else {}
    cur_unit = report_currency(gaap_all, tags_map["revenue"]) if gaap_all else None
    if gaap_all and cur_unit:
        packet["annual"] = {k: annual_series(gaap_all, tags, unit=cur_unit) for k, tags in tags_map.items()}
        fcf_acq = {}
        for end, cfo in packet["annual"]["cfo"].items():
            capex = packet["annual"]["capex"].get(end) or 0
            acq = packet["annual"]["acquisitions"].get(end) or 0
            if cfo is not None:
                fcf_acq[end] = round2(cfo - capex - acq)
        packet["annual"]["fcf_after_acquisitions"] = fcf_acq
        # some companies file no operating-income line (e.g. Nike); build it from the filed lines so it can still be
        # checked: gross profit minus selling/admin and R&D. A gap the build can't explain goes to the settle step.
        an = packet["annual"]
        oi, rd = an["operating_income"], an.get("research_development") or {}
        # only under US rules: IFRS income statements carry other operating lines this simple build would miss
        built = [y for y, gp in an["gross_profit"].items() if y not in oi and an["sga"].get(y) is not None] if tax_name == "us-gaap" else []
        for y in built:
            oi[y] = round2(an["gross_profit"][y] - an["sga"][y] - (rd.get(y) or 0))
        an["operating_income"] = dict(sorted(oi.items(), reverse=True))
        if built:
            an["operating_income_basis"] = ("built from SEC gross profit minus selling and admin" + (" minus R&D" if rd else "")
                                            + " for fiscal years ending " + ", ".join(sorted(built, reverse=True))
                                            + " (no operating-income line filed)")
        packet["annual"]["note"] = (f"Fiscal years from {FOREIGN_FORM or '10-K'} XBRL ({tax_name}), in {cur_unit}, newest first. "
                                    "capex and acquisitions are cash paid (positive).")
        packet["annual"]["currency"] = cur_unit
        packet["annual"]["taxonomy"] = tax_name
        packet["annual"]["newest_end"] = max(packet["annual"]["revenue"]) if packet["annual"]["revenue"] else None
except Exception as e:
    packet["errors"].append(f"sec annual: {type(e).__name__}: {str(e)[:120]}")

# ---------- 4. fredapi ----------
try:
    from fredapi import Fred
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise ValueError("FRED_API_KEY not set")
    fred = Fred(api_key=key)
    series = {
        "DGS3MO": "3m_treasury",
        "DGS10": "10y_treasury",
        "FEDFUNDS": "fed_funds",
        "CPIAUCSL": "cpi_yoy_pct",
        "UNRATE": "unemployment",
    }
    for code, name in series.items():
        s = fred.get_series(code)
        if s is not None and not s.empty:
            s = s.dropna()
            latest = s.iloc[-1]
            if code == "CPIAUCSL":  # index level -> % change vs 12 months earlier
                latest = (s.iloc[-1] / s.iloc[-13] - 1) * 100
            date = s.index[-1].strftime("%Y-%m-%d")
            packet["macro"][name] = {"value": round2(latest), "date": date}
except Exception as e:
    packet["errors"].append(f"fredapi: {type(e).__name__}: {str(e)[:120]}")

# ---------- 4b. the S&P 500's own P/E and P/B (Dreman Rule 21: sell when no longer cheap vs the market) ----------
# Source: Yahoo's holdings table for SPY. Its "Price/Earnings" and "Price/Book" rows are earnings and book YIELDS
# (0.0416 = 4.16%), so the ratios are their inverse; tested 2026-11-06: P/E 24.0, P/B 5.08 vs multpl.com 25.1 and 5.27.
# Yahoo's own SPY "priceToBook" field (1.71) is not the index's P/B and is not used.
try:
    import yfinance as yf
    eh = yf.Ticker("SPY").funds_data.equity_holdings
    col = "SPY" if "SPY" in eh.columns else eh.columns[0]
    ep, bp = float(eh.loc["Price/Earnings", col]), float(eh.loc["Price/Book", col])
    mpe, mpb = round2(1 / ep), round2(1 / bp)
    spy_pe = round2((yf.Ticker("SPY").info or {}).get("trailingPE"))
    if not (8 <= mpe <= 60 and 1 <= mpb <= 12):
        raise ValueError(f"out of range: P/E {mpe}, P/B {mpb}")
    packet["market"] = {"pe": mpe, "pb": mpb, "spy_trailing_pe": spy_pe, "index": "S&P 500 (SPY holdings)",
                        "date": datetime.utcnow().strftime("%Y-%m-%d"), "source": "yfinance SPY equity_holdings (inverse of the yields)"}
except Exception as e:
    packet["errors"].append(f"market P/E: {type(e).__name__}: {str(e)[:120]}")

# ---------- 5. CCXT only for crypto-linked ----------
CRYPTO_TICKERS = {"BTC", "ETH", "COIN", "MSTR", "IBIT", "GBTC", "ETHE", "BITO"}
if TICKER in CRYPTO_TICKERS or TICKER.endswith("-USD"):
    try:
        import ccxt
        coinbase = ccxt.coinbase()
        kraken = ccxt.kraken()
        btc_cb = coinbase.fetch_ticker("BTC/USD")["last"]
        btc_kr = kraken.fetch_ticker("BTC/USD")["last"]
        eth_cb = coinbase.fetch_ticker("ETH/USD")["last"]
        eth_kr = kraken.fetch_ticker("ETH/USD")["last"]
        packet["crypto"] = {
            "btc_coinbase": round2(btc_cb),
            "btc_kraken": round2(btc_kr),
            "btc_spread_pct": round2(abs(btc_cb - btc_kr) / ((btc_cb + btc_kr) / 2) * 100),
            "eth_coinbase": round2(eth_cb),
            "eth_kraken": round2(eth_kr),
            "eth_spread_pct": round2(abs(eth_cb - eth_kr) / ((eth_cb + eth_kr) / 2) * 100),
        }
    except Exception as e:
        packet["errors"].append(f"ccxt: {type(e).__name__}: {str(e)[:120]}")
        packet["crypto"] = None
else:
    packet["crypto"] = None

# ---------- 6. News headlines (Google News RSS, last 30 days; earnings search 100 days; no cap) ----------
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import timezone
import requests
NEWS_QUERIES = [
    f"{TICKER} stock news",
    f"{company_name}",
    f"{company_name} earnings",
    f"{company_name} activist OR spinoff OR restatement OR auditor",
    f"{company_name} removed from index OR index deletion OR fund redemptions OR fund selling OR stake cut",
]
# a headline counts only if it names the company, or names the ticker as a stock (short tickers like SMP match unrelated news)
news_core = " ".join(re.sub(r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|plc|llc|lp|sa|nv|ag|se|holdings?|group|class [a-z])\b", " ", re.sub(r"[,.]", " ", company_name), flags=re.I).split())
news_t = re.escape(TICKER)
NEWS_FIN = r"stocks?|shares|earnings|investors?|price target|target|analysts?|rating|upgrades?|downgrades?|buy|sell|valuation|dividend|quarter|Q[1-4]|guidance|outlook|revenue|sales|profit|CEO|CFO|falls|drops|rises|jumps|gains|slides|surges|plunges|tumbles"
def news_about(title):
    if news_core and re.search(r"\b" + re.escape(news_core) + r"\b", title, re.I):
        return True
    if re.search(r"(\$" + news_t + r"\b|\(" + news_t + r"[):]|:" + news_t + r"\b|\b" + news_t + r"['’]s\b)", title):
        return True
    return bool(re.search(r"\b" + news_t + r"\b", title) and re.search(r"\b(" + NEWS_FIN + r")\b", title, re.I))
news_items = []
news_seen = set()
news_dropped = 0
for query in NEWS_QUERIES:
    news_days = 100 if query == f"{company_name} earnings" else 30  # the last quarterly report is often more than 30 days old
    news_cutoff = datetime.now(timezone.utc) - timedelta(days=news_days)
    try:
        r = requests.get("https://news.google.com/rss/search", params={"q": query + f" when:{news_days}d", "hl": "en-US", "gl": "US", "ceid": "US:en"}, headers={"User-Agent": "Mozilla/5.0 (ticker-forensics-data packet)"}, timeout=20)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            link = it.findtext("link") or ""
            pub = it.findtext("pubDate") or ""
            source = (it.findtext("source") or "").strip()
            if source and title.endswith(" - " + source):
                title = title[: -len(" - " + source)]
            try:
                dt = parsedate_to_datetime(pub)
            except Exception:
                dt = None
            if dt is not None and dt < news_cutoff:
                continue
            key = re.sub(r"\s+", " ", title.lower()).strip()
            if key == "" or key in news_seen:
                continue
            if not news_about(title):
                news_dropped += 1
                continue
            news_seen.add(key)
            news_items.append({"date": dt.strftime("%Y-%m-%d") if dt else None, "source": source, "title": title, "link": link, "query": query})
    except Exception as e:
        packet["errors"].append(f"news ({query}): {type(e).__name__}: {str(e)[:120]}")
news_items.sort(key=lambda x: x["date"] or "", reverse=True)
packet["news"] = {"source": "Google News RSS", "window": "last 30 days (earnings search: last 100 days)", "queries": NEWS_QUERIES, "count": len(news_items), "dropped_not_about_company": news_dropped, "items": news_items}
# ---------- 7. Latest earnings press release (8-K item 2.02, exhibit EX-99.1) ----------
packet["earnings_release"] = None
try:
    from edgar import Company as _Co
    er_cik = int(_Co(TICKER).cik)
    er_sub = sec_get(f"https://data.sec.gov/submissions/CIK{er_cik:010d}.json")
    er_rec = er_sub.get("filings", {}).get("recent", {})
    er_forms = er_rec.get("form") or []
    er_dates = er_rec.get("filingDate") or []
    er_items_list = er_rec.get("items") or []
    er_accns = er_rec.get("accessionNumber") or []
    er_cutoff = str(datetime.utcnow().date() - timedelta(days=120))
    er_filed = None
    er_accn = None
    for er_i, er_form in enumerate(er_forms):
        er_date = er_dates[er_i] if er_i < len(er_dates) else ""
        er_items_text = str(er_items_list[er_i]) if er_i < len(er_items_list) else ""
        if er_form == "8-K" and "2.02" in er_items_text and er_date >= er_cutoff:
            er_filed = er_date
            er_accn = er_accns[er_i] if er_i < len(er_accns) else ""
            break
    if not er_filed:
        packet["errors"].append("earnings release: no 8-K item 2.02 filed in the last 120 days")
    else:
        er_accn_nd = er_accn.replace("-", "")
        er_index_url = f"https://www.sec.gov/Archives/edgar/data/{er_cik}/{er_accn_nd}/{er_accn}-index.htm"
        import requests
        import html
        er_email = os.environ.get("SEC_IDENTITY_EMAIL", "user@example.com")
        er_idx_resp = requests.get(er_index_url, headers={"User-Agent": f"qanicuq {er_email}"}, timeout=30)
        er_idx_resp.raise_for_status()
        er_href = None
        er_href_fallback = None
        for er_row in re.findall(r"<tr\b[^>]*>.*?</tr>", er_idx_resp.text, flags=re.S | re.I):
            er_tds = re.findall(r"<td\b[^>]*>(.*?)</td>", er_row, flags=re.S | re.I)
            er_texts = []
            for er_td in er_tds:
                er_plain = re.sub(r"<[^>]+>", " ", er_td)
                er_plain = html.unescape(er_plain).replace("\xa0", " ")
                er_plain = re.sub(r"\s+", " ", er_plain).strip()
                er_texts.append(er_plain)
            er_m = re.search(r"""href\s*=\s*["']([^"']+)["']""", er_row, flags=re.I)
            er_row_href = er_m.group(1) if er_m else None
            if not er_row_href:
                continue
            if any(t == "EX-99.1" for t in er_texts):
                er_href = er_row_href
                break
            if er_href_fallback is None and any(t.startswith("EX-99") for t in er_texts):
                er_href_fallback = er_row_href
        if er_href is None:
            er_href = er_href_fallback
        if not er_href:
            packet["errors"].append(f"earnings release: no EX-99 exhibit in {er_index_url}")
        else:
            if er_href.startswith("/ix?doc="):
                er_href = er_href[len("/ix?doc="):]
            if er_href.startswith("/"):
                er_href = "https://www.sec.gov" + er_href
            er_ex = requests.get(er_href, headers={"User-Agent": f"qanicuq {er_email}"}, timeout=30)
            er_ex.raise_for_status()
            er_text = er_ex.text
            er_text = re.sub(r"<script\b[^>]*>.*?</script>", " ", er_text, flags=re.S | re.I)
            er_text = re.sub(r"<style\b[^>]*>.*?</style>", " ", er_text, flags=re.S | re.I)
            er_text = re.sub(r"<br\s*/?>", "\n", er_text, flags=re.I)
            er_text = re.sub(r"</p\s*>", "\n", er_text, flags=re.I)
            er_text = re.sub(r"</div\s*>", "\n", er_text, flags=re.I)
            er_text = re.sub(r"</tr\s*>", "\n", er_text, flags=re.I)
            er_text = re.sub(r"</h[1-6]\s*>", "\n", er_text, flags=re.I)
            er_text = re.sub(r"</td\s*>", " | ", er_text, flags=re.I)
            er_text = re.sub(r"</th\s*>", " | ", er_text, flags=re.I)
            er_text = re.sub(r"<[^>]+>", " ", er_text)
            er_text = html.unescape(er_text)
            er_text = er_text.replace("\xa0", " ")
            er_lines = []
            for er_line in er_text.split("\n"):
                er_line = re.sub(r" +", " ", er_line).strip()
                if er_line == "" or set(er_line) <= {"|", " "}:
                    continue
                er_lines.append(er_line)
            er_text = "\n".join(er_lines)
            packet["earnings_release"] = {
                "source": "SEC 8-K item 2.02, exhibit EX-99.1 (company press release)",
                "filed": er_filed,
                "accession": er_accn,
                "index_url": er_index_url,
                "url": er_href,
                "chars_total": len(er_text),
                "truncated": True if len(er_text) > 20000 else False,
                "text": er_text[:20000],
            }
except Exception as e:
    packet["errors"].append(f"earnings release: {type(e).__name__}: {str(e)[:120]}")
with open(OUT_PATH, "w") as f:
    json.dump(packet, f, separators=(",", ":"), default=str)

size_kb = OUT_PATH.stat().st_size / 1024
print(f"Wrote {OUT_PATH} ({size_kb:.2f} KB)")
print(f"News headlines: {packet.get('news', {}).get('count', 0)}")
print(f"Earnings release: {(packet.get('earnings_release') or {}).get('filed', 'none')} ({(packet.get('earnings_release') or {}).get('chars_total', 0)} chars)")
print(f"Mismatches: {len(packet['cross_check']['mismatches'])}, Errors: {len(packet['errors'])}")
if packet["errors"]:
    print("Errors:", packet["errors"])
