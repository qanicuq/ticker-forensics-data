#!/usr/bin/env node
/* Runs the Ticker Forensics page's value engine (engine.js, copied verbatim from the page)
   on Webull tool results saved as files, so the cloud worker builds the same report the page would.

   usage: node engine/run_engine.js TICKER CATEGORY DIR [PACKET_JSON] > engine.json

   DIR holds one file per Webull tool result, saved exactly as the tool returned it:
     snapshot.json  bars.json  profile.json
     income_q.json  income_a.json  cashflow_q.json  cashflow_a.json  balance_q.json  balance_a.json
     rating.json  target.json  alert.json
   A missing or unreadable file is listed in "missing". The 10-year Treasury yield comes from the
   SEC packet (macro.10y_treasury), and so does the exchange rate for companies reporting in another
   currency (fx). Insider and institutional data need Alpha Vantage, which only
   the page has, so they are always listed as missing here. */
const fs = require("fs"), path = require("path");
const { engine, findArr } = require("./engine.js");

const [sym, cat, dir, packetPath] = process.argv.slice(2);
if (!sym || !cat || !dir) { console.error("usage: node engine/run_engine.js TICKER CATEGORY DIR [PACKET_JSON]"); process.exit(2); }

const read = f => { try { return JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")); } catch { return null; } };
const missing = [];
const req = (name, f) => { const v = read(f); if (v == null) missing.push(name); return v; };

const snap = findArr(read("snapshot.json"), x => x && x.symbol != null && x.price != null);
if (!snap || !snap.length) { console.error(`No snapshot with a price in ${dir}/snapshot.json`); process.exit(1); }
const bars = read("bars.json");
if (bars == null) { console.error(`No price bars in ${dir}/bars.json`); process.exit(1); }

let tsy = null, fx;
if (packetPath) { try { const pk = JSON.parse(fs.readFileSync(packetPath, "utf8")); const t = pk.macro?.["10y_treasury"]; if (t && t.value != null) tsy = [{ date: t.date, value: t.value }];
  if (pk.fx && pk.fx.usd_per_unit > 0) fx = pk.fx.usd_per_unit; } catch {} }

const D = {
  sym: sym.toUpperCase(), cat, s: snap[0], bars,
  prof: req("company profile", "profile.json"),
  incQ: req("quarterly income statement", "income_q.json"),
  incA: req("annual income statement", "income_a.json"),
  cfQ: req("quarterly cash flow", "cashflow_q.json"),
  cfA: req("annual cash flow", "cashflow_a.json"),
  bsQ: req("quarterly balance sheet", "balance_q.json"),
  bsA: req("annual balance sheet", "balance_a.json"),
  rate: req("analyst rating", "rating.json"),
  tgt: req("analyst target price", "target.json"),
  alert: req("earnings alert", "alert.json"),
  ins: null, inst: null, tsy, missing, fx
};
missing.push("insider trades (Alpha Vantage)", "institutional ownership (Alpha Vantage)");
if (!tsy) missing.push("10-year Treasury yield");

process.stdout.write(JSON.stringify(engine(D)));
