---
name: value-investing-library
description: Chris's value-investing playbook from 18 classic investing books. Use when analyzing or screening stocks, checking accounts for red flags, valuing a business, sizing positions, planning exits, or building stock tools.
---

**Last Updated:** 2026-10-30 (added Dreman, *Contrarian Investment Strategies: The Next Generation*; 18 books).

# Value Investing Library

A working playbook built from detailed notes on 18 books from the Dynamics Associates "Hedge Fund Reading List". It tells you how to find, check, value, size, buy, hold and sell stocks the way these authors would, adapted to Chris's style.

**What this skill is and is not.** It holds book knowledge only: methods, rules, thresholds, checklists and lessons. It has no live prices, filings or financial data. When a task needs current numbers, get them from whatever market-data tools the chat has (for example a Webull, Alpha Vantage or SEC/EDGAR connector, or web search), say which numbers are live and which are estimated, and never invent figures. Nothing here is personal financial advice; it is a method for thinking clearly.

**Full notes.** If a `references/` folder sits next to this file, it holds the complete per-book notes (core ideas, rulebook, chapter notes, case index, quotes, modern application, limits, cross-links). Open the relevant file when you need a detail, a case, a quote or a number that this summary leaves out. Book-to-file map is in §12. If the folder is absent, work from this file.

---

## 1. Who this is for

- **Chris** is a value investor. Main hunt: **"diamonds in the rough"**, meaning overlooked, under-followed, underpriced stocks. Second goal: **grow the account steadily over time** (compounding, avoiding big losses).
- He is not a professional analyst. Explain in plain words, lead with the answer, and show the numbers behind any verdict.
- Default framing for any stock: *Is it cheap against a conservative value? Are the numbers real? Why is it cheap? What could go wrong? How much should I own, and when do I sell?*

## 2. The process (use this order every time)

1. **Find**: where to look and quick screens (§3).
2. **Verify**: forensic check of the accounts before trusting any number (§4). Cheapness is a reason to run this harder, not to skip it.
3. **Value**: conservative intrinsic value as a range, on normalised numbers (§5).
4. **Decide**: margin of safety, why it is cheap, catalyst, thesis-break condition (§6).
5. **Size and enter**: risk per position, liquidity, tranches, timing (§7).
6. **Hold and exit**: written exit triggers, when to add, when to sell (§7).
7. **Review**: journal, portfolio circuit breakers, learning from mistakes (§7, §9).

When the user names a ticker, follow §11's analysis template. When building a tool, follow §11's tool guidance.

---

## 3. Find: where diamonds in the rough hide

**Fish where the fish are** (Greenwald, Klarman, Lynch, Greenblatt). The best bargains have a *non-fundamental* reason for being cheap: someone is selling for reasons unrelated to value.
- Neglect: small and micro caps, few or no analysts (today: under ~5 analysts, under ~40-50% *active* institutional ownership), outside major indexes, boring or disagreeable businesses, dull names, no-growth industries, stigma, lawsuits, complexity.
- Forced or rule-bound sellers: spinoffs, index deletions, post-bankruptcy stock, merger securities (bonds, preferreds, warrants, CVRs paid to target holders), rights offerings, tax-loss selling (Oct-Dec), fund mandates (no stocks under $5, dividend-payers only, investment-grade only).
- **Forced seller or broken business? (Chan)** Funds hit by redemptions dump holdings "through no fault or merit on their own"; buying the stocks sold hardest over the past 1-4 quarters earned ~7% a year (Coval and Stafford). Index deletions and ETF rebalancing work the same way. Moves caused by someone needing cash revert; moves caused by a business change don't. The bargain comes *after* the forced selling. Retail signs: 13F stake cuts, fund closures, index reconstitution, spinoff dates, tax-loss season.
- Disappointment: stocks at 52-week, two- or three-year lows, especially after a gap down; three-year losers (but one-year momentum persists short term); new-lows lists.
- Hidden value: real estate at historical cost, equity stakes, net cash, NOLs, a valuable unit inside a dull company (sum of the parts), a loss-making division whose sale or closure lifts EPS.
- Change: spinoffs, restructurings, asset sales, recapitalisations, management changes, capacity leaving an industry, emergence from bankruptcy.
- Your own edge (Lynch): products, stores, suppliers and trends you see at work or as a consumer before Wall Street does. A lead is only a reason to research, never a buy signal.

**Graham screens** (thresholds are Graham's; translate bond yields to today):
- *Defensive (Ch. 14, seven tests):* sales ≥ a meaningful size (Graham: $100m in 1971 dollars, so scale up a lot); current ratio ≥ 2 and long-term debt ≤ net current assets; positive earnings each of the last 10 years; uninterrupted dividends 20 years; EPS up ≥ 1/3 over 10 years (3-yr averages at each end); price ≤ 15 × 3-yr average EPS; price ≤ 1.5 × book, or **P/E × P/B ≤ 22.5**. "Graham number" shorthand: max price = √(22.5 × EPS × BVPS).
- *Enterprising (Ch. 15):* P/E ≤ 9 trailing; current assets ≥ 1.5 × current liabilities; debt ≤ 110% of net current assets; no loss in 5 years; some current dividend; latest EPS > EPS 4 years ago; price < 120% of net tangible assets. Buy as a diversified group.
- *Net-net (NCAV):* current assets − all liabilities − preferred, per share. Buy at ≤ 2/3 of NCAV, diversified (30+), and drop companies with current losses (today most net-nets are cash-burning micro-cap biotechs).
- *Bargain issue:* indicated value ≥ 150% of price. Require stable earnings over a decade and price low against *average* past earnings, not just current (a cyclical at a low P/E on peak earnings is a trap).
- *Graham 1976 simplified:* debt ≤ equity; dividend yield ≥ 2/3 of AAA corporate bond yield; earnings yield ≥ 2 × AAA yield.
- *Near asset value:* price ≤ 1.33 × tangible book, with a satisfactory P/E and strong finances.

**Dreman's contrarian screens** (1,500 largest US stocks, 1970-96). The cheapest 20% by low P/E earned 19.0% a year, low P/B 18.8%, low P/CF 18.0%, high yield 16.1%, vs 14.9% for the market; they also fell less in down quarters and kept winning for 2-8 years after purchase.
- *Quick test:* an established company ≥ 20% below the S&P 500 on P/E, P/CF or P/B, or yield ≥ 1 point above the market's.
- *Industry-relative:* the cheapest 20% within each industry earned 17.7-18.4% and beat the favorites 80-90% of the time, even in expensive industries (a separate effect from absolute cheapness).
- *Small caps only when cheap:* the small-cap effect is really a low-P/E effect ($100-500m: low P/E 18.6% vs high P/E 12.5%). Also require debt ≤ ~60% of capital, a rising above-market dividend, above-average growth.
- Avoid IPOs and concept stocks: 4,753 IPOs (1970-90) earned 3% a year vs 11.3% for the S&P 500; the median IPO lost 39%.

**Lynch's six categories.** Classify first; the category sets realistic upside, the numbers that matter and the sell rule. Re-classify as the story changes.

| Category | What it is | Expect | Buy when | Sell when |
|---|---|---|---|---|
| Slow grower | 2-4% growth, big dividend | Income, low gain | Dividend safe and rising, low payout | After 30-50% gain, or share loss, net cash turning to net debt |
| Stalwart | Big leader, ~10-12% growth | 30-50% in 1-2 yrs, then rotate | P/E at low end of its own range | P/E well above its normal range or peers; growth slowing |
| Fast grower | 20-25% growth, proven formula repeating | Multi-baggers | P/E ≤ growth rate, expansion accelerating, few analysts | Same-store sales falling, expansion stalling, P/E far above growth, crowded ownership |
| Cyclical | Earnings swing with the economy | Big gains if timed; 80-90% losses if not | Trough: losses, high P/E, inventories cleared, capacity leaving | Near peak: low P/E, full capacity, new plants announced, inventories building |
| Turnaround | Battered, maybe near bankruptcy | Fast recovery | Can survive creditors; clear turnaround plan in motion | When it has turned and everyone knows it; debt rising again |
| Asset play | Overlooked assets worth more than price | 2-5x, low risk if values are sure | Assets verified, little debt ahead of you | Value recognised, assets sold for less, new debt or dilution |

PEG check: P/E ≈ growth rate is fair; P/E at half the growth rate is attractive; (growth + dividend yield) ÷ P/E ≥ 2 is excellent. Use sustainable growth, not hope.

**Lynch's ideal company:** dull name, dull or disagreeable business, spinoff, no-growth industry, niche or local monopoly, repeat purchases, user (not maker) of technology, insiders buying, company buying back shares. **Avoid:** hottest stock in the hottest industry, "the next X", diworseification (unrelated acquisitions), whisper stocks, one customer > 25% of sales, exciting names.

**Greenblatt's special situations** (change creates mispricing):
- *Spinoffs:* beat peers ~10%/yr for 3 years historically, most in year 2. Best when institutions don't want it for non-value reasons, insiders get stock and options, and a hidden opportunity is revealed. Read the Form 10. Leveraged spinoffs multiply outcomes both ways. The parent can also be the bargain once the unwanted unit is gone.
- *Merger securities:* yes. Nobody wants the bonds, preferreds, warrants and CVRs; read the proxy/S-4.
- *Post-bankruptcy stock ("orphan equities"):* yes, especially good businesses bankrupted by too much LBO debt. Read the disclosure statement and its projections. Avoid stock of companies *in* bankruptcy.
- *Restructurings:* asset sale or closure big relative to the company, with aligned management and a catalyst.
- *Recaps and stubs; LEAPS and warrants:* leverage on a researched idea with loss capped at the premium. Keep LEAPS to 10-15% of the portfolio.
- *Risk arbitrage:* no, for individuals (make $1-2, lose $10+).
- *Rights offerings used as spinoffs:* "stop and look", especially with oversubscription privileges and insiders exercising.

---

## 4. Verify: the forensic check (Schilit, Financial Shenanigans)

Run this **before** valuing any stock. The question is never just "is the accounting wrong?" but **"what business problem is this accounting hiding?"** Look at at least 8-12 quarters and 3-5 years, and ask "why?" and "why now?" about every change.

**Environment flags (proxy, 8-Ks, auditor's report):** win-at-all-costs culture; boasted streaks of beating estimates; dominant CEO with no checks; weak or captured board and audit committee; pay tied to stock price alone or to non-GAAP metrics; very long auditor tenure; listing via reverse merger or SPAC; executives with past enforcement actions; bought from private equity after an LBO.

**Walk-away signals (until restated numbers are out):** revenue-recognition investigation, non-reliance on prior statements, public fight with the auditor, auditor resignation or withdrawn opinion, late filing (NT 10-K), sudden CFO exit, material weakness. First estimates of restatements are almost always far too small.

**The 15-number quick screen:**

| # | Metric | Red flag |
|---|---|---|
| 1 | Operating cash flow (CFFO) vs net income, also 3-yr cumulative | Income growing, CFFO flat or falling; CFFO persistently below income |
| 2 | Free cash flow = CFFO − capex | FCF falling while earnings look fine (capitalised expenses) |
| 3 | FCF after acquisitions = CFFO − capex − cash paid for acquisitions | Negative year after year at a serial acquirer |
| 4 | DSO = *ending* receivables ÷ revenue × days | Rising faster than history, or sudden fall right after a rise |
| 5 | Receivables growth vs revenue growth | Receivables outgrow sales; new long-term, unbilled or notes receivable |
| 6 | Bad-debt allowance ÷ gross receivables | Falling while receivables rise |
| 7 | DSI = inventory ÷ COGS × days | Rising; inventory far outgrowing expected sales |
| 8 | DPO = payables ÷ COGS × days | A jump driving CFFO growth (unsustainable) |
| 9 | Soft assets (prepaids, other assets, deferred costs, capitalised software) | New account or fast growth |
| 10 | Reserves and accruals (warranty, restructuring, deferred revenue) | Sharp releases (earnings boost) or a cookie-jar build-up |
| 11 | Expense-accrual ratios (bad debt, obsolescence, warranty, returns ÷ revenue) | Several falling at once: "head for the hills" |
| 12 | Gross margin and SG&A ratio vs revenue growth | Operating income growing far faster than revenue |
| 13 | Depreciation ÷ gross PP&E; capitalised software ÷ R&D | Useful lives lengthening; capitalisation share rising |
| 14 | Capex vs guidance and industry | Capex jumps while the industry slumps |
| 15 | Non-GAAP vs GAAP gap | Persistent or widening; the same "one-time" items every year |

**Cash flow swing test:** if CFFO growth comes mostly from one or two working-capital swings (receivables, payables, inventory, taxes) rather than from income, treat that part as non-recurring. Subtract any increase in sold receivables (factoring) from CFFO.

**Where to read:** earnings release and call (headlined metrics, changed definitions); MD&A liquidity; revenue-recognition, receivables, inventory, reserves, acquisitions, related-party and contingency footnotes; changes in estimates; supplemental cash flow; risk factors. Compare each with the prior period: anything new is a big deal.

**Normalising rules:** treat recurring "one-time" charges, restructuring every year, stock-based compensation and acquisition costs at a serial acquirer as real costs. Restore reserves to prior ratios. Restate under old accounting policies. Any growth from an accounting change will not recur. Use FCF after acquisitions for acquirers.

**Value-trap patterns:** cheap after a "small" restatement; cheap on EBITDA or "cash earnings" while GAAP shows losses and debt grows; cheap roll-ups with negative FCF after acquisitions; earnings propped by reserve releases, pension income or useful-life changes; high dividend funded by borrowing. Obscure small caps (the diamond-hunting ground) need the governance screen most: insist on arm's-length revenue, collected cash and a credible auditor. Legal-but-aggressive items (factoring, stretched payables) call for adjustment, not automatic rejection; walk away for substance problems.

---

## 5. Value: conservative intrinsic value as a range

**Principles (Graham, Klarman, Greenwald):** value is a range, not a point. Use several methods; when they disagree, lean toward the lower value. Value from the record and the balance sheet (protection), not from forecasts (prediction). Never take one year's earnings seriously: use 7-10-year averages or mid-cycle numbers. EBITDA is a trap (depreciation is a real cost). DCF is right in theory but fragile: small changes in discount or growth rates swing the terminal value enormously; if small input changes swing value a lot, distrust the method.

**Greenwald's three slices, ordered by reliability:**
1. **Asset value.** Viable industry: reproduction cost (what a new entrant would spend). Dying industry: liquidation value. Rough liquidation haircuts: cash 100%, receivables 85%, inventory 50%, PP&E 45%, goodwill 0. Reproduction adjustments: add back bad-debt allowance and LIFO reserve, mark land to market, cut obsolete inventory, add hidden intangibles (capitalised R&D on a 5-year straight line; 1-3 years of SG&A for customer relationships and distribution). Subtract payables and accruals, then debt (market value) and other real obligations.
2. **Earnings power value (EPV)** = sustainable after-tax operating earnings ÷ cost of capital, assuming **zero growth**. EPV of equity = EPV − debt + excess cash (cash above ~1% of sales) + non-operating assets. Build from EBIT: average recurring "one-time" charges over 5 years and deduct; use mid-cycle margins; add back the growth share of R&D and SG&A (Greenwald used 25% each for Intel); tax at a full normal rate; replace D&A with **maintenance capex** (maintenance capex = total capex − growth capex, where growth capex = average PP&E/sales over 5 years × this year's sales increase). Cost of capital: long Treasury + 1-2 points for stable businesses, higher for cyclical or tech (Greenwald used 8% for WD-40, 12% for Intel). Show EPV at several rates.
3. **Growth value** exists only inside a franchise (see below). Demand that growth come free or serve as the margin of safety.

**Diagnosis: compare asset value with EPV.**
- EPV < asset value: poor management or overcapacity. Value at EPV; upside needs a catalyst (takeover, activist, capacity exit). Growth investment destroys value here.
- EPV ≈ asset value: no competitive advantage. The two confirm each other. Pay nothing for growth.
- EPV > asset value: a franchise. The gap must be explained by a specific, durable barrier to entry, or it will be competed away.

**Real franchises** are rare: government licence or patent; customer captivity (habit, search costs, switching costs); proprietary cost advantage; and the most durable, economies of scale plus some captivity within a local or niche market. A brand alone is not a moat. Evidence: returns on capital above cost of capital for many years, stable market share, failed entrants. Default assumption for most firms: no franchise.

**Growth only adds value when return on capital (ROC) exceeds cost of capital (R).** Value multiple over EPV, M = [1 − (R/ROC)(G/R)] ÷ [1 − G/R]:

| G/R ↓ · ROC/R → | 1.0 | 1.5 | 2.0 | 3.0 |
|---|---|---|---|---|
| 0.25 | 1.00 | 1.11 | 1.17 | 1.22 |
| 0.50 | 1.00 | 1.33 | 1.50 | 1.67 |
| 0.75 | 1.00 | 2.00 | 2.50 | 3.00 |

If ROC = R, growth is worth nothing at any speed. Growth multiples are smaller than most people think: a P/E three times the no-growth P/E needs ROC at 3 × R and growth at 75% of R for a long time.

**Other tools:**
- Graham growth formula: value = normal EPS × (8.5 + 2g), g = 7-10-yr expected growth %. Use it backwards to find the growth a price implies, and ask whether that is plausible.
- Lynch PEG and net cash adjustment ($20m cap, $15m net cash, $1m earnings → real P/E ≈ 5).
- Klarman: going-concern (conservative cash flow, scenarios), liquidation or breakup, and comparables only as a cross-check. Cash flow = after-tax earnings + D&A − capex.
- Cap rate: after-tax EBIT ÷ (equity value + debt − cash). Private-market value from recent deal prices per unit or EV/EBITDA.
- Sum of the parts for conglomerates and companies with listed stakes.
- Historical range: buy when P/E is in the low part of the stock's own range or dividend yield in the high part.
- Leverage shrinks the margin of safety: with $100 of assets and $80 of debt, a 10% asset error halves the equity.
- **Mark forecasts down (Dreman).** Consensus quarterly estimates missed by 44% on average (1973-96), only ~1 in 4 within ±5%, and run too high (S&P growth forecast 21.9%/yr vs 7.8% actual, 1982-97). Cut any forward estimate, avoid methods that need precise forecasts, and expect the worst case to be worse than your first guess.

---

## 6. Decide: margin of safety and the buy case

**Required discount.** Graham: buy at about two-thirds of value or less (margin ~1/3 to 1/2). Michael Price: 40% below value. Klarman: big enough to absorb error, bad luck and a fall in business value, with several independent measures of cheapness at once ("belt and suspenders"). Check the margin every day you hold, not only on purchase.

**Risk is permanent loss of capital, not volatility.** Only a lower price creates excess return; higher risk does not. "Rule No. 1: don't lose money." Compounding makes one big loss ruinous.

**Pre-purchase checklist** (Klarman, Graham/Zweig, Lynch, Schwager combined; "no checklist, no buy"):
1. What is it worth? Low end of a range from at least two methods, on normalised numbers.
2. How big is the discount? Is value mostly tangible or proven earnings?
3. **Why is it cheap?** Name the seller and their reason. If the reason is fundamental, what am I missing?
4. Did the forensic check (§4) come back clean?
5. What could go wrong? Leverage, refinancing, contingent liabilities, cash burn, customer concentration, binary events.
6. Catalyst: what will make the market see the value, and roughly when? (Valuation sets the distance; a catalyst sets the timing.)
7. Who runs it, and are they aligned? Owner-operators with big personal stakes; open-market insider buying (Form 4 code "P", clusters); buybacks that shrink the share count net of stock comp. Who pays if the strategy fails?
8. Do I understand it? Can I tell the story in two minutes? If not, pass.
9. Is it better than what I own, and better than cash?
10. Would I happily buy more 20-30% lower? If not, don't buy.
11. **Thesis-break condition written down:** the observable fact that would prove me wrong.
12. If the market closed for five years, would I still want to own it?
13. Premortem: if this is a disaster in three years, why?

**Dreman's five checks** (start from the cheapest 40%): strong finances; good operating ratios; earnings growth recently at least the market's and **not expected to keep falling** (moderate drops become cliffs); a conservative estimate; an above-average dividend the company can sustain and raise.
- A dividend kept or raised through trouble signals management's confidence (after cuts stocks lagged the market 11% the next year; after increases they beat it 7.5%).
- A cheap stock that looks "too perfect" deserves the forensic check twice; when management's reassurances prove false, sell (Westinghouse).
- Cyclicals: judge on P/CF, P/B or ~5-year average earnings. Loss-makers: small positions, only with certain financial strength.

**Courage of your knowledge.** "You are neither right nor wrong because the crowd disagrees with you. You are right because your data and reasoning are right" (Graham). Mr. Market is a servant, not a guide: use his prices, never take them as information about value.

---

## 7. Size, enter, hold, exit, hedge

**Sizing (Schwager, Klarman, Taleb):**
- Size from the downside, not the upside: dollars at risk = position size × (price − realistic value if the thesis is wrong). Keep that near 1-2% of the account, up to 3-5% for top-conviction ideas with a hard asset floor. A real margin of safety allows a larger position for the same dollars at risk.
- Concentration: 10-15 well-understood positions (Klarman, Greenwald); Greenblatt says 6-8 in different industries captures most diversification. Correlated cheap stocks (three regional banks, four oil-service names) are one bet: cap the theme, not just the ticker. A *mechanical* cheap-stock basket needs 20-30 equal-weight names across 15+ industries, twice that for small caps (Dreman).
- Liquidity: cap a position at what you could sell in a few days of normal volume; assume the bid disappears in a crash. Illiquid small caps are exactly where traders got trapped in 1987. Count the spread as a cost ($2.50 bid / $3.50 ask needs +40% to break even); use limit orders (Dreman).
- No leverage on value positions: value can take years, and leverage turns "early" into "wiped out". Never invest money needed in the next 2-3 years.
- Binary events (FDA, litigation, refinancing, rulings): size as if the bad outcome is plausible, or wait.
- Sleep test: if it halved tomorrow, could you act calmly? If not, it is too big.
- **Sizing a strategy or bot (Chan, Kelly).** Kelly needs a track record, so use it for a strategy (the paper bot, a mechanical basket), not one stock: f = m ÷ s² (mean excess return over its variance). Errors in m or s lead to ruin, so **half-Kelly is a ceiling, not a target**, and never leverage (6% excess return at 25% volatility: Kelly ≈ 0.96, so at most about half the account). Short paper records call for less.
- **Risk budget with an off switch (Chan's CPPI).** Decide the most you will lose to a strategy (say half the account); only that slice trades. Reset it to that fraction at each new account high; never top it up after losses. If it is gone, the strategy stops for review.

**Entry: the three-part test.**
1. Cheap: value well above price (sets the distance).
2. Catalyst or change agent visible (sets the timing).
3. The selling has exhausted itself: bad news no longer makes new lows, the stock holds or rises on a weak quarter, volume dries up on declines. This is the answer to the classic value trap of a cheap stock that keeps getting cheaper.

**Don't buy the day after bad news (Chan).** Drops on real news keep drifting the same way (post-earnings drift, now shorter); small no-news dips in a sound trend tend to bounce. Re-check the value, then buy later and calmer if it held up.

**Earnings surprises (Dreman, 1973-96).** Cheapest 20% by P/E: a good surprise brings a big, lasting gain (+8% vs market in a year, +35% over 5 years); a bad one barely matters. Most expensive 20%: a good surprise fades; a bad one brings a big, lasting loss (about −45% over 5 years).
- **Event trigger** (good news on a hated stock, or bad news on a favorite; can be an FDA ruling, lawsuit or product, not only earnings) changes perception for a long time: treat it as a catalyst. Surprises come in runs because analysts revise slowly.
- So Chan's drift is worst for favorites; bad news on an already-cheap holding is usually minor (re-check the thesis). When bad news knocks down a *good* company you want, **let the dust clear about a quarter**: it is usually cheaper within ~90 days.

Scale in on a plan decided in advance (for example a third now, a third after the next quarter confirms the thesis, a third on the first higher low). Keep a ranked watchlist with buy prices so you can act in panics and tax-loss season.

**Averaging down vs stop-losses (the knowledge base's working rule).** Klarman calls stop-losses "crazy" for value investors and wants room to average down; Livermore says never average a loss. Reconciled through Taleb's ruin logic:
1. Before buying, set a maximum position size and a portfolio-level drawdown at which overall risk is cut.
2. Add to a fallen holding only if the thesis is intact, the forensic check is clean, the business is robust (no accelerating harm from debt or operating leverage), the price has stabilised, and the add stays inside the size limit.
3. If losses are eating into the portfolio-level threshold, cut risk regardless of how cheap the stock looks.
Price falls are information about value; portfolio losses are information about survival.

**If a stop is used at all (Chan).** Stops fit momentum, not "buy what fell"; on a value position a stop is only disaster insurance, so set it **wider than the stock's worst past drop**, never tight. Stops don't protect against gaps (a flash-crash stop on Accenture filled at $0.01); size so a gap is survivable.

**Exit triggers (write them into the thesis on day one):**
1. **Value reached:** price at or near re-estimated intrinsic value. Sell or trim; trim rather than sell if value is compounding (a real franchise).
2. **Thesis broken:** the written break condition happened. Sell regardless of price; don't wait to get back to even.
3. **Forensic red flag:** auditor change, cash flow diverging from earnings, receivables ballooning. Treat as a thesis break.
4. **Cyclical peak signals:** new capacity announced, plants full, inventories building. Sell before earnings turn.
5. **Better horse:** a new idea with clearly more upside per unit of downside, which has passed the full process.
6. **No longer cheap (Dreman's Rule 21):** sell when P/E, P/CF and P/B are back near the market's, "regardless of how favorable prospects may appear", and buy another cheap stock. Needs no value estimate, so it cross-checks trigger 1. Use several ratios; ignore a P/E inflated by a temporary earnings dip; trim rather than sell a real compounder.
7. **Time stop, two steps:** at ~18 months with no catalyst and nothing improved, re-underwrite or trim; at 30-36 months (3.5 years for a cyclical in a dip), sell if it still hasn't worked. Dreman: cheap stocks keep winning 2-8 years and reratings are "slow, even glacial".
8. **Set the sell point on the day you buy.** Raising targets as the price rises leads to "the round trip". Sell at once if the long-term business really deteriorates (not one poor quarter). Switch rarely.
9. **Don't sell just because it went up.** Re-ask "would I buy it here, today, at this size?" If earnings and book grew too, the ratios may still be cheap. Lynch made most of his money in years three and four.
"All investments are for sale at the right price" (Klarman). "It is never wrong to change your mind. It is only wrong to change your mind and do nothing about it."

**Portfolio rules:**
- Circuit breaker: about 10% down from the account high, stop buying, review every thesis, cut the broken ones.
- In a losing streak, halve new position sizes until the process produces wins. Raise sizes only after the process has earned it.
- Hold cash when nothing passes the checklist. Cash is a position with zero opportunity-cost risk.
- Keep a written journal of every buy and sell with the reason; review losers in quiet periods.
- **Low turnover (Dreman).** 0.5% per trade at 100% turnover costs ~2.5% of capital in 5 years. "Buy and weed": replace only stocks that reached market ratios or hit the time stop.

**Panic playbook (Dreman).** (1) Buy in a panic, don't sell: after 11 postwar crises the Dow was up 25.8% a year after the low and 37.5% two years after. (2) Write down the reasons given for lower prices and check them; most fall apart. (3) **Value lifelines:** compare P/E, P/B and yield before, at and after the crisis (1990 banks: P/E 9.4 → 6.3, yield 4.1% → 8.8%); keep normal levels on the watchlist. (4) Financial strength first (banks: losses reserved, capital well above minimum, dividend kept). (5) Spread across the hated group (≤ 2% per name) and buy in tranches: "what looks dirt cheap can often drop another 20% or 30%."

**Hedging (for a value investor):**
- The main hedges are sizing, cash and buying cheap.
- Don't routinely buy puts on individual value names (skew makes them expensive). If you insure, do it cheaply at the portfolio level, occasionally.
- Covered calls on diamonds in the rough are usually a mistake: they cap the rerating and takeovers you are paying for, and are economically a short put.
- Selling cash-secured puts at a price you'd happily pay is the honest version: only on fully researched stocks, in sizes you'd want to own.
- Pair hedges (long cheap stock, short sector ETF or expensive peer) isolate the mispricing.
- LEAPS on a researched cheap stock can replace part of a stock position with capped loss (Greenblatt), but keep them small.
- Never hedge to avoid admitting a broken thesis. If it is broken, sell.

**Using options (Natenberg, *Option Volatility & Pricing*).** Options only help when their price is wrong; if your view is only direction, "stick to the underlying".
- **Let the option price pick the tool.** Compare implied volatility (IV) with the stock's recent realized volatility *and* its long-run normal (volatility keeps returning to its average; for long-dated options the long-run average is the best forecast). Wanting to own a researched cheap stock: IV expensive → sell a cash-secured put at the buy-below price; IV cheap → a small LEAPS; IV about fair → just buy the stock. On exit near value, sell a covered call at or above value only if calls are expensive; otherwise sell the stock. No clear view on the stock or the option price → do nothing.
- **LEAPS are a volatility bet too.** Largest vega: bought at high IV they can lose while the stock creeps up. Use the real T-bill rate. Long-dated and deep in-the-money options have the widest spreads ("married to the position"): check bid and ask, skip wide markets.
- **Early assignment.** An in-the-money covered call can be exercised the day before ex-dividend; a deep in-the-money short put can be assigned early (fine only if the cash is set aside). Test: "If I owned this option, would I exercise it now?"
- **No short at-the-money options in the last few days.** Gaps hurt short-dated options far more; close or roll near-the-money short options a few days before expiry.
- **Index options are usually overpriced** (IV above realized, downside puts priced highest): good for a SPY/QQQ put seller, but price and IV hit together in a fall, so size as if assigned. Buy index insurance only when IV is low.
- **Quick move check.** One standard-deviation move ≈ IV ÷ 16 per day, IV ÷ 7.2 per week ($50 stock, IV 32% → about $2.20 a week). Fat tails make this a minimum, not a safe distance.
- **Earnings.** IV rises into earnings and drops right after: selling just before means gap risk (only if glad to own after a bad report); buying short-dated options just before means overpaying.
- **Margin for error and staying power.** "A one-percentage-point margin for error is no margin for error at all": small edge, small size. How much you lose matters more than how often you win. Never "fix" a losing short option by selling more; keep cash to hold every position to expiry.

---

## 8. Risk philosophy (Taleb, Klarman, Soros)

- **Survival first.** "In a strategy that entails ruin, benefits never offset risks of ruin." Know your "uncle point" and stay well below it. One person over a hundred days is not a hundred people once (ensemble vs time probability).
- **Fat tails.** Markets live in Extremistan: a few days drive most returns, and the worst case is worse than history shows. Long calm is not safety (the turkey). Don't trust standard deviation, beta, Sharpe ratios or VaR as risk measures.
- **Fragility test.** If each extra unit of stress hurts more than the last (debt, operating leverage, refinancing walls, customer concentration), the business is fragile. Prefer robust businesses: low debt, redundancy (cash), many small customers, long survival (Lindy: a business that has sold the same thing profitably for decades will likely keep doing so).
- **Asymmetry and barbell.** Prefer bets that lose small and win big; avoid "picking up nickels in front of a steamroller" (selling naked tail risk, leverage, averaging down on margin). The barbell: most capital very safe, a small part in open-ended upside.
- **Expectation, not probability.** What matters is how much you make or lose when it happens, not how often you are right. Win rate is the least important statistic.
- **Noise.** Look at data and the portfolio rarely; daily moves are mostly noise. Only big changes deserve attention.
- **Luck vs skill and survivorship.** Judge decisions by the alternative histories, not the outcome. Great track records appear by chance in big populations.
- **Skin in the game.** Weight people who own what they recommend. Ignore forecasts and price targets from people with nothing at stake. Smooth, steady earnings can hide tail risk; ask what they are short.
- **Reflexivity (Soros).** Prices can change fundamentals when a company needs capital, refinancing or stock-funded acquisitions; credit booms are slow and busts sharp. Write a hypothesis, look for its flaw, and expect to correct it. Most of the time markets are near equilibrium and this is noise.

## 9. Psychology and discipline

- Temperament beats IQ. "The investor's chief problem, and even his worst enemy, is likely to be himself" (Graham).
- Cut losers that break the thesis; sit with winners. "It never was my thinking that made the big money for me. It always was my sitting" (Livermore).
- No tips. Do your own work; steal ideas from great investors' holdings but still do the homework.
- Market reaction to news is information: bad news that no longer pushes a stock down is a sign of strength; good news that fails to lift it is a warning.
- Danger follows big wins; overconfidence kills. Losing streaks call for smaller size, not catch-up bets. You can't win if you have to win.
- Never buy right after a big rise or sell right after a big drop (Graham). When a holding falls: what changed besides the price? Divide your cost by ten: would you still hold? If the facts changed, sell; if not, consider buying more within limits.
- The method must fit the person; breaking discipline once makes it easier the next time.
- Be patient: value investing means being lonely, early and sometimes lagging in bull markets. There are no called strikes; wait for the fat pitch.
- **Most quit right before it works (Dreman).** Value lagged for years after 1988 and investors gave up at the bottom, just before it won for years: "virtually every time". Cheap stocks beat the market only ~60/40 per quarter but in 87-94% of 5- and 10-year periods.
- **Confident voices pull your opinion unnoticed** (one confident person shifted others' estimates up to 80%). Write your own estimate before reading opinions. Manias repeat: easy-wealth image, expert cheerleaders, panic, "this time is different". Overreaction is predictable; its timing is not.

---

## 10. Where the books disagree, and the reconciliation

| Question | Camp A | Camp B | Working rule here |
|---|---|---|---|
| Stop-loss or average down? | Klarman, Lynch: average down, no stops | Livermore, Wizards: cut losses, never average down | §7 working rule: thesis + size limit + portfolio drawdown cap; Chan: any stop on a value position only beyond the worst past drop |
| Buy cheap or buy strength? | Graham, Klarman: buy cheap | O'Neil, Livermore: buy new highs | Select on cheapness; time with "selling exhausted" and stabilising price |
| How diversified? | Graham 10-30, net-nets 30-100; Dreman 20-30 equal-weight | Greenblatt 6-8; Klarman 10-15 | 10-15 researched picks; 20-30 equal-weight for mechanical cheap-stock baskets |
| When to sell a winner? | Dreman: ratios near the market's | Lynch, Klarman: not just because it rose | Value reached or market-level ratios (several ratios); trim a real compounder |
| How long to wait? | Catalyst view: ~18 months | Dreman 2.5-3 yrs; Templeton 6 | Review at 18 months, sell at 30-36 if still not working |
| Bad news? | Chan: drops keep drifting | Dreman: barely hurts cheap stocks, crushes favorites | Re-check value; wait ~a quarter before buying a good company just knocked down |
| Forecast or not? | Graham, Greenwald: value from the record | Soros: dynamic hypotheses about others' beliefs | Value from the record; use reflexivity only for financing-dependent situations |
| Options? | Lynch: avoid; Natenberg: use the stock if your view is only direction | Greenblatt: LEAPS/warrants on researched ideas | Fully researched names only, never short-dated speculation; IV picks the tool (§7): rich → cash-secured put at buy-below, cheap → small LEAPS, fair → stock |

## 11. Output templates

**Stock analysis (when Chris names a ticker).** Pull live data first and label it. Then:
1. **Verdict up front:** BUY / WATCH / AVOID, with intrinsic value range, buy-below price (about a third under the conservative value) and current margin of safety.
2. **Category and story** in two minutes (Lynch category, why it is cheap, who is selling). Cheapness vs market and industry; surprise tag (Dreman).
3. **Forensic check:** pass, caution or fail, with the specific flags from §4 and the numbers behind them.
4. **Valuation:** at least two methods (for example EPV and asset value, Graham screens, PEG), normalised inputs shown, low end used.
5. **Balance sheet and fragility:** net cash or debt, maturities, current ratio, interest cover, pension and lease obligations.
6. **Insiders and ownership:** insider buying or selling, buybacks vs dilution, institutional and analyst coverage.
7. **Catalyst and timing:** what unlocks value and when; is the selling exhausted?
8. **Risks and thesis-break condition.**
9. **Sizing and plan:** dollars at risk vs account, tranches, exit triggers incl. ratio sell point, 18-month review, 30-36-month time stop.
10. **Confidence and gaps:** what was live, what was estimated, what to check next.

**Building tools (scanners, scorers, dashboards, bots).**
- Encode the process order: forensic flags gate the valuation; valuation sets buy-below; sizing comes from downside, not upside.
- Useful fields: verdict, intrinsicValue (low/base), buyBelow, marginOfSafety %, category (Lynch), forensic score with named flags, EPV, asset/NCAV value, Graham defensive and enterprising pass/fail per test, P/E × P/B, PEG, net cash per share, insider buying (90 days), active institutional %, analyst count, catalyst, thesisBreak, exit triggers (value reached, no longer cheap vs market, thesis broken, forensic flag, 18-month review and 30-36-month time stop), max position %, dollars at risk. Dreman: ratios vs S&P 500 (≥ 20% cheaper on one, or yield ≥ 1 pt higher), rank within industry, dividend held/raised/cut, surprise tag (event trigger / reinforcing / warning).
- Treat recurring "one-time" charges and stock comp as costs. Use ending balances for DSO. Use multi-year averages, not one year.
- **Keep scoring simple (Chan, Kahneman).** Combine factors with equal weights or a plain rank sum (rank on each factor, flip the sign where lower is better, add up). Greenblatt's two-factor magic formula is the model. Finely tuned weights mostly fit past noise; if a weight tweak makes history look better, suspect overfitting.
- **Testing a screen or bot honestly (Chan).** Include delisted and bankrupt companies (without them "buy the beaten-down" screens look far too good), use only information available at the time, adjust for splits and dividends, include costs, keep rules few, don't re-tune after seeing results, compare with an index. Paper-trade forward and expect live results about **half as good** as the back-test. Write down why it should work and when it gets switched off.
- **Option tools (Natenberg).** Show IV next to 20/60-day realized and 1-year (long-run) volatility with a plain "expensive / fair / cheap → sell a put / buy the stock / LEAPS" line; ask for bid and ask, not one price, and warn on wide spreads; for LEAPS show the dollar loss if IV drops 5 points and use the real T-bill rate; warn on covered calls that are in the money with an ex-dividend date before expiry; label model probabilities "assumes no gaps".
- Show the data source and timestamp next to every number, and mark estimated values.
- Never let a tool place real trades or move money without the user's explicit confirmation.

## 12. Which book answers which question (reference files)

| Question | Book (file in `references/`) |
|---|---|
| Are the numbers real? Accounting tricks, forensic checklist | Financial Shenanigans, Schilit (`financial-shenanigans.md`, §4) |
| Graham screens, net-nets, margin of safety, defensive vs enterprising | The Intelligent Investor, 2024 ed. (`the-intelligent-investor.md`, §3) |
| Valuation: asset value, EPV, franchise, growth | Value Investing, Greenwald (`value-investing-greenwald.md`, §3) |
| Risk-averse value philosophy, why things are cheap, selling, catalysts | Margin of Safety, Klarman (`margin-of-safety.md`, §3) |
| Finding overlooked stocks, six categories, two-minute story | One Up On Wall Street, Lynch (`one-up-on-wall-street.md`, §3) |
| Special situations: spinoffs, merger securities, post-bankruptcy, LEAPS | You Can Be a Stock Market Genius, Greenblatt (`you-can-be-a-stock-market-genius.md`, §4) |
| Position risk, entries, exits, hedging, pre-trade checklist | The New Market Wizards, Schwager (`the-new-market-wizards.md`, §3 and §11) |
| Trader discipline, cutting losses, risk per trade | Market Wizards, Schwager (`market-wizards.md`) |
| Speculation, tape, sitting tight, psychology | Reminiscences of a Stock Operator, Lefèvre/Livermore (`reminiscences-of-a-stock-operator.md`) |
| Reflexivity, boom/bust, credit cycles | The Alchemy of Finance, Soros (`the-alchemy-of-finance.md`) |
| Luck vs skill, survivorship, noise | Fooled by Randomness, Taleb (`fooled-by-randomness.md`) |
| Fat tails, prediction limits, barbell | The Black Swan, Taleb (`the-black-swan.md`) |
| Fragility, optionality, via negativa, Lindy | Antifragile, Taleb (`antifragile.md`) |
| Incentives, insiders, ruin, stop-loss vs averaging down rule | Skin in the Game, Taleb (`skin-in-the-game.md`, §9) |
| Aphorisms on noise, robustness, advice-givers | The Bed of Procrustes, Taleb (`bed-of-procrustes.md`) |
| Forced-selling bargains, news drift, stops on value positions, Kelly/half-Kelly, risk budget (CPPI), testing screens and bots, simple scoring | Algorithmic Trading, Chan (`algorithmic-trading-chan.md`, §3 and §9 checklist) |
| Low-ratio evidence, industry-relative cheapness, surprises (event triggers), forecast error, sell when no longer cheap, time stop, panic playbook, small caps and spreads, 41 rules | Contrarian Investment Strategies, Dreman (`contrarian-investment-strategies.md`, §3, §4 screens and §10 checklist) |
| Options: implied vs realized volatility, which tool (stock / cash-secured put / LEAPS), greeks, LEAPS vega and liquidity, early assignment, gap risk near expiry, index skew, earnings IV | Option Volatility & Pricing, Natenberg (`option-volatility-and-pricing.md`, §3 and §9 option-ticket checklist) |

Each reference file follows the same layout: context, core ideas on one page, rulebook by theme, chapter notes, case or story index, traps or mistakes, quotes, people, applying it today for Chris, limits and critiques, cross-reference hooks, glossary, source note.

## 13. Limits

- The books are mostly from 1923-2013 (Intelligent Investor commentary updated 2024). Dreman's data end in 1996-97; since then value lagged growth for much of 2007-2020, a longer drought than any he tested [outside the books]. Dollar thresholds, P/E norms and bond yields must be translated to today's rates; compare with the company's own history and peers rather than fixed numbers.
- Accounting has changed: goodwill is impairment-tested not amortised, leases are on the balance sheet (count them as debt-like), revenue follows ASC 606, and non-GAAP metrics are everywhere.
- Mechanical screens decay once widely followed. Net-nets are now rare and often cash-burning.
- Rules marked as adaptations in the reference files (sizing formula, tranche splits, liquidity rule of thumb, cash-secured puts, the retail version of Chan's forced-selling signals, the half-Kelly worked example, Natenberg's IV rules translated into the stock / cash-secured put / LEAPS choice, the two-step 18-month / 30-36-month time stop combining the catalyst check with Dreman's) are this knowledge base's syntheses, not the authors' words.
- This skill cannot see the market. Every live number must come from a data tool, with its source stated.
