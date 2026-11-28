import json
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import backtest as bt  # noqa: E402
import signals as sg  # noqa: E402


def fake_raw(end="2003-12-31"):
    m = pd.date_range("1953-04-01", end, freq="MS")
    d = pd.date_range("1990-01-01", end, freq="B")
    w = pd.date_range("1967-01-07", end, freq="W-SAT")
    raw = {"GS10": pd.Series(5.0, m), "TB3MS": pd.Series(4.0, m), "BAA": pd.Series(7.0, m),
           "DGS10": pd.Series(5.0, d), "DTB3": pd.Series(4.0, d), "DBAA": pd.Series(7.0, d),
           "ICSA": pd.Series(300000.0, w), "SAHMREALTIME": pd.Series(0.1, m)}
    pay = pd.date_range("1950-01-01", end, freq="MS")
    raw["PAYEMS_VINTAGES"] = pd.DataFrame({"date": pay, "rs": pay + pd.DateOffset(months=1),
                                           "re": pd.Timestamp("2200-01-01"), "value": range(1000, 1000 + len(pay))})
    return raw


def test_lasting_needs_months_in_a_row():
    f = pd.Series([True, False, True, True, True])
    assert sg._lasting(f, 2).tolist() == [False, False, False, True, True]
    assert sg._lasting(f, 1).tolist() == f.tolist()


def test_curve_stays_on_12_months_after_inversion():
    raw = fake_raw()
    raw["TB3MS"]["2001-03-01"] = 6.0                     # one inverted month
    s = sg.signals(sg.readings(raw, "2003-12-31"), 0.5, 0.2, 1)
    assert s.loc["2001-03-01", "curve"] and s.loc["2002-02-01", "curve"]
    assert not s.loc["2002-03-01", "curve"] and not s.loc["2001-02-01", "curve"]
    s2 = sg.signals(sg.readings(raw, "2003-12-31"), 0.5, 0.2, 2)
    assert not s2["curve"].any()                         # 1 month is not enough when 2 are required


def test_claims_ignore_week_not_yet_published():
    raw = fake_raw()
    raw["ICSA"]["2002-06-29"] = 1_000_000.0              # week ends Sat Jun 29, out Jul 4
    r = sg.readings(raw, "2003-12-31")
    assert r.loc["2002-06-01", "claims4"] == 300000.0
    assert r.loc["2002-07-01", "claims4"] > 300000.0


def test_payrolls_use_number_as_first_published():
    raw = fake_raw()
    v = raw["PAYEMS_VINTAGES"]
    # Pretend May 2002 was first shown as a big drop, then revised up in Sep 2002
    i = v.index[v["date"] == "2002-05-01"][0]
    v.loc[i, "re"] = pd.Timestamp("2002-08-31")
    v.loc[len(v)] = [pd.Timestamp("2002-05-01"), pd.Timestamp("2002-09-01"), pd.Timestamp("2200-01-01"), v.loc[i, "value"]]
    v.loc[i, "value"] -= 100
    r = sg.readings(raw, "2003-12-31")
    assert r.loc["2002-06-01", "jobs3"] < 0              # as known in June 2002
    assert r.loc["2002-10-01", "jobs3"] > 0              # after the revision


def test_sahm_uses_last_month_and_overrides_level():
    raw = fake_raw()
    raw["SAHMREALTIME"]["2002-04-01"] = 0.6
    s = sg.signals(sg.readings(raw, "2003-12-31"), 0.5, 0.2, 1)
    assert s.loc["2002-05-01", "level"] == 3 and s.loc["2002-04-01", "level"] == 0


def test_partial_month_uses_daily_rates():
    raw = fake_raw("2003-12-31")
    raw["DTB3"]["2003-12-01":] = 6.0
    for k in ("GS10", "TB3MS", "BAA"):
        raw[k] = raw[k][:"2003-11-01"]                   # December monthly not posted yet
    r = sg.readings(raw, "2003-12-15")
    assert r.index[-1] == pd.Timestamp("2003-12-01") and r["curve"].iloc[-1] == pytest.approx(-1.0)
    assert r.loc["2003-11-01", "curve"] == pytest.approx(1.0)


def test_judge_hits_false_and_undecided():
    idx = pd.date_range("2000-01-01", "2010-12-01", freq="MS")
    usrec = pd.Series(0, idx)
    usrec["2005-01-01":"2005-06-01"] = 1
    on = pd.Series(False, idx)
    on["2004-01-01":"2004-03-01"] = True                 # 12 months early: hit
    on["2001-01-01":"2001-02-01"] = True                 # no recession within 24 months: false
    on["2010-06-01":"2010-07-01"] = True                 # data ends before 24 months pass
    j = bt.judge(on, usrec, idx[0], idx[-1], "early")
    assert j["caught"] == 1 and j["recessions"][0]["months_before_start"] == 12
    assert j["false_count"] == 1 and j["false_alarms"][0]["from"] == "2001-01"
    assert len(j["too_early_to_judge"]) == 1


def test_alert_pushes_only_on_change(tmp_path, monkeypatch):
    import alert
    import fred
    raw = fake_raw("2003-12-31")
    monkeypatch.setattr(fred, "fetch_all", lambda **k: raw)
    monkeypatch.setattr(alert, "today_ny", lambda: pd.Timestamp("2003-12-10"))   # a Wednesday
    sent = []
    monkeypatch.setattr(alert, "push", lambda *a: sent.append(a[0]))
    monkeypatch.chdir(tmp_path)
    json.dump({"spread_x": 0.5, "claims_y": 0.2, "persist": 1}, open("config.json", "w"))
    alert.main()                                        # first run: summary only
    assert sent == ["Recession Alert weekly: ALL CLEAR"]
    alert.main()                                        # nothing changed
    assert len(sent) == 1
    raw["DTB3"]["2003-12-01":] = 9.0; raw["TB3MS"] = raw["TB3MS"][:"2003-11-01"]
    alert.main()                                        # curve inverts this month
    assert sent[-1] == "Recession Alert: WATCH"


def test_warning_is_judged_on_early_signals_only():
    raw = fake_raw("2006-12-31")
    idx = pd.date_range("1953-04-01", "2006-12-01", freq="MS")
    raw["USREC"] = pd.Series(0, idx)
    raw["SAHMREALTIME"]["2003-04-01"] = 0.6           # a lone RECESSION SIGNAL month, no early signals
    out, _ = bt.run(raw, "2006-12-31")
    assert out["test"]["warning"]["false_count"] == 0
    assert out["test"]["recession_signal"]["false_count"] == 1
