"""When one ratio is already above the market's, the "no longer cheap" sell line and the no-trigger note say so,
instead of "both ratios would be back at the market's" and a bare "target is less than 10% above the entry"
(ELF, Nov 25 2026: P/E 72.2 vs the S&P 500's 24.0, P/B 4.99 vs 5.08, line $105.38, entry $103.47). Wording only:
which trades get a trigger does not change."""
import contextlib, io, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "worker"))
import forensics_tools as F  # noqa: E402

MK = {"pe": 24.04, "pb": 5.08, "date": "2026-11-25"}


def lines(price, pe, pb, target=178.47):
    E = {"quote": {"price": price, "pe": pe, "pb": pb}}
    A = {"exitPlan": {"entryType": "value", "entry": price, "target": target}, "value": {}}
    F._market_lines(E, A, MK)
    return A


def test_elf_line_and_note():
    ce = lines(103.47, 72.205164, 4.987732)["exitPlan"]["cheapExit"]
    assert ce["price"] == 105.38  # 103.47 × 5.08 ÷ 4.987732 = 105.3846; the P/E line is 34.45
    assert ce["note"].startswith("Also sell at about $105.38, where the P/B (now 4.99) would reach the market's 5.08; "
                                 "the P/E (now 72.2) is already above the market's 24.0 (S&P 500 P/E 24.0 and P/B 5.08 on 2026-11-25).")
    assert "both" not in ce["note"]


def test_pb_above_pe_below():
    ce = lines(50, 12, 8)["exitPlan"]["cheapExit"]  # P/E line 100.17, P/B line 31.75
    assert ce["price"] == 100.17
    assert "where the P/E (now 12.0) would reach the market's 24.0; the P/B (now 8.00) is already above the market's 5.08" in ce["note"]


def test_both_below_market_keeps_old_wording():
    ce = lines(50, 12, 2)["exitPlan"]["cheapExit"]  # P/E line 100.17, P/B line 127.00
    assert ce["note"].startswith("Also sell at about $127.00, where both the P/E (now 12.0) and the P/B (now 2.00) would be back at")


def test_both_above_market_keeps_old_wording():
    ce = lines(50, 40, 8)["exitPlan"]["cheapExit"]
    assert ce["note"].startswith("Already priced like the market")


def test_line_above_value_keeps_old_wording():
    ce = lines(50, 12, 4, target=60)["exitPlan"]["cheapExit"]  # line 100.17 ≥ value 60
    assert "so the value target comes first" in ce["note"]


def trigger_note(tmp_path, monkeypatch, ep):
    final = {"quote": {"price": 103.47}, "analysis": {"verdict": "WATCH", "confidence": 70, "entryPrice": 103.47, "exitPlan": ep}}
    (tmp_path / "f.json").write_text(json.dumps(final))
    monkeypatch.setattr(F, "_bot_file", lambda name: {})  # no held positions, no older triggers
    b = io.StringIO()
    with contextlib.redirect_stdout(b):
        F.cmd_trigger(str(tmp_path / "f.json"), "ELF")
    return json.loads(b.getvalue()).get("triggerNote")


ELF_EP = {"entryType": "value", "entry": 103.47, "stop": 29.8, "target": 178.47, "timeStopMonths": 36, "reviewMonths": 18,
          "targetBasis": "Sell or trim when price reaches estimated value",
          "cheapExit": {"price": 105.38, "marketPE": 24.04, "marketPB": 5.08, "stockPE": 72.205164, "stockPB": 4.987732, "date": "2026-11-25"}}


def test_elf_no_trigger_note(tmp_path, monkeypatch):
    assert trigger_note(tmp_path, monkeypatch, ELF_EP) == (
        "No trigger sent: the \"no longer cheap\" sell price $105.38 is less than 10% above the entry $103.47, so the stock is "
        "not clearly cheaper than the market (P/E 72.2 vs the S&P 500's 24.0, P/B 4.99 vs 5.08; Dreman Rule 21). "
        "The value estimate $178.47 is not used as the target while the stock is priced like the market.")


def test_value_target_too_close_keeps_old_note(tmp_path, monkeypatch):
    ep = {**ELF_EP, "target": 110.0, "cheapExit": {**ELF_EP["cheapExit"], "price": 120.0}}  # line above value: no cheap-first
    assert trigger_note(tmp_path, monkeypatch, ep) == "No trigger sent: the target $110.00 is less than 10% above the entry $103.47."


def test_elf_nov_26_line_already_below_entry(tmp_path, monkeypatch):
    # ELF, Nov 26 2026: the stock rose to $108.93, past its $105.38 "no longer cheap" line
    ep = {**ELF_EP, "entry": 108.93, "stop": 31.37, "target": 180.26,
          "cheapExit": {**ELF_EP["cheapExit"], "stockPE": 76.015352, "stockPB": 5.250929, "date": "2026-11-26"}}
    assert trigger_note(tmp_path, monkeypatch, ep) == (
        "No trigger sent: the \"no longer cheap\" sell price $105.38 is already below the entry $108.93, so the stock is "
        "not clearly cheaper than the market (P/E 76.0 vs the S&P 500's 24.0, P/B 5.25 vs 5.08; Dreman Rule 21). "
        "The value estimate $180.26 is not used as the target while the stock is priced like the market.")
