#!/usr/bin/env python3
"""Cheap options scanner: finds options where IV << HV20."""

import csv
import json
import math
import os
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
import yfinance as yf


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_price(spot: float, strike: float, t: float, r: float, sigma: float, is_call: bool) -> float:
    if t <= 0 or sigma <= 0:
        return max(0.0, (spot - strike) if is_call else (strike - spot))
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    if is_call:
        return spot * norm_cdf(d1) - strike * math.exp(-r * t) * norm_cdf(d2)
    else:
        return strike * math.exp(-r * t) * norm_cdf(-d2) - spot * norm_cdf(-d1)


def implied_vol(spot: float, strike: float, t: float, r: float, mid: float, is_call: bool) -> float | None:
    if t <= 0 or mid <= 0:
        return None
    low, high = 0.01, 5.00
    # Check if mid is outside the range
    price_low = bs_price(spot, strike, t, r, low, is_call)
    price_high = bs_price(spot, strike, t, r, high, is_call)
    if mid < price_low or mid > price_high:
        return None
    for _ in range(100):
        mid_sigma = (low + high) / 2.0
        price = bs_price(spot, strike, t, r, mid_sigma, is_call)
        if abs(price - mid) < 0.0001:
            return mid_sigma
        if price > mid:
            high = mid_sigma
        else:
            low = mid_sigma
    return (low + high) / 2.0


def get_sp500() -> list[str]:
    url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(pd.io.common.StringIO(resp.text))
    symbols = df["Symbol"].astype(str).tolist()
    return [s.replace(".", "-") for s in symbols]


def get_watchlist() -> list[str]:
    path = "screens/cheap_options_watchlist.txt"
    if not os.path.exists(path):
        return []
    tickers = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                tickers.append(line.upper())
    return tickers


def get_diamond() -> list[str]:
    path = "screens/diamond_screen.json"
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return [str(t).upper() for t in data.get("all_passing", [])]
    except Exception:
        return []


ALERTS_PATH = "screens/cheap_options_alerts.csv"
ALERT_FIELDS = ["alert_date", "ticker", "expiration", "strike", "spot", "call_mid", "put_mid",
                "iv", "hv20", "ratio", "close_at_exp", "straddle_value", "straddle_pnl_pct"]


def read_alerts() -> list[dict]:
    if not os.path.exists(ALERTS_PATH):
        return []
    with open(ALERTS_PATH, newline="") as f:
        return list(csv.DictReader(f))


def write_alerts(rows: list[dict]) -> None:
    with open(ALERTS_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ALERT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def fill_outcome(row: dict, close_at_exp: float) -> None:
    """Value of buying both the call and the put (a straddle), held to expiration."""
    strike = float(row["strike"])
    paid = float(row["call_mid"]) + float(row["put_mid"])
    value = abs(close_at_exp - strike)
    row["close_at_exp"] = round(close_at_exp, 2)
    row["straddle_value"] = round(value, 2)
    row["straddle_pnl_pct"] = round((value - paid) / paid * 100, 1)


def update_outcomes(rows: list[dict], today) -> None:
    for row in rows:
        if row.get("close_at_exp"):
            continue
        exp = datetime.strptime(row["expiration"], "%Y-%m-%d").date()
        if exp >= today:
            continue
        try:
            h = yf.Ticker(row["ticker"]).history(start=exp - timedelta(days=7), end=exp + timedelta(days=1))
            closes = h["Close"].dropna()
            closes = closes[[d.date() <= exp for d in closes.index]]
            if closes.empty:
                continue
            fill_outcome(row, float(closes.iloc[-1]))
        except Exception:
            continue


def track_record(rows: list[dict]) -> str:
    done = [float(r["straddle_pnl_pct"]) for r in rows if r.get("straddle_pnl_pct")]
    if not done:
        return f"Track record: {len(rows)} alerts logged, none expired yet."
    wins = sum(1 for p in done if p > 0)
    avg = sum(done) / len(done)
    return (f"Track record: {len(done)} finished alerts. Buying both the call and put on each "
            f"made money {wins} of {len(done)} times, average {avg:+.1f}% per alert.")


def main():
    print("Starting cheap options scan")
    sp500 = get_sp500()
    watch = get_watchlist()
    diamond = get_diamond()
    your_list = set(watch) | set(diamond)
    full = list(dict.fromkeys(sp500 + watch + diamond))  # preserve order, unique
    print(f"Universe size: {len(full)} (S&P {len(sp500)}, watch {len(watch)}, diamond {len(diamond)})")

    # Risk-free rate
    irx = yf.Ticker("^IRX")
    irx_hist = irx.history(period="5d")
    if irx_hist.empty:
        print("Could not get risk-free rate")
        sys.exit(1)
    rf = float(irx_hist["Close"].iloc[-1]) / 100.0
    print(f"Risk-free rate: {rf:.4f}")

    ny = ZoneInfo("America/New_York")
    today_ny = datetime.now(ny).date()

    # Market open check
    spy = yf.Ticker("SPY")
    spy_hist = spy.history(period="5d")
    if spy_hist.empty:
        print("Could not get SPY prices")
        sys.exit(1)
    last_spy_date = spy_hist.index[-1].date()
    if last_spy_date != today_ny:
        print("Market closed today, nothing to do")
        sys.exit(0)

    results = []
    errors = 0
    earnings_skipped = 0
    scanned = 0

    for ticker in full:
        scanned += 1
        time.sleep(0.3)
        try:
            tk = yf.Ticker(ticker)
            hist = tk.history(period="3mo")
            if len(hist) < 21:
                continue
            closes = hist["Close"].dropna()
            if len(closes) < 21:
                continue
            spot = float(closes.iloc[-1])
            if spot < 5.0:
                continue

            # HV20
            last21 = closes.iloc[-21:]
            log_rets = np.log(last21 / last21.shift(1)).dropna()
            if len(log_rets) < 20:
                continue
            hv20 = float(log_rets.std(ddof=1) * math.sqrt(252))
            if hv20 <= 0 or math.isnan(hv20):
                continue
            # Same HV20 with the single biggest daily move removed. If an option only looks
            # cheap because of one jump day (news, FDA, lawsuit), it is not really cheap.
            biggest = log_rets.abs().idxmax()
            hv20_ex = float(log_rets.drop(biggest).std(ddof=1) * math.sqrt(252))

            # Expirations
            expirations = tk.options
            if not expirations:
                continue
            best_exp = None
            best_diff = 999
            for exp_str in expirations:
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
                days = (exp_date - today_ny).days
                if 20 <= days <= 45:
                    diff = abs(days - 30)
                    if diff < best_diff:
                        best_diff = diff
                        best_exp = exp_str
            if best_exp is None:
                continue
            exp_date = datetime.strptime(best_exp, "%Y-%m-%d").date()
            days_to_exp = (exp_date - today_ny).days
            t_years = days_to_exp / 365.0

            # Earnings: skip if earnings fall anywhere from 31 days ago up to expiration.
            # Past earnings matter: an earnings jump inside the last 20 trading days inflates HV20
            # and makes options look falsely cheap.
            earnings_unknown = False
            skip_earnings = False
            try:
                ed_df = tk.get_earnings_dates(limit=8)
                if ed_df is None or ed_df.empty:
                    earnings_unknown = True
                else:
                    window_start = today_ny - timedelta(days=31)
                    for ts in ed_df.index:
                        if window_start <= ts.date() <= exp_date:
                            skip_earnings = True
                            break
            except Exception:
                earnings_unknown = True
            if skip_earnings:
                earnings_skipped += 1
                continue

            # Option chain
            chain = tk.option_chain(best_exp)
            calls = chain.calls
            puts = chain.puts
            if calls.empty or puts.empty:
                continue

            # ATM strike present in both
            common_strikes = set(calls["strike"]) & set(puts["strike"])
            if not common_strikes:
                continue
            atm_strike = min(common_strikes, key=lambda k: abs(k - spot))

            call_row = calls[calls["strike"] == atm_strike].iloc[0]
            put_row = puts[puts["strike"] == atm_strike].iloc[0]

            def mid_and_quality(row):
                bid = float(row.get("bid", 0) or 0)
                ask = float(row.get("ask", 0) or 0)
                oi = int(row.get("openInterest", 0) or 0)
                if bid <= 0 or ask <= 0:
                    return None, False
                mid = (bid + ask) / 2.0
                if mid <= 0:
                    return None, False
                spread = (ask - bid) / mid
                if spread > 0.10 or oi < 100:
                    return None, False
                return mid, True

            call_mid, call_ok = mid_and_quality(call_row)
            put_mid, put_ok = mid_and_quality(put_row)
            if not call_ok or not put_ok:
                continue

            # IV
            call_iv = implied_vol(spot, atm_strike, t_years, rf, call_mid, True)
            put_iv = implied_vol(spot, atm_strike, t_years, rf, put_mid, False)
            if call_iv is None or put_iv is None:
                continue
            iv = (call_iv + put_iv) / 2.0
            ratio = iv / hv20 if hv20 > 0 else None
            if ratio is None or math.isnan(ratio):
                continue
            ratio_ex = iv / hv20_ex if hv20_ex > 0 else 999.0

            results.append({
                "ticker": ticker,
                "spot": round(spot, 2),
                "expiration": best_exp,
                "days": days_to_exp,
                "strike": atm_strike,
                "call_mid": round(call_mid, 2),
                "put_mid": round(put_mid, 2),
                "iv": round(iv, 4),
                "hv20": round(hv20, 4),
                "ratio": round(ratio, 4),
                "ratio_ex": round(ratio_ex, 4),
                "your_list": ticker in your_list,
                "earnings_unknown": earnings_unknown,
            })
        except Exception as e:
            errors += 1
            # print(f"Error on {ticker}: {e}")  # keep quiet unless debugging
            continue

    print(f"Scanned: {scanned}, passed: {len(results)}, errors: {errors}")
    print(f"Skipped for earnings: {earnings_skipped}")

    if errors > len(full) / 2:
        print(f"Too many errors: {errors}")
        sys.exit(1)

    # Append to history
    hist_path = "screens/iv_history.csv"
    file_exists = os.path.exists(hist_path)
    with open(hist_path, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["ticker", "date", "iv", "hv20", "cheap_ratio"])
        for r in results:
            writer.writerow([r["ticker"], today_ny.isoformat(), r["iv"], r["hv20"], r["ratio"]])

    results_sorted = sorted(results, key=lambda x: x["ratio"])

    # Hits: must still look cheap with the single biggest move day removed
    def is_cheap(r):
        return r["ratio"] <= 0.75 and r["ratio_ex"] <= 0.75
    market_hits = [r for r in results_sorted if is_cheap(r)][:5]
    your_hits = [r for r in results_sorted if r["your_list"] and is_cheap(r)][:10]
    one_day_skipped = sum(1 for r in results_sorted if r["ratio"] <= 0.75 and r["ratio_ex"] > 0.75)
    print(f"Skipped (only cheap because of one big move day): {one_day_skipped}")

    # Alert log: fill in finished alerts, then add today's real alerts (once per ticker per day)
    alert_rows = read_alerts()
    update_outcomes(alert_rows, today_ny)
    logged = {(r["alert_date"], r["ticker"]) for r in alert_rows}
    for r in market_hits + your_hits:
        key = (today_ny.isoformat(), r["ticker"])
        if key in logged:
            continue
        logged.add(key)
        alert_rows.append({
            "alert_date": today_ny.isoformat(), "ticker": r["ticker"], "expiration": r["expiration"],
            "strike": r["strike"], "spot": r["spot"], "call_mid": r["call_mid"], "put_mid": r["put_mid"],
            "iv": r["iv"], "hv20": r["hv20"], "ratio": r["ratio"],
            "close_at_exp": "", "straddle_value": "", "straddle_pnl_pct": "",
        })
    write_alerts(alert_rows)
    record = track_record(alert_rows)
    print(record)

    # Write markdown
    md_lines = [
        f"# Cheap Options Scan",
        f"Run: {datetime.now(ny).strftime('%Y-%m-%d %H:%M %Z')}",
        "",
        "| Ticker | Spot | Exp | Days | Strike | Call | Put | IV | HV20 | Ratio | Your list | Earnings unk |",
        "|--------|------|-----|------|--------|------|-----|----|------|-------|-----------|--------------|",
    ]
    for r in results_sorted:
        md_lines.append(
            f"| {r['ticker']} | {r['spot']} | {r['expiration']} | {r['days']} | {r['strike']} | "
            f"{r['call_mid']} | {r['put_mid']} | {r['iv']} | {r['hv20']} | {r['ratio']} | "
            f"{'Y' if r['your_list'] else ''} | {'Y' if r['earnings_unknown'] else ''} |"
        )
    md_lines.append("")
    md_lines.append(
        "Cheap ratio = option-implied move ÷ the stock's actual move over the last 20 trading days. "
        "Under 0.75 = unusually cheap. Not advice; when you buy an option, the most you can lose is what you paid."
    )
    md_lines.append("")
    md_lines.append(
        "Alerts also need the ratio to stay under 0.75 with the stock's single biggest move day removed, "
        "so one news jump can't make an option look cheap."
    )
    md_lines.append("")
    md_lines.append(record + " Full log: cheap_options_alerts.csv")
    with open("screens/cheap_options.md", "w") as f:
        f.write("\n".join(md_lines) + "\n")

    test_ping = os.environ.get("TEST_PING") == "1"
    if not market_hits and not your_hits:
        if test_ping:
            market_hits = results_sorted[:5]
            prefix = "TEST "
        else:
            print("Nothing unusually cheap today")
            sys.exit(0)
    else:
        prefix = ""

    # Message
    lines = []
    if market_hits:
        lines.append("Market-wide:")
        for r in market_hits:
            extra = " (earnings date unknown — check)" if r["earnings_unknown"] else ""
            lines.append(
                f"{r['ticker']} exp {r['expiration']}, ${r['strike']} strike: "
                f"call ${r['call_mid']:.2f} / put ${r['put_mid']:.2f} — "
                f"option expects {r['iv']*100:.0f}% move, stock really moving {r['hv20']*100:.0f}% "
                f"(ratio {r['ratio']:.2f}){extra}"
            )
    if your_hits:
        lines.append("Your list:")
        for r in your_hits:
            extra = " (earnings date unknown — check)" if r["earnings_unknown"] else ""
            lines.append(
                f"{r['ticker']} exp {r['expiration']}, ${r['strike']} strike: "
                f"call ${r['call_mid']:.2f} / put ${r['put_mid']:.2f} — "
                f"option expects {r['iv']*100:.0f}% move, stock really moving {r['hv20']*100:.0f}% "
                f"(ratio {r['ratio']:.2f}){extra}"
            )
    message = prefix + "\n".join(lines)
    with open("ntfy_message.txt", "w") as f:
        f.write(message + "\n")
    print("Wrote ntfy_message.txt")


if __name__ == "__main__":
    main()
