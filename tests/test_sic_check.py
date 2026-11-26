"""sic-check: the page picks Altman Z / Z″ by Webull's industry name; the packet's SEC code must win (IBM, Nov 26 2026)."""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "worker"))
from forensics_tools import sic_check


def eng(ver="Z″", basis="industry name (IT Services & Consulting)", util=False):
    X = {"altmanBasis": basis}
    if ver:
        X["altmanVersion"] = ver
    notes = ["Regulated utility: the Altman bankruptcy score doesn't apply."] if util else ["Other note"]
    return {"analysis": {"forensic": X, "value": {"notes": notes}}}


def test_ibm_manufacturer_code_rebuilds():
    w, why = sic_check(eng("Z″"), {"sic": 3570})
    assert w == "REBUILD" and "3570" in why and "Z″" in why


def test_service_code_with_z2_ok():
    assert sic_check(eng("Z″"), {"sic": 7370})[0] == "OK"


def test_maker_by_name_but_service_code_rebuilds():
    assert sic_check(eng("Z", "industry name (Semiconductors)"), {"sic": 7370})[0] == "REBUILD"


def test_maker_both_ok():
    assert sic_check(eng("Z", "industry name (Semiconductors)"), {"sic": 3674})[0] == "OK"


def test_already_sec_basis_ok():
    assert sic_check(eng("Z″", "SEC industry code 3570"), {"sic": 3570})[0] == "OK"


def test_no_sic_ok():
    for pk in ({}, {"sic": None}, {"sic": "3570"}, {"sic": True}, None):
        assert sic_check(eng("Z″"), pk)[0] == "OK"


def test_utility_by_code_not_by_name_rebuilds():
    assert sic_check(eng("Z″"), {"sic": 4911})[0] == "REBUILD"


def test_utility_by_name_not_by_code_rebuilds():
    assert sic_check(eng(None, util=True), {"sic": 4400})[0] == "REBUILD"


def test_utility_both_ok():
    assert sic_check(eng(None, util=True), {"sic": 4931})[0] == "OK"


def test_no_score_financial_ok():
    assert sic_check(eng(None, "industry name (Banks)"), {"sic": 6021})[0] == "OK"


def test_command_line(tmp_path):
    job, pk = tmp_path / "job.json", tmp_path / "pk.json"
    job.write_text(json.dumps({"engine": eng("Z″")}))
    pk.write_text(json.dumps({"sic": 3570}))
    out = subprocess.run([sys.executable, str(ROOT / "worker/forensics_tools.py"), "sic-check", str(job), str(pk)],
                         capture_output=True, text=True).stdout
    assert out.startswith("REBUILD ")
    e = tmp_path / "e.json"
    e.write_text(json.dumps(eng("Z", "SEC industry code 3570")))
    out = subprocess.run([sys.executable, str(ROOT / "worker/forensics_tools.py"), "sic-check", str(job), str(pk), "--engine", str(e)],
                         capture_output=True, text=True).stdout
    assert out.startswith("OK ")
