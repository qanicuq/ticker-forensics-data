"""8-K item 5.02 reader: an interim holder handing over to a new appointee is not a departure (NKE, Nov 19 2026).
Texts follow the wording of Nike's real 8-Ks (quoted from the packet's stored sentences)."""
import ast, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "generate_packet.py").read_text()
tree = ast.parse(src).body
keep = [n for n in tree if (isinstance(n, ast.FunctionDef) and n.name == "classify_502") or
        (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in ("FINANCE_ROLES", "LEAVING", "CHANGE") for t in n.targets))]
ns = {"re": re}
exec(compile(ast.Module(keep, []), "classify_502", "exec"), ns)
classify_502 = ns["classify_502"]

HEAD = ("Item 5.02 Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers; "
        "Compensatory Arrangements of Certain Officers. ")
END = " SIGNATURES"

def kind(body):
    return classify_502(HEAD + body + END)[0]

def test_nov_9_2026_new_chief_accounting_officer():  # the bug: was "finance officer departure"
    assert kind("On November 4, 2026, the Company announced the appointment of Dan McKenzie as Vice President, Chief "
                "Accounting Officer, Finance Operations & Transformation, effective November 9, 2026. Mr. McKenzie has no "
                "direct or indirect material interest subject to disclosure under Item 404(a) of Regulation S-K. On November 9, "
                "2026, the Company also announced that, as of the effective date, David Denton, the Company's Executive Vice "
                "President and Chief Financial Officer, will cease serving as Interim Corporate Controller and principal "
                "accounting officer.") == "officer or director change"

def test_jun_23_2026_cfo_steps_down_still_departure():
    assert kind("The Company announced the appointment of David Denton as Executive Vice President and Chief Financial "
                "Officer. Mr. Denton has no direct or indirect material interest subject to disclosure under Item 404(a) of "
                "Regulation S-K. On June 23, 2026, the Company also announced that, as of the effective date, Matthew Friend "
                "will cease serving as Executive Vice President and CFO and begin serving as an advisor to the Company."
                ) == "finance officer departure"

def test_aug_10_2026_chief_accounting_officer_resigns_still_departure():
    assert kind("On August 4, 2026, Johanna Nielsen informed NIKE, Inc. (the \"Company\") of her intent to resign as Vice "
                "President, Chief Accounting Officer and Corporate Controller of the Company, effective September 4, 2026."
                ) == "finance officer departure"

def test_interim_cfo_resigning_without_successor_still_departure():
    assert kind("On May 1, 2026, Jane Roe resigned as interim Chief Financial Officer, effective immediately.") == \
        "finance officer departure"

def test_director_resigns_is_a_change():
    assert kind("On November 13, 2026, Monica Gil notified NIKE, Inc. of her decision to resign as a member of the Board "
                "of Directors.") == "officer or director change"

def test_pay_plan_only():
    assert kind("On July 15, 2026, the Board of Directors of NIKE, Inc. adopted an amendment and restatement of the NIKE, "
                "Inc. Employee Stock Purchase Plan, subject to shareholder approval.") == "pay plan only"
