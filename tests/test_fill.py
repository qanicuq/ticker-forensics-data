"""Checks for adding one new quarter from a company press release when Webull is behind."""
import copy, json, os, sys, tempfile, unittest
from io import StringIO
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))
import forensics_tools as ft

LINES = [
    "Company reports results for the quarter",
    "Period ended 2026-10-25",
    "Revenue $10,409 million",
    "Gross profit $5,251 million",
    "Operating income $3,658 million",
    "Net income $2,718 million",
    "Diluted EPS $3.40",
    "Diluted shares 798 million",
    "A year earlier revenue was $6,800 million",
    "A year earlier gross profit was $3,265 million",
    "A year earlier operating income was $1,712 million",
    "A year earlier net income was $1,897 million",
]


def _fig(v, line):
    return {"v": v, "line": line}


def _qrow(end, rev, gp, op, ni):
    return {
        "fiscal_year": 2026, "fiscal_period": 3, "end_date": end, "currency": "USD", "publish_date": end,
        "total_revenue": str(rev), "revenue": str(rev), "gross_profit": str(gp), "op_income": str(op),
        "net_income": str(ni), "diluted_avg_shares": "800000000",
        "diluted_eps_excl_extra": "1.00", "diluted_eps_incl_extra": "1.00",
    }


def base_figs():
    return {
        "filed": "2026-11-12",
        "url": "https://www.sec.gov/Archives/edgar/data/example",
        "units": 1000000,
        "share_units": 1000000,
        "period_end": "2026-10-25",
        "fiscal_year_end": False,
        "quarter": {
            "total_revenue": _fig(10409, 3),
            "gross_profit": _fig(5251, 4),
            "op_income": _fig(3658, 5),
            "net_income": _fig(2718, 6),
            "diluted_eps": _fig(3.40, 7),
            "diluted_avg_shares": _fig(798, 8),
        },
        "year_ago": {
            "period_end": "2025-10-26",
            "total_revenue": _fig(6800, 9),
            "gross_profit": _fig(3265, 10),
            "op_income": _fig(1712, 11),
            "net_income": _fig(1897, 12),
        },
    }


def base_income_q():
    return [
        _qrow("2026-07-26", 9000000000, 4500000000, 3000000000, 2500000000),
        _qrow("2026-04-26", 8500000000, 4200000000, 2800000000, 2300000000),
        _qrow("2026-01-25", 8000000000, 3900000000, 2500000000, 2100000000),
        _qrow("2025-10-26", 6800000000, 3265000000, 1712000000, 1897000000),
        _qrow("2025-07-27", 7000000000, 3400000000, 1800000000, 1500000000),
    ]


def add_v2(figs, factor):
    figs = copy.deepcopy(figs)
    for name in ("quarter", "year_ago", "annual", "annual_year_ago"):
        section = figs.get(name)
        if not isinstance(section, dict):
            continue
        for fig in section.values():
            if isinstance(fig, dict) and "v" in fig:
                fig["v2"] = fig["v"] * factor
    return figs


def _readb(path):
    with open(path, "rb") as f:
        return f.read()


def _readj(path):
    with open(path) as f:
        return json.load(f)


class FillTests(unittest.TestCase):
    def setUp(self):
        self.alerts = []
        self._alert = ft.alert

        def fake(title, msg, priority="high"):
            self.alerts.append({"title": title, "msg": msg, "priority": priority})
            return True

        ft.alert = fake
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        ft.alert = self._alert
        self.tmp.cleanup()

    def _build(self, name, income_q=None, figs=None, lines=None, eps_actual="3.40"):
        d = os.path.join(self.tmp.name, name)
        os.makedirs(d)
        income_q = base_income_q() if income_q is None else income_q
        figs = base_figs() if figs is None else figs
        lines = LINES if lines is None else lines
        q_path = os.path.join(d, "income_q.json")
        with open(q_path, "w") as f:
            json.dump(income_q, f)
        original = _readb(q_path)
        with open(os.path.join(d, "income_a.json"), "w") as f:
            json.dump([_qrow("2025-10-26", 25000000000, 12000000000, 8000000000, 6000000000)], f)
        with open(os.path.join(d, "calendar.json"), "w") as f:
            json.dump([{
                "fiscal_year": 2026, "fiscal_period": 4, "expected_publish_date": "2026-11-12",
                "eps_actual": eps_actual, "eps_est": "3.20", "rev_actual": "10409000000",
            }], f)
        packet = os.path.join(d, "packet.json")
        with open(packet, "w") as f:
            json.dump({"earnings_release": {
                "source": "SEC 8-K item 2.02", "filed": "2026-11-12",
                "url": "https://www.sec.gov/Archives/edgar/data/example",
                "text": "\n".join(lines),
            }}, f)
        figs_path = os.path.join(d, "figs.json")
        with open(figs_path, "w") as f:
            json.dump(figs, f)
        return d, figs_path, packet, original

    def _run(self, d, figs_path, packet, web=False):
        buf = StringIO()
        args = ["fill", "AMAT", d, figs_path]
        if web:
            args.append("--web")
        elif packet:
            args.extend(["--packet", packet])
        with redirect_stdout(buf):
            ft.main(args)
        return buf.getvalue()

    def test_pass_writes_new_quarter(self):
        d, figs_path, packet, original = self._build("pass")
        out = self._run(d, figs_path, packet)
        self.assertTrue(out.startswith("PASS\n"), out)
        self.assertEqual(self.alerts, [])
        got = _readj(os.path.join(d, "income_q.json"))
        self.assertEqual(len(got), 6)
        new = got[0]
        self.assertEqual(new["end_date"], "2026-10-25")
        self.assertEqual(new["publish_date"], "2026-11-12")
        self.assertEqual(new["currency"], "USD")
        self.assertEqual(new["source"], "company press release")
        self.assertEqual(new["total_revenue"], "10409000000")
        self.assertEqual(new["op_income"], "3658000000")
        self.assertEqual(new["net_income"], "2718000000")
        self.assertEqual(new["gross_profit"], "5251000000")
        self.assertEqual(new["cost_of_revenue"], "5158000000")
        self.assertEqual(new["diluted_avg_shares"], "798000000")
        self.assertEqual(new["diluted_eps_excl_extra"], "3.4")
        self.assertEqual(new["diluted_eps_incl_extra"], "3.4")
        self.assertNotIn("fiscal_year", new)
        self.assertNotIn("fiscal_period", new)
        self.assertEqual(got[1]["end_date"], "2026-07-26")
        self.assertEqual(_readb(os.path.join(d, "income_q.webull.json")), original)
        filled = _readj(os.path.join(d, "filled.json"))
        self.assertEqual(filled["status"], "PASS")
        self.assertEqual(filled["ticker"], "AMAT")
        self.assertEqual(filled["ttm_rev_before"], 32300000000)
        self.assertEqual(filled["ttm_rev_before_end"], "2026-07-26")
        self.assertEqual(filled["web"], False)
        self.assertTrue(filled["checks"])

    def test_not_needed_when_webull_already_has_the_quarter(self):
        rows = base_income_q()
        rows[0]["end_date"] = "2026-10-25"
        d, figs_path, packet, original = self._build("not", income_q=rows)
        out = self._run(d, figs_path, packet)
        self.assertEqual(out.strip(), "NOT_NEEDED")
        self.assertEqual(_readb(os.path.join(d, "income_q.json")), original)
        self.assertFalse(os.path.exists(os.path.join(d, "filled.json")))
        self.assertFalse(os.path.exists(os.path.join(d, "income_q.webull.json")))
        self.assertEqual(self.alerts, [])

    def test_fail_when_figure_is_not_on_its_line(self):
        figs = base_figs()
        figs["quarter"]["total_revenue"]["line"] = 1
        d, figs_path, packet, original = self._build("line", figs=figs)
        out = self._run(d, figs_path, packet)
        self.assertTrue(out.startswith("FAIL\n"), out)
        self.assertIn("total_revenue", out)
        self.assertEqual(_readb(os.path.join(d, "income_q.json")), original)
        self.assertFalse(os.path.exists(os.path.join(d, "income_q.webull.json")))
        filled = _readj(os.path.join(d, "filled.json"))
        self.assertEqual(filled["status"], "FAIL")
        self.assertEqual(len(self.alerts), 1)
        self.assertEqual(self.alerts[0]["title"], "AMAT can not verify new quarter")

    def test_fail_when_year_ago_revenue_differs_by_3_percent(self):
        figs = base_figs()
        figs["year_ago"]["total_revenue"] = _fig(7004, 9)
        lines = list(LINES)
        lines[8] = "A year earlier revenue was $7,004 million"
        d, figs_path, packet, original = self._build("ya", figs=figs, lines=lines)
        out = self._run(d, figs_path, packet)
        self.assertTrue(out.startswith("FAIL\n"), out)
        self.assertIn("7004000000", out)
        self.assertIn("6800000000", out)
        self.assertEqual(_readb(os.path.join(d, "income_q.json")), original)
        self.assertEqual(len(self.alerts), 1)

    def test_fail_when_eps_math_is_wrong(self):
        figs = base_figs()
        figs["quarter"]["net_income"] = _fig(100, 6)
        lines = list(LINES)
        lines[5] = "Net income $100 million"
        d, figs_path, packet, original = self._build("eps", figs=figs, lines=lines)
        out = self._run(d, figs_path, packet)
        self.assertTrue(out.startswith("FAIL\n"), out)
        self.assertIn("diluted EPS", out)
        self.assertEqual(_readb(os.path.join(d, "income_q.json")), original)
        self.assertEqual(len(self.alerts), 1)

    def test_fail_when_calendar_eps_differs_by_a_tenth(self):
        d, figs_path, packet, original = self._build("cal", eps_actual="3.50")
        out = self._run(d, figs_path, packet)
        self.assertTrue(out.startswith("FAIL\n"), out)
        self.assertIn("3.5", out)
        self.assertIn("3.4", out)
        self.assertEqual(_readb(os.path.join(d, "income_q.json")), original)
        self.assertEqual(len(self.alerts), 1)

    def test_parenthesized_number_is_negative(self):
        self._build("neg")
        self.assertEqual(ft._line_numbers("(21)"), [-21.0])
        self.assertEqual(ft._line_numbers("-21"), [-21.0])
        self.assertEqual(ft._line_numbers("1,234"), [1234.0])
        self.assertEqual(ft._line_numbers("$3.40"), [3.4])
        self.assertEqual(ft._line_numbers("loss of (21)%"), [-21.0])
        self.assertEqual(ft._line_numbers("Period ended 2026-10-25"), [])

    def test_web_mode_accepts_a_tenth_of_a_percent_and_rejects_two_percent(self):
        ok_figs = add_v2(base_figs(), 1.001)
        d, figs_path, packet, original = self._build("webok", figs=ok_figs)
        out = self._run(d, figs_path, packet, web=True)
        self.assertTrue(out.startswith("PASS\n"), out)
        self.assertEqual(self.alerts, [])
        filled = _readj(os.path.join(d, "filled.json"))
        self.assertEqual(filled["status"], "PASS")
        self.assertEqual(filled["web"], True)
        self.assertNotEqual(_readb(os.path.join(d, "income_q.json")), original)

        bad = add_v2(base_figs(), 1.001)
        bad["quarter"]["total_revenue"]["v2"] = bad["quarter"]["total_revenue"]["v"] * 1.02
        d2, figs_path2, packet2, original2 = self._build("webbad", figs=bad)
        self.alerts.clear()
        out2 = self._run(d2, figs_path2, packet2, web=True)
        self.assertTrue(out2.startswith("FAIL\n"), out2)
        self.assertIn("0.5%", out2)
        self.assertEqual(_readb(os.path.join(d2, "income_q.json")), original2)
        self.assertEqual(len(self.alerts), 1)


if __name__ == "__main__":
    unittest.main()


class FillPartsAndYearEndTests(FillTests):
    """Claude's additions (Nov 13 2026): a figure printed as several lines (DHT), and a year-end quarter whose
    year-ago quarter differs from Webull's while the full years match (NFG)."""

    def test_parts_add_up_and_each_part_is_on_its_line(self):
        lines = LINES + ["Voyage expenses (2,000)", "Vessel operating expenses (3,158)",
                         "Voyage expenses a year earlier (1,500)", "Vessel operating a year earlier (2,035)"]
        figs = base_figs()
        figs["quarter"]["cost_of_revenue"] = {"v": 5158, "parts": [{"v": 2000, "line": 13}, {"v": 3158, "line": 14}]}
        figs["year_ago"]["cost_of_revenue"] = {"v": 3535, "parts": [{"v": 1500, "line": 15}, {"v": 2035, "line": 16}]}
        income_q = base_income_q()
        income_q[3]["cost_of_revenue"] = "3535000000"
        d, figs_path, packet, _ = self._build("parts", income_q=income_q, figs=figs, lines=lines)
        out = self._run(d, figs_path, packet)
        self.assertTrue(out.startswith("PASS\n"), out)
        # a part that is not on its line, and parts that don't add up, both fail
        figs["quarter"]["cost_of_revenue"] = {"v": 5158, "parts": [{"v": 2000, "line": 13}, {"v": 3000, "line": 14}]}
        d2, figs_path2, packet2, original2 = self._build("parts_bad", income_q=income_q, figs=figs, lines=lines)
        out2 = self._run(d2, figs_path2, packet2)
        self.assertTrue(out2.startswith("FAIL\n"), out2)
        self.assertIn("not on line 14", out2)
        self.assertIn("do not add up", out2)
        self.assertEqual(_readb(os.path.join(d2, "income_q.json")), original2)

    def _year_end(self, name, q4_rev):
        """Q4 revenue 10,409 = full year 35,909 − Webull's three quarters (9,000 + 8,500 + 8,000)."""
        lines = LINES + ["Full year revenue $35,909 and a year earlier $31,300",
                         "Full year operating income $11,958 and a year earlier $9,000",
                         "Full year gross profit $17,851 and a year earlier $15,000",
                         "Full year net income $9,618 and a year earlier $8,000",
                         "Full year diluted EPS $12.04 and diluted shares 799",
                         f"A year earlier quarter revenue restated $6,650"]
        figs = base_figs()
        figs["fiscal_year_end"] = True
        figs["quarter"]["total_revenue"] = _fig(q4_rev, 3)
        figs["year_ago"]["total_revenue"] = _fig(6650, 18)  # differs from Webull's 6,800 by 2.2%
        figs["annual"] = {"total_revenue": _fig(35909, 13), "op_income": _fig(11958, 14), "gross_profit": _fig(17851, 15),
                          "net_income": _fig(9618, 16), "diluted_eps": _fig(12.04, 17), "diluted_avg_shares": _fig(799, 17)}
        figs["annual_year_ago"] = {"period_end": "2025-10-26", "total_revenue": _fig(31300, 13), "op_income": _fig(9000, 14),
                                   "gross_profit": _fig(15000, 15), "net_income": _fig(8000, 16)}
        d, figs_path, packet, original = self._build(name, figs=figs, lines=lines)
        with open(os.path.join(d, "income_a.json"), "w") as f:
            json.dump([{"end_date": "2025-10-26", "currency": "USD", "total_revenue": "31300000000", "op_income": "9000000000",
                        "gross_profit": "15000000000", "net_income": "8000000000"}], f)
        return d, figs_path, packet, original

    def test_year_end_restated_year_ago_quarter_is_excused_when_full_year_agrees(self):
        d, figs_path, packet, _ = self._year_end("ye_ok", 10409)
        out = self._run(d, figs_path, packet)
        self.assertTrue(out.startswith("PASS\n"), out)
        self.assertIn("excused", out)

    def test_year_end_not_excused_when_quarter_is_not_year_minus_three_quarters(self):
        lines_q = 10409  # same printed value, but make Webull's quarters disagree with the full year
        d, figs_path, packet, original = self._year_end("ye_bad", lines_q)
        rows = _readj(os.path.join(d, "income_q.json"))
        rows[0]["total_revenue"] = "9500000000"
        with open(os.path.join(d, "income_q.json"), "w") as f:
            json.dump(rows, f)
        out = self._run(d, figs_path, packet)
        self.assertTrue(out.startswith("FAIL\n"), out)
        self.assertIn("year-ago total_revenue", out)
        self.assertIn("full year minus", out)
