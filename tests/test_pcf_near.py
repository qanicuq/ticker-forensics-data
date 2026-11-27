"""Dreman Rule 21 with P/CF and the 10% "near the market" margin (user, 2026-11-27): the "no longer cheap" sell line
is the price where the P/E, P/B and P/CF are ALL within 10% of the S&P 500's. P/CF = market cap ÷ operating cash
flow over the last 12 months; left out (with a note) when the packet has no market P/CF or cash flow is <= 0."""
import contextlib, io, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "worker"))
import forensics_tools as F  # noqa: E402

MK = {"pe": 24.04, "pb": 5.08, "pcf": 18.0, "date": "2026-11-27"}


def ce_of(price, pe, pb, mcap, cfo, target=178.47, mk=MK):
    E = {"quote": {"price": price, "pe": pe, "pb": pb, "marketCap": mcap}, "fin": {"cfo": cfo}}
    A = {"exitPlan": {"entryType": "value", "entry": price, "target": target}, "value": {}}
    F._market_lines(E, A, mk)
    return A["exitPlan"]["cheapExit"]


def test_margin_is_ten_percent():
    assert F.NEAR == 0.90


def test_all_three_below_market():
    ce = ce_of(50, 12, 2, 1e9, 1e8)  # P/CF 10; lines: P/E 90.15, P/B 114.30, P/CF 50 × 0.9 × 18 ÷ 10 = 81.00
    assert ce["price"] == 114.30 and ce["stockPCF"] == 10.0 and ce["marketPCF"] == 18.0 and ce["near"] == 0.90
    assert ce["note"].startswith("Also sell at about $114.30, where the P/E (now 12.0), the P/B (now 2.00) and the P/CF (now 10.0) "
                                 "would all be within 10% of the market's (S&P 500 P/E 24.0, P/B 5.08 and P/CF 18.0 on 2026-11-27)")


def test_low_pcf_raises_the_line():
    # ELF-like: P/E and P/B already near the market, cash flow cheap → P/CF sets the line
    ce = ce_of(103.47, 72.205164, 4.987732, 6e9, 6e8)  # P/CF 10 → 103.47 × 0.9 × 18 ÷ 10 = 167.6214
    assert ce["price"] == 167.62
    assert ("where the P/CF (now 10.0) would come within 10% of the market's 18.0; the P/E (now 72.2) vs 24.0 and the P/B "
            "(now 4.99) vs 5.08 are already within 10% of the market's or above it") in ce["note"]


def test_high_pcf_already_near():
    ce = ce_of(103.47, 72.205164, 4.987732, 6e9, 2e8)  # P/CF 30
    assert ce["price"] == 94.85 and ce["note"].startswith("Already priced near the market: P/E 72.2, P/B 4.99, P/CF 30.0 vs")


def test_negative_cash_flow_leaves_pcf_out():
    ce = ce_of(50, 12, 2, 1e9, -1e7)
    assert ce["price"] == 114.30 and ce["stockPCF"] is None
    assert ce["note"].endswith("P/CF not used: operating cash flow over the last 12 months is negative or missing.")
    assert "S&P 500 P/E 24.0 and P/B 5.08 on 2026-11-27" in ce["note"]


def test_missing_cash_flow_leaves_pcf_out():
    assert ce_of(50, 12, 2, 1e9, None)["stockPCF"] is None
    assert ce_of(50, 12, 2, None, 1e8)["stockPCF"] is None


def test_market_pcf_missing_keeps_pe_pb():
    ce = ce_of(50, 12, 2, 1e9, 1e8, mk={"pe": 24.04, "pb": 5.08, "date": "2026-11-27"})
    assert ce["price"] == 114.30 and ce["stockPCF"] is None
    assert ce["note"].endswith("P/CF not used: the S&P 500's P/CF was unavailable this run.")


def trigger(tmp_path, monkeypatch, ep, price=103.47):
    final = {"quote": {"price": price}, "analysis": {"verdict": "WATCH", "confidence": 70, "entryPrice": ep["entry"], "exitPlan": ep}}
    (tmp_path / "f.json").write_text(json.dumps(final))
    monkeypatch.setattr(F, "_bot_file", lambda name: {})
    monkeypatch.setattr(F, "_send_checked", lambda *a, **k: (True, None))
    b = io.StringIO()
    with contextlib.redirect_stdout(b):
        F.cmd_trigger(str(tmp_path / "f.json"), "TEST")
    return json.loads(b.getvalue())


EP = {"entryType": "value", "entry": 103.47, "stop": 29.8, "target": 178.47, "timeStopMonths": 36, "reviewMonths": 18,
      "targetBasis": "Sell or trim when price reaches estimated value"}


def test_no_trigger_note_lists_pcf(tmp_path, monkeypatch):
    ep = {**EP, "cheapExit": {"price": 94.85, "marketPE": 24.04, "marketPB": 5.08, "marketPCF": 18.0, "stockPE": 72.205164,
                              "stockPB": 4.987732, "stockPCF": 30.0, "near": 0.9, "date": "2026-11-27"}}
    note = trigger(tmp_path, monkeypatch, ep)["triggerNote"]
    assert "(P/E 72.2 vs the S&P 500's 24.0, P/B 4.99 vs 5.08, P/CF 30.0 vs 18.0; Dreman Rule 21)" in note
    assert "is already below the entry $103.47" in note


def test_sent_trigger_says_pcf_and_margin(tmp_path, monkeypatch):
    sent = []
    ep = {**EP, "cheapExit": {"price": 167.62, "marketPE": 24.04, "marketPB": 5.08, "marketPCF": 18.0, "stockPE": 72.205164,
                              "stockPB": 4.987732, "stockPCF": 10.0, "near": 0.9, "date": "2026-11-27"}}
    final = {"quote": {"price": 103.47}, "analysis": {"verdict": "WATCH", "confidence": 70, "entryPrice": 103.47, "exitPlan": ep}}
    (tmp_path / "f.json").write_text(json.dumps(final))
    monkeypatch.setattr(F, "_bot_file", lambda name: {})
    monkeypatch.setattr(F, "_send_checked", lambda y, *a, **k: (sent.append(y), (True, None))[1])
    with contextlib.redirect_stdout(io.StringIO()):
        F.cmd_trigger(str(tmp_path / "f.json"), "TEST")
    assert sent and "target: {price: 167.62}" in sent[0]
    assert "no longer cheap: p/e, p/b and p/cf within 10% of the s&p 500's, below estimated value" not in sent[0]  # not lower-cased
    assert "(no longer cheap: P/E, P/B and P/CF within 10% of the S&P 500's, below estimated value)" in sent[0]
