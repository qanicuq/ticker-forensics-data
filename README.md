# ticker-forensics-data
Data layer for Ticker Forensics: gathers compact JSON packets from open-source libraries

`engine/` holds a copy of the Ticker Forensics page's value engine. The cloud worker runs `node engine/run_engine.js` on saved Webull results to build reports for requests that don't come from the page (e.g. Option Calc). If the page's engine changes, copy it here too.

`diamond_screen.py` (workflow `Diamond Screen`) runs Mon/Wed/Fri after the close and saves a shortlist of cheap, financially sound small caps to `screens/diamond_screen.md`, using the value-investing-library SKILL.md rules (copy in `skill/value-investing-library/SKILL.md`). It finds candidates to research in Ticker Forensics, not buys.

## Cheap Options Scan
The Cheap Options Scan looks for stock options whose prices imply less movement than the stock has actually shown over the last 20 trading days. It runs every weekday during market hours and sends a phone notification only when it finds unusually cheap options. Add your favorite tickers to `screens/cheap_options_watchlist.txt` to include them in the scan.

## Past Calls Report Card
Every Forensic Analysis verdict is saved to `calls/log.csv` by `worker/log_call.py`. Each Saturday, `score_calls.py` (workflow `Past Calls Report Card`) checks how each call did after 30, 90 and 180 days, starting from the first close after the call, compared with SPY, and writes `calls/scorecard.md`. AVOID calls count as right when the stock trails SPY.
