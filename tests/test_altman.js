/* Altman Z (manufacturers, SEC industry code 2000-3999) vs Z″ (all other non-financial companies). Nov 20 2026.
   run: node tests/test_altman.js
   Inputs are Webull's figures on Nov 20 2026 (newest quarter's balance sheet, last 4 quarters of operating income and
   revenue, the snapshot's market value); the expected scores were worked out separately in Python, not by this code. */
const assert = require("assert");
const { engine, altman, isMakerByName } = require("../engine/engine.js");
const M = 1e6, r4 = x => Math.round(x * 1e4) / 1e4;
let n = 0; const t = (name, fn) => { fn(); n++; console.log("ok  " + name); };

/* ---- the two formulas on real companies ---- */
const SD = { wc: (111.480 - 73.144) * M, re: -393.780 * M, ebit: (15.730 + 25.957 + 17.856 + 15.187) * M, ta: 712.703 * M, tl: 143.167 * M,
  mcap: 440091866.40, rev: (54.416 + 51.117 + 49.777 + 39.400) * M, equity: 569.536 * M };
t("SD (oil producer, SIC 1311): Z″ 3.4333 safe", () => { const a = altman(false, SD); assert.deepStrictEqual([r4(a.z), a.version, a.zone], [3.4333, "Z″", "safe"]); });
t("SD under the old 1968 Z: 1.7546 distress", () => { const a = altman(true, SD); assert.deepStrictEqual([r4(a.z), a.version, a.zone], [1.7546, "Z", "distress"]); });

const BB = { wc: (561.9 - 236.5) * M, re: -2121.9 * M, ebit: (33.6 + 15.3 + 22.9 + 11.9) * M, ta: 1263 * M, tl: 471.4 * M,
  mcap: 4578851776.20, rev: (163.3 + 152.9 + 156.0 + 141.8) * M, equity: 791.6 * M };
t("BB (software, SIC 7372): Z″ -1.5783 distress", () => { const a = altman(false, BB); assert.deepStrictEqual([r4(a.z), a.zone], [-1.5783, "distress"]); });
t("BB under the old 1968 Z: 4.4899 safe", () => { const a = altman(true, BB); assert.deepStrictEqual([r4(a.z), a.zone], [4.4899, "safe"]); });

const AVA = { wc: (728 - 761) * M, re: 957 * M, ebit: (66 + 54 + 134 + 112) * M, ta: 8697 * M, tl: 5867 * M, equity: 2830 * M };
t("AVA (utility, SIC 4931): Z″ 1.1231 grey", () => { const a = altman(false, AVA); assert.deepStrictEqual([r4(a.z), a.zone], [1.1231, "grey"]); });

const LRCX = { wc: (18124.112 - 7312.499) * M, re: 37291.174 * M, ebit: (3283.727 + 2513.488 + 2047.016 + 1810.203) * M, ta: 26353.056 * M,
  tl: 12444.582 * M, mcap: 230097298200.0, rev: (8219.418 + 6722.238 + 5841.488 + 5344.791) * M, equity: 13908.474 * M };
t("LRCX (chip-equipment maker, SIC 3559): Z 15.7677 safe", () => { const a = altman(true, LRCX); assert.deepStrictEqual([r4(a.z), a.version, a.zone], [15.7677, "Z", "safe"]); });

/* ---- zone edges: under 1.8 / 1.1 is distress, 3 / 2.6 or more is safe ---- */
const one = { wc: 0, re: 0, ebit: 0, ta: 1, tl: 1, rev: 0 };
t("Z edges: 1.8 is grey, 3 is safe", () => {
  assert.strictEqual(altman(true, { ...one, mcap: 1.8 / 0.6, rev: 1e-12 }).zone, "grey");
  assert.strictEqual(altman(true, { ...one, mcap: 1.7999 / 0.6, rev: 1e-12 }).zone, "distress");
  assert.strictEqual(altman(true, { ...one, mcap: 3 / 0.6, rev: 1e-12 }).zone, "safe"); });
t("Z″ edges: 1.1 is grey, 2.6 is safe", () => {
  assert.strictEqual(altman(false, { ...one, equity: 1.1 / 1.05 }).zone, "grey");
  assert.strictEqual(altman(false, { ...one, equity: 1.0999 / 1.05 }).zone, "distress");
  assert.strictEqual(altman(false, { ...one, equity: 2.6 / 1.05 }).zone, "safe"); });

/* ---- missing data gives no score, never a made-up one ---- */
t("no score without total assets or total liabilities", () => {
  assert.strictEqual(altman(false, { ...SD, ta: null }), null); assert.strictEqual(altman(false, { ...SD, tl: 0 }), null);
  assert.strictEqual(altman(true, { ...SD, ta: 0 }), null); });
t("Z needs market value and revenue; Z″ needs book equity", () => {
  assert.strictEqual(altman(true, { ...SD, mcap: null }), null); assert.strictEqual(altman(true, { ...SD, rev: null }), null);
  assert.strictEqual(altman(false, { ...SD, equity: null }), null);
  assert.ok(altman(false, { ...SD, mcap: null, rev: null })); });  /* Z″ uses neither */

/* ---- name fallback (Webull industry), used when there is no SEC code (the page has no data packet) ---- */
t("industry names: makers", () => { for (const s of ["Semiconductor Equipment & Testing", "Semiconductors", "Pharmaceuticals", "Specialty Chemicals",
  "Auto & Truck Manufacturers", "Aerospace & Defense", "Iron & Steel", "Industrial Machinery & Equipment", "Food Processing", "Oil & Gas Refining and Marketing"])
  assert.strictEqual(isMakerByName(s), true, s); });
t("industry names: not makers", () => { for (const s of ["Oil & Gas Exploration and Production", "Multiline Utilities", "Electric Utilities",
  "Business Support Services", "Software", "Homebuilding", "Pharmacies & Drug Retailers", "Medical Equipment, Supplies & Distribution", "", null, undefined])
  assert.strictEqual(isMakerByName(s), false, String(s)); });

/* ---- the engine: SEC code first, then the name; the zone drives the strength score and the AVOID rule ---- */
function D(industry, sic, over = {}) {
  const bars = []; for (let i = 0; i < 260; i++) { const d = new Date(Date.UTC(2025, 10, 7) + i * 864e5).toISOString().slice(0, 10);
    const c = 10 + Math.sin(i / 9); bars.push({ time: d, high: c + 0.1, low: c - 0.1, close: c, volume: 1e6 }); }
  const q = e => ({ end_date: e, currency: "USD", total_revenue: "100", op_income: "-5", net_income: "-5", gross_profit: "40", diluted_avg_shares: "10", ...over.inc });
  return { sym: "TEST", cat: "x", sic, s: { symbol: "TEST", price: "10", market_value: "50" }, bars, missing: [],
    prof: { company_name: "Test Co", industries: ["Group", industry] },
    incQ: ["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31"].map(q),
    cfQ: ["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31"].map(e => ({ end_date: e, cfo: "-1", capex: "-2" })),
    bsQ: [{ end_date: "2026-09-30", total_assets: "1000", total_cur_assets: "100", total_cur_liab: "200", total_liab: "900",
      retained_earnings: "-500", total_sh_equity: "100", ...over.bs }] };
}
const run = d => engine(d).analysis;
t("SEC code 3559 overrides a non-maker name: Z", () => { const f = run(D("Software", 3559)).forensic;
  assert.deepStrictEqual([f.altmanVersion, f.altmanBasis], ["Z", "SEC industry code 3559"]); });
t("SEC code 1311 overrides a maker name: Z″", () => { const f = run(D("Semiconductors", 1311)).forensic;
  assert.deepStrictEqual([f.altmanVersion, f.altmanBasis], ["Z″", "SEC industry code 1311"]); });
t("no SEC code: the Webull industry name decides", () => {
  assert.strictEqual(run(D("Semiconductors", undefined)).forensic.altmanVersion, "Z");
  const f = run(D("Oil & Gas Exploration and Production", null)).forensic;
  assert.deepStrictEqual([f.altmanVersion, f.altmanBasis], ["Z″", "industry name (Oil & Gas Exploration and Production)"]); });
t("distress zone + negative free cash flow = AVOID, labelled with the version used", () => { const a = run(D("Software", 7372));
  assert.strictEqual(a.forensic.altmanZone, "distress");
  assert.strictEqual(a.verdict, "AVOID"); assert.ok(a.redFlags.some(f => f.issue === "Altman Z″ in the distress zone" && f.severity === "high"));
  assert.ok(a.forensic.metrics.some(m => m.name === "Altman Z″-score" && m.status === "bad")); });
t("grey zone: no AVOID from the Altman rule", () => {
  /* Z″ = 6.56×(100−100)/1000 + 3.26×200/1000 + 6.72×(−20)/1000 + 1.05×500/500 = 0 + 0.652 − 0.1344 + 1.05 = 1.5676 (grey) */
  const a = run(D("Software", 7372, { bs: { retained_earnings: "200", total_liab: "500", total_sh_equity: "500", total_cur_liab: "100" } }));
  assert.strictEqual(a.forensic.altmanZone, "grey"); assert.ok(!a.redFlags.some(f => /Altman/.test(f.issue)));
  assert.notStrictEqual(a.verdictWhy, "Distress-zone balance sheet and burning cash"); });
t("banks still get no Altman score", () => { const f = run(D("Banks", 6021)).forensic;
  assert.strictEqual(f.altmanZ, undefined); assert.ok(!f.metrics.some(m => /Altman/.test(m.name))); });

console.log(`\n${n} tests passed`);
