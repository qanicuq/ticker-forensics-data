/* Two fixes found on RLX's Nov 27 2026 report.
   1) Webull's analyst targets for RLX come in CNY (median 16.954), but the report showed them as dollars ("$16.95, +897%").
      They are now converted with the financials' exchange rate, or left out when that rate is for another currency.
   2) Free cash flow paired 12-month operating cash flow with last fiscal year's capex when Webull's quarterly cash flow has
      no capex line (RLX), under a "last fiscal year" label (0.7%). Both now come from the same period.
   run: node tests/test_fx_targets_fcf.js
   RLX figures: Webull quarterly cfo (CNY), Webull targets (CNY, Nov 26 2026), SEC 20-F FY2025 cfo 1,104,548k and capex 117,729k,
   CNY rate 0.150509 (packet, Nov 27 2026), Webull market cap 2,077,832,758.8 at $1.70. Expected values worked out by hand. */
const assert = require("assert");
const { engine } = require("../engine/engine.js");
let n = 0; const t = (name, fn) => { fn(); n++; console.log("ok  " + name); };

const ENDS = ["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30"];
const FX = 0.150509, MCAP = 2077832758.8;
function D({ cur = "CNY", tgt, cfQcapex = false, annualCf = true } = {}) {
  const bars = []; for (let i = 0; i < 260; i++) { const d = new Date(Date.UTC(2025, 6, 1) + i * 864e5).toISOString().slice(0, 10);
    const c = 1.7 + 0.02 * Math.sin(i / 9); bars.push({ time: d, high: c + 0.01, low: c - 0.01, close: c, volume: 2e6 }); }
  const rev = [1916.6e6, 1010.453e6, 1585.821e6, 1141.338e6, 1129.271e6];
  const incQ = ENDS.map((e, i) => ({ end_date: e, currency: cur, total_revenue: String(rev[i]), cost_of_revenue: String(rev[i] * 0.7),
    op_income: String(rev[i] * 0.05), net_income: String(rev[i] * 0.1), gross_profit: String(rev[i] * 0.3), diluted_avg_shares: "1250000000" }));
  const bsQ = ENDS.map(e => ({ end_date: e, currency: cur, total_assets: "17000000000", total_cur_assets: "11000000000", total_cur_liab: "1500000000",
    total_liab: "1800000000", total_sh_equity: "15200000000", retained_earnings: "4100000000" }));
  const cfo = [40041000, -63227000, -68841000, 310221000];
  const cfQ = ENDS.slice(0, 4).map((e, i) => { const r = { end_date: e, currency: cur, cfo: String(cfo[i]) }; if (cfQcapex) r.capex = "-30000000"; return r; });
  const d = { sym: "RLX", cat: "x", sic: 2111, fx: cur === "USD" ? undefined : FX,
    s: { symbol: "RLX", price: "1.70", market_value: String(MCAP), pe_ratio: "16.8", ps_ratio: "2.46" }, bars, missing: [],
    prof: { company_name: "Test Co", industries: ["Group", "Tobacco"] }, incQ, bsQ, cfQ,
    rate: { number: 6, strong_buy: 3, buy: 2, hold: 1, sell: 0 } };
  if (annualCf) d.cfA = [{ end_date: "2025-12-31", currency: cur, cfo: "1104548000", capex: "-117729000" }];
  if (tgt) d.tgt = tgt;
  return d;
}
const run = d => engine(d).analysis;
const CNY_TGT = { mean: "16.66983", low: "10.013", high: "21.345", median: "16.954", currency: "CNY" };
const near = (a, b, tol = 0.005) => assert.ok(Math.abs(a - b) <= tol, `${a} not near ${b}`);

t("RLX: CNY targets are converted to dollars ($2.55, +50.1%)", () => {
  const a = run(D({ tgt: CNY_TGT }));
  assert.ok(a.analystView.includes("Median target $2.55 (+50.1% from here)"), a.analystView);
  near(a.priceTargets.base, 16.954 * FX); near(a.priceTargets.bull, 21.345 * FX); near(a.priceTargets.bear, 10.013 * FX);
});

t("targets in a currency other than the financials' are left out, with a note", () => {
  const a = run(D({ cur: "USD", tgt: CNY_TGT }));
  assert.ok(!a.analystView.includes("Median target"), a.analystView);
  assert.ok(a.analystView.includes("Targets are in CNY and couldn't be converted to dollars, so they aren't shown."), a.analystView);
  near(a.priceTargets.base, 1.70, 0.05);
});

t("dollar targets are unchanged", () => {
  const a = run(D({ cur: "USD", tgt: { mean: "2.6", low: "1.5", high: "3.2", median: "2.55", currency: "USD" } }));
  assert.ok(a.analystView.includes("Median target $2.55 (+50.0% from here)"), a.analystView);
  near(a.priceTargets.base, 2.55, 1e-9);
});

t("targets with no currency are unchanged (old behaviour)", () => {
  const a = run(D({ tgt: { mean: "2.6", low: "1.5", high: "3.2", median: "2.55" } }));
  near(a.priceTargets.base, 2.55, 1e-9);
});

t("RLX: no quarterly capex, so free cash flow is the last fiscal year's on both lines (7.1%)", () => {
  const a = run(D());
  /* (1,104,548k − 117,729k) × 0.150509 = $148.5M ÷ $2,077.8M = 7.1% (old code: 12-month cfo 218,194k − 117,729k → 0.7%) */
  assert.ok(a.fundamentals.valuation.includes("free-cash-flow yield 7.1% (last fiscal year)"), a.fundamentals.valuation);
});

t("quarterly cfo and capex both present: 12-month free cash flow, as before", () => {
  const a = run(D({ cfQcapex: true }));
  /* (218,194k − 120,000k) × 0.150509 = $14.8M ÷ $2,077.8M = 0.7% */
  assert.ok(a.fundamentals.valuation.includes("free-cash-flow yield 0.7% (last 12 months)"), a.fundamentals.valuation);
});

t("no annual cash flow and no quarterly capex: no free cash flow shown", () => {
  const a = run(D({ annualCf: false }));
  assert.ok(!a.fundamentals.valuation.includes("free-cash-flow yield"), a.fundamentals.valuation);
});

console.log`${n} tests passed`);
