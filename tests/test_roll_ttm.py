"""SEC's last 4 quarters rolled forward one quarter with a results release whose 10-Q isn't filed yet (NVDA, Nov 19 2026:
SEC $302.97B to Jul 26 2026 vs Webull $361.81B; $302,969M - $57,006M (Q3 FY26) + $115,844M (Q3 FY27) = $361,807M)."""
import ast, contextlib, io, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "generate_packet.py").read_text()
want = {"_release_nums", "roll_ttm", "REV_LABELS"}
nodes = [n for n in ast.parse(src).body
         if (isinstance(n, ast.FunctionDef) and n.name in want)
         or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in want for t in n.targets))]
ns = {"re": re}
exec(compile(ast.Module(nodes, []), "roll_ttm", "exec"), ns)
roll_ttm, nums = ns["roll_ttm"], ns["_release_nums"]

sys.path.insert(0, str(ROOT / "worker"))
import forensics_tools as F  # noqa: E402
F.stale_scripts = lambda: None

NVDA_TEXT = json.loads((ROOT / "packets" / "NVDA.json").read_text())["earnings_release"]["text"]
# oldest quarter (Q3 FY26) is the real SEC figure; the other three only need to sum to SEC's real $302,969M total
REV_Q = [("2025-10-26", 57006e6), ("2026-01-25", 68127e6), ("2026-04-26", 81615e6), ("2026-07-26", 96221e6)]
EPS_Q = [("2025-10-26", 1.30), ("2026-01-25", 1.76), ("2026-04-26", 2.39), ("2026-07-26", 2.46)]


def test_nvda_revenue_rolls_to_webull():
    v, how = roll_ttm(NVDA_TEXT, REV_Q, "revenue")
    assert sum(x for _, x in REV_Q) == 302969e6
    assert v == 361807e6  # Webull's figure exactly
    assert "57,006" in how and "115,844" in how


def test_nvda_eps_rolls_to_yfinance_pe():
    v, how = roll_ttm(NVDA_TEXT, EPS_Q, "eps")
    assert round(v, 2) == 9.31  # Webull epsTtm 9.3068
    assert abs(145.98 / v - 15.68) / 15.68 < 0.02  # yfinance P/E
    assert "| 2.70 |" in how  # the per-share line, not the 24,186 diluted share-count line


def test_year_ago_must_match_sec():
    bad = [("2025-10-26", 57100e6)] + REV_Q[1:]
    assert roll_ttm(NVDA_TEXT, bad, "revenue") == (None, None)
    assert roll_ttm(NVDA_TEXT, [("2025-10-26", 1.25)] + EPS_Q[1:], "eps") == (None, None)


def test_sequential_column_layout_not_used():
    # current quarter, prior quarter, year-ago quarter: the second number is SEC's newest quarter, not the oldest
    t = "Revenue | $ | 115,844 | | $ | 96,221 | | $ | 57,006"
    assert roll_ttm(t, REV_Q, "revenue") == (None, None)


def test_headline_sentence_not_used():
    assert roll_ttm("Revenue of $115.8 billion, up 103% from a year ago", REV_Q, "revenue") == (None, None)


def test_needs_four_quarters_and_text():
    assert roll_ttm(NVDA_TEXT, REV_Q[1:], "revenue") == (None, None)
    assert roll_ttm("", REV_Q, "revenue") == (None, None)
    assert roll_ttm(None, REV_Q, "revenue") == (None, None)


def test_numbers():
    assert nums("Net loss | $ | (1.30) | | $ | 2.70 | 103%") == [-1.30, 2.70]
    assert nums("Q3 FY27 2026-10-25 | 5") == [5.0]


def sec(tmp_path, last_q, rolled):
    cc = {"matches": [{"field": "market_cap", "yfinance": 3.5e12, "sec": 3.5e12, "pct_diff": 0},
                      {"field": "revenue_4q_sum", "yfinance": 302969e6, "sec": 302969e6, "pct_diff": 0}],
          "mismatches": []}
    if rolled:
        cc["sec_rolled"] = {"revenue_4q_sum": 361807e6, "revenue_base_end": "2026-07-26", "release_filed": "2026-11-17",
                            "revenue_how": "how"}
    pk = {"cross_check": cc, "annual": {}}
    eng = {"ticker": "NVDA", "analysis": {"value": {}, "redFlags": []}, "quote": {"price": 145.98, "marketCap": 3.5e12},
           "fin": {"currency": "USD", "rev": 361807e6, "lastQ": last_q, "annual": []}}
    for name, obj in (("p.json", pk), ("e.json", eng), ("j.json", {"ticker": "NVDA"})):
        (tmp_path / name).write_text(json.dumps(obj))
    b = io.StringIO()
    with contextlib.redirect_stdout(b):
        F.cmd_sec(str(tmp_path / "j.json"), str(tmp_path / "p.json"), str(tmp_path / "e.json"))
    o = json.loads(b.getvalue())
    return next(c for c in o["compared"] if c["figure"] == "Trailing 12-month revenue"), o


def test_worker_uses_rolled_window_when_webull_is_newer(tmp_path):
    c, o = sec(tmp_path, "2026-10-25", True)
    assert c["pctApart"] == 0 and c["sec"] == 361807e6 and "rolled forward" in c["secBasis"]
    assert not o["serious"] and o["disagreements"] == 0


def test_worker_keeps_plain_sec_when_webull_is_not_newer(tmp_path):
    c, o = sec(tmp_path, "2026-07-26", True)
    assert c["sec"] == 302969e6 and "secBasis" not in c and o["serious"]


def test_worker_without_rolled_flags_as_before(tmp_path):
    c, o = sec(tmp_path, "2026-10-25", False)
    assert c["pctApart"] == 19.42 and o["serious"][0]["figure"] == "Trailing 12-month revenue"
