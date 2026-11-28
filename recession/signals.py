"""Turn raw FRED data into monthly readings, signals and an alert level.

Every reading for month m uses only what was public by the end of month m
(or by the as_of day for the current, unfinished month)."""
import pandas as pd

LEVELS = {0: "ALL CLEAR", 1: "WATCH", 2: "WARNING", 3: "RECESSION SIGNAL"}
SAHM_LINE = 0.50          # standard Sahm Rule line, not tuned
CLAIMS_LAG_DAYS = 5       # weekly claims come out 5 days after the week ends


def _monthly(monthly, daily):
    """Monthly averages; months FRED hasn't posted yet are filled from the daily series."""
    return monthly.combine_first(daily.resample("MS").mean())


def readings(raw, as_of):
    """One row per month up to as_of with the five readings."""
    as_of = pd.Timestamp(as_of).normalize()
    months = pd.date_range("1953-04-01", as_of, freq="MS")

    def upto(s):
        return s[s.index <= as_of]

    gs10 = _monthly(upto(raw["GS10"]), upto(raw["DGS10"]))
    tb3 = _monthly(upto(raw["TB3MS"]), upto(raw["DTB3"]))
    baa = _monthly(upto(raw["BAA"]), upto(raw["DBAA"]))

    out = pd.DataFrame(index=months)
    out["curve"] = gs10 - tb3                     # 10-year minus 3-month bill
    out["spread"] = baa - gs10                    # Moody's Baa bond minus 10-year
    out["spread_rise"] = out["spread"] - out["spread"].rolling(12, min_periods=12).min()

    claims4 = upto(raw["ICSA"]).rolling(4).mean()
    claims_low = claims4.rolling(52, min_periods=52).min()
    sahm = upto(raw["SAHMREALTIME"])
    vint = raw["PAYEMS_VINTAGES"]

    c_lvl, c_rise, s_val, p_val = [], [], [], []
    for m in months:
        end = min(m + pd.offsets.MonthEnd(0), as_of)
        known = claims4[claims4.index <= end - pd.Timedelta(days=CLAIMS_LAG_DAYS)]
        if len(known) and pd.notna(claims_low.get(known.index[-1])):
            c_lvl.append(known.iloc[-1])
            c_rise.append(known.iloc[-1] / claims_low[known.index[-1]] - 1)
        else:
            c_lvl.append(float("nan")); c_rise.append(float("nan"))
        # Sahm Rule (real-time version): last month's value is out by the end of this month
        prior = sahm[sahm.index <= m - pd.DateOffset(months=1)]
        s_val.append(prior.iloc[-1] if len(prior) else float("nan"))
        # Payrolls as they were published on that day (not today's revised numbers)
        v = vint[(vint["rs"] <= end) & (vint["re"] >= end)].sort_values("date")
        p_val.append((v["value"].iloc[-1] - v["value"].iloc[-4]) / 3 * 1000 if len(v) >= 4 else float("nan"))
    out["claims4"] = c_lvl
    out["claims_rise"] = c_rise
    out["sahm"] = s_val
    out["jobs3"] = p_val                          # 3-month average job change (people)
    return out


def _lasting(flag, months):
    """True only when flag has been true for `months` months in a row."""
    flag = flag.fillna(False).astype(bool)
    run = flag.copy()
    for k in range(1, months):
        run &= flag.shift(k, fill_value=False)
    return run


def signals(r, spread_x, claims_y, persist):
    """Five on/off signals plus the alert level for each month."""
    s = pd.DataFrame(index=r.index)
    inverted = _lasting(r["curve"] < 0, persist)
    s["curve"] = inverted.astype(float).rolling(12, min_periods=1).max().astype(bool)   # inverted now or in last 12 months
    s["credit"] = _lasting(r["spread_rise"] >= spread_x, persist)
    s["claims"] = _lasting(r["claims_rise"] >= claims_y, persist)
    s["sahm"] = (r["sahm"] >= SAHM_LINE).fillna(False)
    s["jobs"] = (r["jobs3"] < 0).fillna(False)
    early = s[["curve", "credit", "claims"]].sum(axis=1)
    level = early.clip(upper=2)                    # 1 early signal = WATCH, 2+ = WARNING
    level[s["sahm"] | s["jobs"]] = 3
    s["early_count"] = early
    s["level"] = level.astype(int)
    return s
