#!/usr/bin/env python3
"""TEMPORARY dry run (branch crosscheck-fixes only, never merged): the SEC side of the fixed cross-check for a list of
tickers, using generate_packet.py's own functions, so the new checks can be tested without building full packets."""
import ast, json, os, sys
from datetime import datetime
import requests
from edgar import Company, set_identity

email = os.environ.get("SEC_IDENTITY_EMAIL", "user@example.com")
set_identity(f"qanicuq <{email}>")
src = open("generate_packet.py").read()
keep = {"round2", "days", "last_4_quarters", "pick_revenue_tag", "annual_series", "ANNUAL_TAGS"}
mod = ast.Module(body=[n for n in ast.parse(src).body
                       if (isinstance(n, ast.FunctionDef) and n.name in keep)
                       or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in keep for t in n.targets))], type_ignores=[])
import pandas as pd
G = {"pd": pd}
exec(compile(mod, "generate_packet.py", "exec"), G)
H = {"User-Agent": f"qanicuq {email}"}
out = {}
for t in sys.argv[1:]:
    r = {"errors": []}
    try:
        cik = int(Company(t).cik)
        r["cik"] = cik
        forms = requests.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers=H, timeout=30).json()["filings"]["recent"]["form"]
        annual = next((f for f in forms if f in ("10-K", "20-F", "40-F")), None)
        if annual in ("20-F", "40-F"):
            r["foreign"] = annual
            out[t] = r
            continue
        facts = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", headers=H, timeout=30).json()["facts"]
        gaap = facts.get("us-gaap", {})
        # shares: same lines as generate_packet.py
        total_shares, stale_end = None, None
        for s in (facts.get("dei", {}).get("EntityCommonStockSharesOutstanding", {}), gaap.get("CommonStockSharesOutstanding", {})):
            shares = s.get("units", {}).get("shares", [])
            if not shares:
                continue
            latest_accn = max(shares, key=lambda e: (e["filed"], e["end"]))["accn"]
            latest = [e for e in shares if e["accn"] == latest_accn]
            latest_end = max(e["end"] for e in latest)
            if (datetime.utcnow() - datetime.fromisoformat(latest_end)).days > 400:
                stale_end = stale_end or latest_end
                continue
            total_shares = sum(e["val"] for e in latest if e["end"] == latest_end)
            r["shares_end"] = latest_end
            break
        r["shares"] = total_shares
        r["shares_stale_end"] = stale_end
        tag = G["pick_revenue_tag"](gaap)
        r["revenue_tag"] = tag
        q = G["last_4_quarters"](gaap[tag]["units"]["USD"]) if tag else None
        r["revenue_4q_sum"] = sum(q) if q else None
        r["annual"] = {k: G["annual_series"](gaap, tags) for k, tags in G["ANNUAL_TAGS"].items() if k in ("revenue", "operating_income", "net_income")}
    except Exception as e:
        r["errors"].append(f"{type(e).__name__}: {str(e)[:150]}")
    out[t] = r
json.dump(out, open("dryrun_sec.json", "w"), indent=1)
print(json.dumps({k: (v.get("foreign") or v.get("revenue_tag"), v["errors"]) for k, v in out.items()}))
