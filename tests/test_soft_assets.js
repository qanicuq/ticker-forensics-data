/* Soft assets: a jump on a balance sheet Webull published in the last 7 days is "can not verify", not a flag.
   Nov 26 2026, found on ELF: Webull's first copy of the Sep 30 2026 quarter (published Nov 4) gave 6.5% of assets as
   'other' (the 10-Q's "Other assets" $167,563K of $2,567,248K); its next-day copy moved the $76,861K of leased-property
   assets (10-Q lease note) into property, leaving $90,702K = 3.5%.
   run: node tests/test_soft_assets.js */
const assert = require("assert");
const { engine } = require("../engine/engine.js");
const K = 1e3;
let n = 0; const t = (name, fn) => { fn(); n++; console.log("ok  " + name); };

const ENDS = ["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30"];
const TA = [2567248, 2460649, 2394158, 2323720, 2318782];   /* ELF total assets, $K (Webull = 10-Q) */
const today = new Date().toLocaleDateString("en-CA", { timeZone: "America/New_York" });
const daysAgo = d => new Date(Date.parse(today) - d * 864e5).toISOString().slice(0, 10);

function D(otherLt, pub) {
  const bars = []; for (let i = 0; i < 260; i++) { const d = new Date(Date.UTC(2025, 6, 1) + i * 864e5).toISOString().slice(0, 10);
    const c = 10 + Math.sin(i / 9); bars.push({ time: d, high: c + 0.1, low: c - 0.1, close: c, volume: 1e6 }); }
  const incQ = ENDS.map(e => ({ end_date: e, currency: "USD", total_revenue: "500000000", cost_of_revenue: "150000000",
    op_income: "50000000", net_income: "40000000", gross_profit: "350000000", diluted_avg_shares: "59000000" }));
  const bsQ = ENDS.map((e, i) => {
    const b = { end_date: e, currency: "USD", total_assets: String(TA[i] * K), total_cur_assets: "900000000", total_cur_liab: "350000000",
      total_liab: "1300000000", total_sh_equity: "1200000000", retained_earnings: "-60000000", other_lt_assets: String(otherLt[i] * K) };
    if (i === 0 && pub) b.publish_date = pub;
    return b; });
  return { sym: "TEST", cat: "x", sic: 2844, s: { symbol: "TEST", price: "100", market_value: "6000000000" }, bars, missing: [],
    prof: { company_name: "Test Co", industries: ["Group", "Personal Products"] }, incQ, bsQ,
    cfQ: ENDS.slice(0, 4).map(e => ({ end_date: e, cfo: "60000000", capex: "-5000000" })) };
}
const run = d => engine(d);
const soft = a => a.analysis.forensic.metrics.find(m => m.name === "Soft assets");
const flagOf = a => a.analysis.redFlags.find(f => f.issue === "Soft assets growing");
const ELF_NOW = [90702, 86456, 95007, 95641, 87450];        /* Webull today: 3.5% (was 3.8%) */
const ELF_RAW = [167563, 86456, 95007, 95641, 87450];       /* Webull's first copy: 6.5% (was 3.8%) */
const JUMP = [241000, 86456, 95007, 95641, 87450];          /* 241,000 / 2,567,248 = 9.4%: a 5.6-point jump */

t("ELF today: 3.5% (was 3.8%), no flag, nothing unverified", () => {
  const a = run(D(ELF_NOW, daysAgo(22)));
  assert.strictEqual(soft(a).value, "3.5% of assets (was 3.8%)"); assert.ok(!flagOf(a)); assert.deepStrictEqual(a.unverified, []); });
t("ELF first copy: 6.5% (was 3.8%), under the 5-point line: no flag, nothing unverified", () => {
  const a = run(D(ELF_RAW, daysAgo(0)));
  assert.strictEqual(soft(a).value, "6.5% of assets (was 3.8%)"); assert.ok(!flagOf(a)); assert.deepStrictEqual(a.unverified, []); });
t("jump on a balance sheet published 2 days ago: can not verify, no flag", () => {
  const a = run(D(JUMP, daysAgo(2)));
  assert.ok(!flagOf(a)); assert.strictEqual(soft(a).status, "warn");
  assert.deepStrictEqual(a.unverified, ["the soft-assets jump (3.8% to 9.4% of assets; Webull published this balance sheet 2 days ago and may still be adjusting it: check the 10-Q)"]);
  assert.ok(a.missing.includes("Soft-assets check (Webull published this quarter's balance sheet 2 days ago; it may not be final)"), a.missing); });
t("published 7 days ago: still can not verify", () => {
  const a = run(D(JUMP, daysAgo(7))); assert.ok(!flagOf(a)); assert.strictEqual(a.unverified.length, 1); });
t("published 8 days ago: medium flag as before", () => {
  const a = run(D(JUMP, daysAgo(8))); assert.strictEqual(flagOf(a).severity, "medium"); assert.deepStrictEqual(a.unverified, []); });
t("no publish date from Webull: medium flag as before", () => {
  const a = run(D(JUMP, null)); assert.strictEqual(flagOf(a).severity, "medium"); assert.deepStrictEqual(a.unverified, []); });
console.log(`${n} tests passed`);
