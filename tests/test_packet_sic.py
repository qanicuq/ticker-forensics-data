"""The packet saves the SEC industry code (sic) from the submissions call, for the engine's Altman Z / Z″ choice (Nov 20 2026)."""
import ast, types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "generate_packet.py").read_text()
fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "foreign_annual_form")


def run(sub):
    """Run foreign_annual_form with SEC's reply replaced by `sub`; return (result, packet)."""
    class R:
        def raise_for_status(self): pass
        def json(self): return sub
    fake_requests = types.ModuleType("requests"); fake_requests.get = lambda *a, **k: R()
    fake_edgar = types.ModuleType("edgar"); fake_edgar.Company = lambda t: types.SimpleNamespace(cik="1349436")
    import sys
    sys.modules["requests"], sys.modules["edgar"] = fake_requests, fake_edgar
    ns = {"os": __import__("os"), "TICKER": "SD", "packet": {}, "NEWEST_REPORT": None}
    exec(compile(ast.Module([fn], []), "foreign_annual_form", "exec"), ns)
    return ns["foreign_annual_form"](), ns["packet"]


FILINGS = {"filings": {"recent": {"form": ["10-Q", "10-K"], "accessionNumber": ["a", "b"], "reportDate": ["2026-09-30", "2025-12-31"]}}}


def test_sic_saved_as_number():
    res, pk = run({"sic": "1311", "sicDescription": "Crude Petroleum & Natural Gas", **FILINGS})
    assert res is None and pk == {"sic": 1311, "sic_description": "Crude Petroleum & Natural Gas"}


def test_missing_sic_is_none():
    for s in ("", None, "n/a"):
        _, pk = run({"sic": s, **FILINGS})
        assert pk == {"sic": None, "sic_description": None}


def test_foreign_form_still_found():
    res, pk = run({"sic": "7370", "sicDescription": "x", "filings": {"recent": {"form": ["6-K", "20-F"], "accessionNumber": ["a", "b"], "reportDate": ["", "2025-12-31"]}}})
    assert res == "20-F" and pk["sic"] == 7370
