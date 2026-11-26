"""A soft-assets jump on a balance sheet Webull published in the last 7 days is "can not verify", which stops the
paper-bot trigger like any other unverified item (ELF, Nov 25 2026: Webull's first copy of the Sep 30 quarter put
leased-property assets in 'other' assets; its next-day copy moved them to property, 6.5% -> 3.5%)."""
import contextlib, io, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "worker"))
import forensics_tools as F  # noqa: E402

F.stale_scripts = lambda: None
ITEM = ("the soft-assets jump (3.8% to 9.4% of assets; Webull published this balance sheet 2 days ago and may still "
        "be adjusting it: check the 10-Q)")


def finalize(tmp_path, unverified):
    pk = {"governance": {"watch": []}, "cross_check": {"matches": [], "mismatches": []}, "annual": {}}
    eng = {"ticker": "T", "analysis": {"value": {}, "redFlags": [], "exitPlan": {}}, "quote": {"price": 10, "marketCap": 1e9, "pe": 10},
           "missing": [], "unverified": unverified}
    for name, obj in (("p.json", pk), ("e.json", eng), ("j.json", {"ticker": "T"}), ("patch.json", {})):
        (tmp_path / name).write_text(json.dumps(obj))
    b = io.StringIO()
    with contextlib.redirect_stdout(b):
        F.cmd_sec(str(tmp_path / "j.json"), str(tmp_path / "p.json"), str(tmp_path / "e.json"))
    (tmp_path / "s.json").write_text(b.getvalue())
    b = io.StringIO()
    with contextlib.redirect_stdout(b):
        F.cmd_finalize(str(tmp_path / "j.json"), str(tmp_path / "patch.json"), str(tmp_path / "s.json"), str(tmp_path / "e.json"))
    return json.loads(b.getvalue())["analysis"]


def test_engine_unverified_item_holds_the_trigger(tmp_path):
    # this bare test packet has no SEC share count, so "market cap" is also unverified; the engine item is added to it
    A = finalize(tmp_path, [ITEM])
    assert A["dataHold"]["unverified"][-1] == ITEM
    assert ITEM in A["dataHold"]["note"]


def test_no_engine_item_adds_nothing(tmp_path):
    A = finalize(tmp_path, [])
    assert not any("soft-assets" in u for u in A["dataHold"]["unverified"])
