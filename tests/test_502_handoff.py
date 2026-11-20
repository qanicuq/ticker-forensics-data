"""The 8-K text the packet read reaches the report writer for every executive change, not only a finance officer
leaving (HOPE, Nov 19 2026: its Aug 25 8-K, the CEO's contract extension, was reported as "could not be read")."""
import contextlib, io, json, sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "worker"))
import forensics_tools as F  # noqa: E402

F.stale_scripts = lambda: None
RECENT = (date.today() - timedelta(days=30)).isoformat()
URL = "https://www.sec.gov/Archives/edgar/data/1/x.htm"
TEXT = "employment agreement ... will end on august 31, 2031"


def run(tmp_path, watch):
    pk = {"governance": {"watch": watch}, "cross_check": {"matches": [], "mismatches": []}, "annual": {}}
    eng = {"ticker": "T", "analysis": {"value": {}, "redFlags": []}, "quote": {"price": 10, "marketCap": 1e9, "pe": 10}}
    for name, obj in (("p.json", pk), ("e.json", eng), ("j.json", {"ticker": "T"})):
        (tmp_path / name).write_text(json.dumps(obj))
    b = io.StringIO()
    with contextlib.redirect_stdout(b):
        F.cmd_sec(str(tmp_path / "j.json"), str(tmp_path / "p.json"), str(tmp_path / "e.json"))
    o = json.loads(b.getvalue())
    flag = next(f for f in o["add"]["redFlags"] if f["issue"] == "Executive or director change")
    judge = next(j for j in o["judge"] if j.startswith("Executive or director change"))
    return flag, judge


def item(kind, sentence):
    return {"form": "8-K", "date": RECENT, "url": URL, "kind": kind, "sentence": sentence,
            "issue": "Director or officer departure/appointment (8-K item 5.02)"}


def test_read_text_is_passed_on(tmp_path):
    flag, judge = run(tmp_path, [item("officer or director change", TEXT)])
    assert TEXT in flag["detail"] and TEXT in judge
    assert "do not call the 8-K unread" in judge


def test_unread_8k_keeps_old_wording(tmp_path):
    flag, judge = run(tmp_path, [item("unread", "")])
    assert flag["detail"] == f"8-K filed {RECENT}"
    assert "already read" not in judge


def test_unclear_kind_text_not_presented_as_checked(tmp_path):
    flag, judge = run(tmp_path, [item("unclear", "some text")])
    assert "already read" not in judge and "some text" not in flag["detail"]
