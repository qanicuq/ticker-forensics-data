"""SEC annual net income falls back to NetIncomeLossAvailableToCommonStockholdersBasic when NetIncomeLoss is older
(IRM, Nov 27 2026: NetIncomeLoss ends 2010, so the worker found no SEC net income to compare and held the trigger)."""
import ast
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
tree = ast.parse((ROOT / "generate_packet.py").read_text())
want = {"round2", "days", "annual_series"}
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in want] + \
        [n for n in tree.body if isinstance(n, ast.Assign) and any(getattr(t, "id", "") in ("ANNUAL_TAGS", "ANNUAL_FORMS") for t in n.targets)]
ns = {"pd": pd}
exec(compile(ast.Module(nodes, []), "generate_packet_parts", "exec"), ns)


def fy(end, val, filed):
    return {"start": end[:4] + "-01-01", "end": end, "val": val, "form": "10-K", "filed": filed}


# IRM's real SEC figures (data.sec.gov companyconcept, checked Nov 27 2026)
IRM = {
    "NetIncomeLoss": {"units": {"USD": [fy("2008-12-31", 82037000, "2011-03-01"), fy("2009-12-31", 220877000, "2011-03-01"),
                                        fy("2010-12-31", -53900000, "2011-03-01")]}},
    "NetIncomeLossAvailableToCommonStockholdersBasic": {"units": {"USD": [
        fy("2021-12-31", 450219000, "2024-02-22"), fy("2022-12-31", 556981000, "2025-02-14"),
        fy("2023-12-31", 184234000, "2026-02-12"), fy("2024-12-31", 180156000, "2026-02-12"),
        fy("2025-12-31", 144591000, "2026-02-12")]}},
}


def test_irm_uses_common_stockholders_line():
    used = {}
    got = ns["annual_series"](IRM, ns["ANNUAL_TAGS"]["net_income"], used=used, key="net_income")
    assert got == {"2025-12-31": 144591000.0, "2024-12-31": 180156000.0, "2023-12-31": 184234000.0,
                   "2022-12-31": 556981000.0, "2021-12-31": 450219000.0}  # = Webull net_income, all 5 years
    assert used["net_income"] == "NetIncomeLossAvailableToCommonStockholdersBasic"


def test_current_netincomeloss_still_wins_a_tie():
    # same newest year in both lines: keep NetIncomeLoss (a preferred-stock issuer's common line is smaller)
    facts = {"NetIncomeLoss": {"units": {"USD": [fy("2025-12-31", 100, "2026-02-01")]}},
             "NetIncomeLossAvailableToCommonStockholdersBasic": {"units": {"USD": [fy("2025-12-31", 90, "2026-02-01")]}}}
    used = {}
    assert ns["annual_series"](facts, ns["ANNUAL_TAGS"]["net_income"], used=used, key="net_income") == {"2025-12-31": 100.0}
    assert used["net_income"] == "NetIncomeLoss"
