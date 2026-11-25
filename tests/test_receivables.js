/* Days sales outstanding counts money owed by customers only (Webull ar_trade_net), not Webull's total receivables,
   which also holds amounts due from related parties. Nov 25 2026, found on RLX.
   run: node tests/test_receivables.js
   RLX figures are Webull's (RMB thousands, × 1000 here), checked against RLX's Aug 14 2026 6-K balance sheet:
   total 826,709 = accounts and notes receivable 333,047 + amounts due from related parties 483,381
   + receivables from online payment platforms 10,281. Expected day counts were worked out separately in Python. */
const assert = require("assert");
const { engine } = require("../engine/engine.js");
const K = 1e3;
let n = 0; const t = (name, fn) => { fn(); n++; console.log("ok  " + name); };

const ENDS = ["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"];
/* RLX quarterly revenue, total receivables and customer receivables, newest first */
const RLX = {
  rev: [1010453, 1585821, 1141338, 1129271, 879952],
  total: [826709, 888235, 404761, 352976, 407039],
  trade: [333047, 329940, 190442, 202455, 236247] };

function D({ rev, total, trade }, annual) {
  const bars = []; for (let i = 0; i < 260; i++) { const d = new Date(Date.UTC(2025, 6, 1) + i * 864e5).toISOString().slice(0, 10);
    const c = 10 + Math.sin(i / 9); bars.push({ time: d, high: c + 0.1, low: c - 0.1, close: c, volume: 1e6 }); }
  const incQ = ENDS.map((e, i) => ({ end_date: e, currency: "USD", total_revenue: String(rev[i] * K), cost_of_revenue: String(rev[i] * K * 0.65),
    op_income: String(rev[i] * K * 0.1), net_income: String(rev[i] * K * 0.08), gross_profit: String(rev[i] * K * 0.35), diluted_avg_shares: "1000000000" }));
  const bsQ = ENDS.map((e, i) => {
    const b = { end_date: e, currency: "USD", total_assets: "16851211000", total_cur_assets: "10790104000", total_cur_liab: "1017095000",
      total_liab: "1225020000", total_sh_equity: "15512261000", retained_earnings: "4147102000" };
    if (total[i] != null) b.total_recv_net = String(total[i] * K);
    if (trade[i] != null) b.ar_trade_net = String(trade[i] * K);
    return b; });
  const d = { sym: "TEST", cat: "x", sic: 2111, s: { symbol: "TEST", price: "10", market_value: "10000000000" }, bars, missing: [],
    prof: { company_name: "Test Co", industries: ["Group", "Tobacco"] }, incQ, bsQ,
    cfQ: ENDS.slice(0, 4).map(e => ({ end_date: e, cfo: "100000000", capex: "-10000000" })) };
  if (annual) Object.assign(d, annual);
  return d;
}
const run = d => engine(d).analysis;
const dso = a => a.forensic.metrics.find(m => m.name === "Days sales outstanding");
const flagOf = (a, issue) => a.redFlags.find(f => f.issue === issue);

t("RLX: customers only, 24 → 30 days (+23%): medium flag, not high", () => {
  const a = run(D(RLX));
  assert.strictEqual(dso(a).value, "30 days (was 24)"); assert.strictEqual(dso(a).status, "warn");
  assert.strictEqual(flagOf(a, "Customers are taking longer to pay").severity, "medium"); });
t("RLX: the jump in non-customer receivables gets its own flag", () => {
  const f = flagOf(run(D(RLX)), "Money owed by others than customers jumped");
  assert.ok(f, "no flag"); assert.strictEqual(f.severity, "medium");
  /* 407,039 − 236,247 = 170,792; 826,709 − 333,047 = 493,662; 493,662 ÷ 1,010,453 = 48.9% */
  assert.ok(f.detail.includes("rose from $170.79M to $493.66M in a year, 49% of the quarter's sales"), f.detail); });
t("no customer line in either quarter: falls back to the total and says so", () => {
  const a = run(D({ ...RLX, trade: [null, null, null, null, null] }));
  assert.strictEqual(dso(a).value, "75 days (was 42) (all receivables: Webull has no customer-only line)");
  assert.strictEqual(dso(a).status, "bad");
  assert.ok(!flagOf(a, "Money owed by others than customers jumped")); });
t("customer line in only one of the two quarters: total for both (never mixes the two)", () => {
  const a = run(D({ ...RLX, trade: [333047, 329940, 190442, 202455, null] }));
  assert.ok(dso(a).value.startsWith("75 days (was 42)"), dso(a).value); });
t("customer line equal to the total (most US companies): same result as before", () => {
  const a = run(D({ ...RLX, trade: RLX.total }));
  assert.strictEqual(dso(a).value, "75 days (was 42)"); assert.ok(!flagOf(a, "Money owed by others than customers jumped")); });
t("non-customer receivables doubled but under 10% of the quarter's sales: no flag", () => {
  /* other: 40,000 → 90,000 (2.25×), 90,000 ÷ 1,010,453 = 8.9% */
  const a = run(D({ ...RLX, total: [423047, 888235, 404761, 352976, 276247] }));
  assert.ok(!flagOf(a, "Money owed by others than customers jumped")); });
t("non-customer receivables up but not doubled: no flag", () => {
  /* other: 300,000 → 493,662 (1.65×) */
  const a = run(D({ ...RLX, total: [826709, 888235, 404761, 352976, 536247] }));
  assert.ok(!flagOf(a, "Money owed by others than customers jumped")); });

/* Beneish M-score: DSRI uses customer receivables when both years have the line. M changes by exactly 0.92 × the DSRI change. */
function annual(withTrade) {
  const y = [{ e: "2025-12-31", rev: 3958861, tot: 404761, tr: 190442 }, { e: "2024-12-31", rev: 2748576, tot: 331745, tr: 145383 }];
  return {
    incA: y.map(x => ({ end_date: x.e, currency: "USD", total_revenue: String(x.rev * K), gross_profit: String(x.rev * K * 0.35), net_income: String(x.rev * K * 0.2),
      op_income: String(x.rev * K * 0.1), sga_exp: String(x.rev * K * 0.15), diluted_avg_shares: "1000000000" })),
    cfA: y.map(x => ({ end_date: x.e, cfo: String(x.rev * K * 0.21), capex: "-10000000", dna: "40000000" })),
    bsA: y.map(x => ({ end_date: x.e, currency: "USD", total_assets: "17000000000", total_cur_assets: "11000000000", total_cur_liab: "1500000000",
      total_liab: "2000000000", total_sh_equity: "15000000000", ppe_net: "300000000", retained_earnings: "4000000000",
      total_recv_net: String(x.tot * K), ...(withTrade ? { ar_trade_net: String(x.tr * K) } : {}) })) };
}
t("Beneish uses customer receivables when both years have them", () => {
  const mTr = run(D(RLX, annual(true))).forensic.beneish, mTot = run(D(RLX, annual(false))).forensic.beneish;
  const dsriTr = (190442 / 3958861) / (145383 / 2748576), dsriTot = (404761 / 3958861) / (331745 / 2748576);
  assert.ok(Number.isFinite(mTr) && Number.isFinite(mTot));
  assert.ok(Math.abs((mTr - mTot) - 0.92 * (dsriTr - dsriTot)) < 1e-9, `${mTr} ${mTot}`); });

console.log(`\n${n} tests passed`);
