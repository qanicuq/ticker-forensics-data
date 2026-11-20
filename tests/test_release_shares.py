"""Release share count for foreign filers' market-cap check (NBIS, Nov 19 2026)."""
import ast, json, re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "generate_packet.py").read_text()
fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "release_share_count")
ns = {"re": re, "datetime": datetime}
exec(compile(ast.Module([fn], []), "release_share_count", "exec"), ns)
release_share_count = ns["release_share_count"]

def test_nbis_q3_wording_with_line_break():
    t = ("The total number of shares issued and outstanding as of September 30,\n2026 was 292,902,405, including "
         "259,597,352 Class A shares and 33,305,053 Class B shares")
    assert release_share_count(t) == (292902405, "2026-09-30")

def test_no_sentence():
    assert release_share_count("Revenue was $980.8 million.") == (None, None)
    assert release_share_count(None) == (None, None)

def test_bad_date():
    assert release_share_count("total number of shares issued and outstanding as of Smarch 40, 2026 was 5") == (None, None)

def test_real_nbis_packet():
    p = json.loads((ROOT / "packets" / "NBIS.json").read_text())
    shares, when = release_share_count(p["earnings_release"]["text"])
    assert (shares, when) == (292902405, "2026-09-30")
    assert round(shares * 96.92, 2) == 28388101092.6  # = Webull's market cap
