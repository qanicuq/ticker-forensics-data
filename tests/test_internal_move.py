"""ETN fixes (Nov 22 2026): (1) an internal move of a finance officer is not a departure; (2) operating income is
built from revenue minus cost of revenue when a company files no operating-income or gross-profit line."""
import ast, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "generate_packet.py").read_text()
tree = ast.parse(src).body
keep = [n for n in tree if (isinstance(n, ast.FunctionDef) and n.name == "classify_502") or
        (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in ("FINANCE_ROLES", "LEAVING", "CHANGE", "INTERNAL_MOVE") for t in n.targets))]
ns = {"re": re}
exec(compile(ast.Module(keep, []), "classify_502", "exec"), ns)
classify_502 = ns["classify_502"]

HEAD = ("Item 5.02 Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers; "
        "Compensatory Arrangements of Certain Officers. ")
END = " SIGNATURES"

def kind(body):
    return classify_502(HEAD + body + END)[0]

def test_etn_oct_5_2026_controller_moves_inside_company():  # the bug: was "finance officer departure"
    assert kind("Departure of Principal Accounting Officer On September 30, 2026, Adam Wadecki, Senior Vice President and "
                "Controller of Eaton Corporation, accepted a new position within the Company and will transition into a "
                "non-executive officer position as Senior Vice President, Finance, Electrical, effective October 5, 2026. "
                "Mr. Wadecki served as the Company's principal accounting officer. Appointment of Principal Accounting "
                "Officer On October 1, 2026, Andrea Trabacchin was appointed as Senior Vice President and Controller of "
                "Eaton Corporation, effective October 5, 2026, and will serve as principal accounting officer."
                ) == "officer or director change"

def test_cfo_resigns_to_pursue_other_opportunities_still_departure():
    assert kind("On March 2, 2026, John Roe informed the Company of his decision to resign as Chief Financial Officer "
                "to pursue other opportunities, effective April 1, 2026.") == "finance officer departure"

def test_cfo_retires_into_advisory_role_still_departure():
    assert kind("On March 2, 2026, John Roe, Chief Financial Officer, announced he will retire and will transition into "
                "an advisory role until June 30, 2026.") == "finance officer departure"

def build_oi(an, tax_name="us-gaap"):
    """Copy of the operating-income build in generate_packet.py section 3b, run on a small annual dict."""
    seg = src[src.index("        an = packet[\"annual\"]\n"):src.index("        packet[\"annual\"][\"note\"]")]
    body = "\n".join(l[8:] for l in seg.splitlines())
    ns2 = {"packet": {"annual": an}, "tax_name": tax_name, "round2": lambda x: round(x, 2)}
    exec(body, ns2)
    return an

def test_etn_2025_operating_income_built_from_cost_of_revenue():
    an = build_oi({"operating_income": {"2019-12-31": 3675e6}, "revenue": {"2025-12-31": 27448e6, "2024-12-31": 24878e6},
                   "cost_of_revenue": {"2025-12-31": 17131e6, "2024-12-31": 15375e6}, "gross_profit": {},
                   "sga": {"2025-12-31": 4311e6, "2024-12-31": 4077e6},
                   "research_development": {"2025-12-31": 797e6, "2024-12-31": 794e6},
                   "pretax_income": {"2025-12-31": 4932e6}, "nonoperating": {}})
    assert an["operating_income"]["2025-12-31"] == 5209e6
    assert an["operating_income"]["2024-12-31"] == 4632e6
    assert an["operating_income"]["2019-12-31"] == 3675e6  # a filed figure is never replaced
    assert "revenue minus cost of revenue" in an["operating_income_basis"]

def test_gross_profit_build_still_used_first():
    an = build_oi({"operating_income": {}, "revenue": {"2025-12-31": 100.0}, "cost_of_revenue": {"2025-12-31": 70.0},
                   "gross_profit": {"2025-12-31": 31.0}, "sga": {"2025-12-31": 10.0}, "research_development": {},
                   "pretax_income": {}, "nonoperating": {}})
    assert an["operating_income"]["2025-12-31"] == 21.0
    assert "gross profit" in an["operating_income_basis"] and "cost of revenue" not in an["operating_income_basis"]

def test_ifrs_not_built():
    an = build_oi({"operating_income": {}, "revenue": {"2025-12-31": 100.0}, "cost_of_revenue": {"2025-12-31": 70.0},
                   "gross_profit": {}, "sga": {"2025-12-31": 10.0}, "research_development": {},
                   "pretax_income": {}, "nonoperating": {}}, tax_name="ifrs-full")
    assert an["operating_income"] == {} and "operating_income_basis" not in an

def test_profit_before_tax_build_still_wins_over_cost_build():  # keeps Lilly's figures unchanged
    an = build_oi({"operating_income": {}, "revenue": {"2025-12-31": 100.0}, "cost_of_revenue": {"2025-12-31": 20.0},
                   "gross_profit": {}, "sga": {"2025-12-31": 10.0}, "research_development": {"2025-12-31": 30.0},
                   "pretax_income": {"2025-12-31": 25.0}, "nonoperating": {"2025-12-31": -2.0}})
    assert an["operating_income"]["2025-12-31"] == 27.0
    assert "cost of revenue" not in an["operating_income_basis"]


def test_elf_nov_16_2026_pao_title_handover_cfo_stays():  # the bug: was "finance officer departure"
    assert kind("Effective November 12, 2026, the Board of Directors of e.l.f. Beauty, Inc. (the 'Company') appointed "
                "Amit Khetan, the Company's Chief Accounting Officer, to serve as principal accounting officer of the "
                "Company, succeeding Mandy Fields, the Company's Senior Vice President and Chief Financial Officer, in "
                "that role. Ms. Fields will continue to serve as Senior Vice President, Chief Financial Officer of the "
                "Company. Mr. Khetan will not receive any additional compensation in connection with this appointment."
                ) == "officer or director change"

def test_cfo_resigns_but_continues_as_advisor_still_departure():
    assert kind("On March 2, 2026, John Roe informed the Company of his decision to resign as Chief Financial Officer, "
                "effective April 1, 2026. Mr. Roe will continue to serve as an advisor until June 30, 2026.") == "finance officer departure"

def test_cfo_succeeded_without_staying_still_departure():
    assert kind("On March 2, 2026, the Board appointed Jane Doe as Chief Financial Officer, succeeding John Roe, "
                "effective April 1, 2026.") == "finance officer departure"
