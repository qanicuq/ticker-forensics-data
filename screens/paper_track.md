# Diamond Finder: honest forward test

Updated with closes through 2026-11-20. Paper money only. 1 monthly basket(s) per method so far.

Each month, two paper baskets of the top 20 stocks are bought at that run's closing prices: one by the **new ranking** (clean stocks first, price-to-cash-flow factor; from 2026-11-15) and one by the **old ranking** (before 2026-11-15). Each is held 12 months. Costs of 0.5% per buy and per sell are taken off (assumed bid/ask spread; stock commissions are $0). A stock that stops trading counts as $0 until checked by hand. Baselines: IWN (small-cap value ETF) and SPY (S&P 500 ETF).

| Month | New ranking | Old ranking | IWN | SPY |
|---|---|---|---|---|
| 2026-11 (so far) | -9.0% | -8.7% | -6.5% | -8.6% |
| **Total so far** | **-9.0%** | **-8.7%** | **-6.5%** | **-8.6%** |

## How to read this

- **Versions tried: 2** (old and new ranking). With more than one version, the better-looking one is partly ahead by luck, so discount its lead.
- Judge only after at least 12 months, and only against IWN. A few months, or one good year, proves little (SKILL.md: about 30 years of results are needed to be 95% sure).
- These are equal-weight baskets, so there is no bet sizing to test here.
- This is a test of the screen, not a buy list. Real trading would also need the full research in Ticker Forensics.
