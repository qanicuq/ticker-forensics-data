# Recession Alert

Checks free US economic data from FRED every weekday and pushes to your phone (ntfy)
only when something changes. Every Monday it sends a short summary so you know it's alive.
If the bot fails, or the data stops updating, it tells you, so silence never means "all clear" by mistake.

## What it watches

| Signal | Kind | Danger line |
|---|---|---|
| Yield curve (10-year minus 3-month Treasury bill) | early | below 0 now, or in the last 12 months |
| Credit spread (Moody's Baa bonds minus 10-year) | early | risen by the amount in `config.json` above its 12-month low |
| Jobless claims (4-week average) | early | this % above its 52-week low (`config.json`) |
| Sahm Rule (real-time version) | it's here | 0.50 |
| Jobs (3-month average change, as first published) | it's here | below 0 |

## Alert levels

- 👀 **WATCH**: 1 early signal on
- ⚠️ **WARNING**: 2 or 3 early signals on
- 🚨 **RECESSION SIGNAL**: Sahm Rule or falling jobs

`config.json` comes from the history test (`results/RESULTS.md`): settings picked on 1968-1999 only,
judged on 2000-today. Signals must last the number of months in `config.json`.

Not used: ISM manufacturing index (removed from FRED in 2016 at ISM's request) and the
Conference Board Leading Economic Index (full history needs a paid subscription).

## Files

- `signals.py`: readings, signals, levels (same code for history test and daily check)
- `backtest.py`: history test, writes `results/`
- `alert.py`: daily check, writes `state.json`
- Workflows: `Recession history test` and `Recession check` (repo secrets `FRED_API_KEY`, `NTFY_TOPIC`)
