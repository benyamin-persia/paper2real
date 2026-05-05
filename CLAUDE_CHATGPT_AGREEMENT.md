# Paper2Real Agreement Between Claude And ChatGPT

Last verified from the codebase: 2026-05-05

For operational handoff, deployment, current API cost, Twitter account rationale,
and provider-switch instructions, read `PROJECT_RUNBOOK.md` first.

This file is the shared agreement for future conversations with Claude or
ChatGPT. Treat it as the current source of truth when discussing the trading
system. If another document disagrees with this file, verify the code before
trusting the older document.

## Core Goal

Build a Bitcoin paper-trading intelligence system.

The system should combine:

- Live BTC price and 15-minute indicators.
- Historical pattern matching from the master dataset.
- Daily market context from derivatives, macro, market structure, and halving cycle.
- Critical override alerts for hacks, bans, exchange failures, and stablecoin depegs.
- Claude as an analyst only.
- `risk_engine.py` as the deterministic final authority.

Claude advises. The risk engine decides. The trader executes.

## Non-Negotiable Rules

- Default action is HOLD.
- A missed trade is acceptable. A bad trade is not.
- Critical bearish events block trading regardless of technicals.
- Stablecoin depeg blocks trading regardless of technicals.
- Stale or missing critical-event data blocks new BUYs.
- Claude must never execute a trade directly.
- Claude output must pass through `risk_engine.evaluate()`.
- No single indicator is allowed to force a trade alone.
- Technicals support decisions; they do not override risk.
- More data is useful only if it improves safety or decision quality.
- Do not add noisy sentiment sources before logging, backtesting, and risk controls are solid.
- Data collection should use Playwright/browser sessions where possible. Direct Python data calls in live trading are technical debt and should be replaced or explicitly accepted case by case.

## Data Collection Rule

The user preference is: no paid data APIs and no fragile direct data API dependency.
The only paid/official API that is accepted as core infrastructure is the AI API.

Current practical agreement:

- Preferred method: Playwright loads the public site, then `page.evaluate(fetch(...))` runs inside the browser session.
- Acceptable for existing collectors: public endpoints fetched from inside Playwright/browser context.
- Technical debt: `main.py` still uses direct `httpx` calls for Yahoo/Coinbase/Fear & Greed/stablecoin live checks.
- Future work should move live data fetching toward the Playwright/browser pattern unless there is a clear speed or safety reason not to.

This rule is about reliability and access. It does not mean every useful public JSON endpoint is forbidden. It means the project should not depend on paid data APIs or direct Python API calls when a browser scrape is the safer path.

## Current Implemented Status

### Built And Wired

- BTC live 15-minute candles in `main.py`.
- Live indicators: RSI, MACD, EMA20/50/200, Bollinger Bands, ATR, Stoch, volume ratio.
- Fear and Greed current value.
- Historical dataset: `data/processed/master_dataset.csv`.
- Pattern matcher: `data/processor/matcher.py`.
- CoinGlass derivatives history: funding, liquidations, open interest, long/short ratio, ETF flow.
- CoinGecko market structure: dominance, market cap, USDT market cap, altcoin season fallback.
- Macro context: S&P 500, DXY, VIX, gold.
- On-chain context: hash rate, total BTC supply, transaction volume.
- CryptoPanic critical-event scraper: `data/collector/events.py`.
- `data/raw/events.json` cache.
- Background CryptoPanic refresh loop every 15 minutes when FastAPI is running.
- Stablecoin depeg live check for USDT and USDC in `main.py`.
- Halving cycle calculation in `main.py` with no scraper required.
- Daily context loader in `main.py` reads existing CSVs every scan.
- Claude prompt in `brain.py` includes live technicals, daily context, alert status, and halving cycle.
- Risk engine has 13 checks, including monthly loss limit and stale events blocking new BUYs.
- Decision logging is stored in SQLite `decisions` table.
- `/decisions` endpoint summarizes Claude actions, final actions, executions, and risk blocks.
- Decision logs include trigger source: `scheduled`, `manual`, `webhook`, or `event_price_move`.
- Event-driven scan loop exists in `main.py`: 2 percent BTC move in about 30 minutes, max 3 per day, 30 minute cooldown.
- Backtest engine exists in `backtest.py`.
- Latest backtest reports are saved under `data/reports/`.
- `main.py` caches latest live candles to `data/raw/live_btc_15m.csv` for future decision evaluation.
- Clean live X account list in `data/raw/account_tiers.json`.

### Not Built Yet

- ~~Tier 1 X/Twitter crawler wiring into `brain.py`.~~ DONE — `_get_twitter_context()` in `main.py` reads `twitter_playwright.json`; `_twitter_refresh_loop()` scrapes Tier 1 every 30 min; `brain.py` shows alerts + context to Claude.
- ~~Twitter Tier 1 live alert ingestion.~~ DONE — see above.
- `daily_context.json` file. Current daily context is loaded directly from CSVs, not saved as JSON.
- Options max pain / put-call ratio.
- Reddit sentiment.
- Google Trends.
- Whale movement tracker.
- Exchange reserves.
- Miner revenue / Puell Multiple.
- AI decision feedback loop exists in `decision_evaluator.py`; it scores Claude/final actions once enough future price data exists and writes reports under `data/reports/`.
- Current blocker: `paper_trader.db` has no decisions yet, so the evaluator is built but needs live paper scans before it can produce useful learning.

### Deployment Agreement

- A VPS is the preferred always-on host.
- TrueNAS is acceptable if Paper2Real runs inside an Ubuntu VM, not directly on the TrueNAS host shell.
- Minimum live-trader VPS: 2 vCPU, 4 GB RAM, 30 GB SSD.
- Preferred full-scraping VPS: 4 vCPU, 8 GB RAM, 50+ GB SSD.
- The live app should run continuously under `systemd`.
- Heavy jobs (`collect.py`, full 84-account X/Twitter scrape, large backtests) should run as scheduled jobs, not inside every trade scan.
- Deployment files exist under `deploy/`, including TrueNAS VM notes and systemd units.
- Real-money execution remains blocked until the system has profitable backtest evidence plus at least 30 days of positive paper trading.

### Already Enough For Testing

The project already has enough historical and contextual data to begin testing the trading logic. Do not block progress by adding more random data sources.

Current useful data:

- BTC candles and indicators.
- Fear and Greed.
- CoinGlass derivatives and ETF flow.
- CoinGecko market structure.
- Macro context.
- On-chain context.
- Critical events.
- Stablecoin depeg check.
- Halving cycle.

The current missing foundation is not "more indicators." The missing foundation is auditability and proof:

- Strategy profitability after fees and slippage.

## Current Verified Gaps

### 1. ~~Freshness Gate Is Not Shared Everywhere~~ — FIXED
`events_unavailable` is now set inside `get_market_context()` itself, so all three paths (`_run_scan`, `/scan`, `/webhook`) receive the same flag before `risk_engine.evaluate()` runs.

### 2. ~~Daily Context Can Return Null Latest Values~~ — FIXED
`_load_daily_context()` now uses `_latest(df, col)` which does `df.sort_values("date")[col].dropna().iloc[-1]` per field. Each column independently finds its own last non-null value. Sparse last rows no longer mask older good data.

### 3. Events Cache Only Stays Fresh While Server Runs

`data/raw/events.json` is refreshed every 15 minutes only when FastAPI is running.

Agreement:

- If the server is not running, `events.json` can become stale.
- Stale events block new BUYs (risk engine check #7).
- Before paper-trading live, ensure the server lifespan background task is running.

## Signal Layer Agreement

### Layer A: Critical Overrides

These can block trades.

- Exchange hack.
- Exchange collapse.
- Government ban.
- SEC/CFTC/DOJ emergency enforcement action.
- Stablecoin depeg.
- Stale or missing critical-event feed.
- Portfolio max drawdown.
- Consecutive-loss limit.
- Daily loss limit.
- Monthly loss limit for new BUYs.
- FOMC/CPI event day with insufficient confidence.

Layer A signals do not need to be bullish. Their main job is to prevent bad trades.

### Layer B: High-Impact Context

These adjust confidence and risk.

- ETF flows.
- Funding rate.
- Open interest.
- Long/short ratio.
- Liquidations.
- BTC dominance.
- USDT market cap.
- Altcoin season index.
- S&P 500.
- DXY.
- VIX.
- Gold.
- Halving cycle percentage.

Layer B should not force trades alone.

### Layer C: Live Technicals

These help timing.

- RSI.
- MACD.
- EMA trend.
- Bollinger Bands.
- ATR.
- Stoch.
- Volume ratio.

Layer C is useful but must never override Layer A.

### Layer D: Sentiment And Social

Current status:

- X account list exists.
- CSV crawler prototype exists in `data/collector/twitter_playwright.py`.
- Puppeteer CSV crawler exists in `data/collector/twitter_puppeteer.js`.
- Tier 1 crawler is wired into `main.py` and `brain.py`: background refresh every 30 minutes, latest tweets/alerts passed into Claude context.
- Full 84-account scraping remains offline/daily research only, not part of every trade scan.

Future rule:

- Tier 1 tweets can become alerts.
- Tier 2 and Tier 3 tweets are context.
- Influencer sentiment should not become an automatic trade trigger.

## Resource Priority Agreement

This section answers: which resources matter now, which matter later, and which should not distract the project.

### Critical Now

These resources directly affect whether the bot is safe or dangerous.

1. BTC live price and 15-minute candles.
   - Purpose: every scan depends on current price and indicators.
   - Failure behavior: if BTC price/candles are missing or stale, skip the scan.
   - Current code: `main.py` uses Yahoo Finance 15-minute candles with Coinbase fallback.

2. `risk_engine.py`.
   - Purpose: deterministic veto layer after Claude.
   - Why critical: Claude can be wrong or overconfident; the risk engine protects capital.
   - Current status: built with 13 checks.

3. Decision logs.
   - Purpose: prove what Claude wanted, what the risk engine allowed/blocked, and why.
   - Why critical: without logs, there is no way to diagnose overtrading, excessive blocking, or bad signals.
   - Current status: SQLite `decisions` table and `/decisions` endpoint.

4. Backtest engine.
   - Purpose: test strategy changes before live paper trading or real money.
   - Why critical: no strategy change should be trusted without replaying it through fees, slippage, stops, and risk limits.
   - Current status: `backtest.py` exists and writes reports to `data/reports/`.

5. Critical events.
   - Purpose: block or reduce risk during hacks, collapses, bans, enforcement shocks, and stablecoin depegs.
   - Why critical: these can invalidate technical signals immediately.
   - Current status: CryptoPanic events scraper plus stablecoin depeg check.

6. Tier 1 latest X/Twitter posts.
   - Purpose: catch high-impact public statements from institutions, regulators, exchanges, security accounts, and major Bitcoin actors.
   - Why critical: these are alert/context signals, not automatic trade triggers.
   - Current status: Tier 1 crawler is wired into `main.py` and `brain.py`; full 84-account scans remain offline/daily only.

Critical Tier 1 categories:

- President / White House.
- Federal Reserve.
- SEC / CFTC / Treasury / DOJ.
- Major exchanges: Binance and Coinbase.
- ETF/institutional accounts: BlackRock, iShares, Fidelity, Grayscale.
- MicroStrategy and Saylor.
- Tether and Paolo Ardoino.
- Security alerts: ZachXBT, PeckShield, SlowMist, CertiK.
- WuBlockchain.

### Critical For Strategy Quality

These resources help decide whether a BUY signal is good. Most already exist. The current task is to use them better, not blindly add more data.

- Funding rate.
- Open interest.
- Long/short ratio.
- Liquidations.
- ETF flows.
- BTC dominance.
- USDT market cap.
- S&P 500.
- DXY.
- VIX.
- Gold.
- Fear and Greed.
- ATR, RSI, MACD, EMA, Bollinger Bands, and volume.

Agreement:

- These resources should adjust confidence and filter weak entries.
- They should not force BUY alone.
- Strategy changes must be measured by `backtest.py`.

### Critical For Future

These become important after the base strategy is profitable or after Tier 1 social alerts are wired cleanly.

1. Options max pain and put/call ratio.
   - Best use: context near options expiry.
   - Priority: medium.

2. Exchange reserves.
   - Best use: BTC leaving exchanges is bullish context; BTC entering exchanges is sell-pressure context.
   - Priority: medium if a stable source exists.

3. Tier 2 and Tier 3 X/Twitter sentiment.
   - Best use: daily/weekly context, not live trade trigger.
   - Priority: later, after Tier 1 works.

4. AI decision feedback loop.
   - Best use: learn from Claude's own BUY/SELL/HOLD decisions, including blocked trades and missed moves.
   - Current status: built in `decision_evaluator.py`; needs live decision history before it becomes useful.

5. Dashboard for decision logs.
   - Best use: monitor blocks, Claude bias, execution rate, and PnL.
   - Priority: useful for long-running paper trading.

6. Weekly data refresh scheduler.
   - Best use: hands-off refresh of `collect.py`.
   - Priority: operations, not strategy.

### Not Critical Now

Skip these until the current strategy has positive expectancy or there is a specific measured reason to add them.

- Reddit sentiment.
- Google Trends.
- Whale movement tracker.
- More technical indicators.
- Full 84-account live X/Twitter scan before every trade.
- Random influencer sentiment.

Reason:

- These sources are noisy, delayed, manipulated, slow, or easy to overfit.
- Adding them now can hide weak strategy logic.
- The immediate problem is BUY quality, not lack of raw data.

### Highest Priority Resource Stack

If the system had to be reduced to essentials, keep these:

- BTC candles.
- Risk engine.
- Decision logs.
- Backtest.
- Critical events.
- Stablecoin depeg.
- Funding, open interest, and liquidations.
- ETF flows.
- Macro: DXY, VIX, S&P 500.
- Tier 1 latest X/Twitter posts.

Everything else is secondary until the backtest improves.

## Risk Engine Agreement

`risk_engine.py` is the final authority.

Current checks:

1. Max drawdown.
2. Consecutive losses.
3. Daily loss limit.
4. Monthly loss limit blocks new BUYs.
5. Stablecoin depeg.
6. Exchange alert.
7. Events unavailable blocks BUY.
8. Claude confidence below 60.
9. Max open trades.
10. Missing ATR.
11. Bollinger Band squeeze.
12. FOMC/CPI event day with confidence below 80.
13. Insufficient cash.

Risk-based sizing:

- Max risk per trade: 1 percent of account.
- Stop uses ATR.
- Position size is capped at 30 percent of cash balance.

## Halving Cycle Agreement

The halving cycle is a useful context signal.

Current code calculates:

- Days since last halving.
- Days to next halving.
- Halving cycle percentage.

Use:

- 20-60 percent cycle progress: generally accumulation-friendly context.
- Above 80 percent cycle progress: late-cycle risk increases.

Do not use:

- Halving cycle alone as a BUY or SELL trigger.

## Historical Matching Agreement

The matcher provides evidence, not truth.

Known limitation:

- Historical dataset is daily.
- Live scan uses 15-minute indicators.
- This is useful as broad context but not perfect statistical matching.

Agreement:

- Do not overstate the historical matcher.
- Use it as one input among risk, macro, derivatives, alerts, and technicals.
- The backtest engine exists, but the latest result is not profitable yet.
- A profitable backtest plus at least 30 days of paper trading is still required before real money.

## Latest Backtest Agreement

Latest run: 2026-05-01.

Files:

- `backtest.py`
- `data/reports/backtest_latest.json`
- `data/reports/backtest_trades.csv`
- `data/reports/backtest_equity.csv`

Result:

- Period: 2024-11-15 to 2026-04-30.
- Rows replayed: 531.
- Final equity: $9,909.28.
- Return: -0.91 percent.
- Buy and hold return over the same period: -17.18 percent.
- Max drawdown: 3.35 percent.
- Closed trades: 10.
- Win rate: 40.0 percent.
- Average trade: -$9.07.
- Worst trade: -$76.69.
- HOLD ratio: 98.12 percent.

Interpretation:

- The strategy avoided most of the buy-and-hold drawdown in this period.
- It still lost money after fees and slippage.
- It is not ready for real money.
- The largest blocker is consecutive-loss protection: after four losses, 46 later BUY signals were blocked.
- Disabling the consecutive-loss brake made performance worse (-2.07 percent return, 7.66 percent max drawdown, 28.57 percent win rate), so the safety brake is not the main problem.
- The next strategy work should improve BUY quality, not weaken risk controls.

## Next Build Order

Do these before adding random new sentiment sources:

1. ~~Make the freshness gate shared across auto-scan, `/scan`, and `/webhook`.~~ DONE
2. ~~Fix `_load_daily_context()` to use latest non-null value per field.~~ DONE
3. ~~Add monthly loss limiter.~~ DONE
4. ~~Add decision audit logging for every scan.~~ DONE
5. ~~Build proper backtest engine.~~ DONE
6. ~~Add event-driven scan trigger for large BTC moves.~~ DONE
7. Improve strategy profitability before real money.
8. ~~Finish Tier 1 X/Twitter crawler reliability and wire into context.~~ DONE — background loop every 30 min, alerts and context fed to Claude.
9. Add options max pain and put-call ratio.
10. Add exchange reserves if a stable Playwright source is found.
11. ~~Build AI decision feedback evaluator.~~ DONE — `decision_evaluator.py` writes JSON/CSV/MD reports and `brain.py` reads the latest summary.
12. Collect enough live paper decisions for the evaluator to become useful.

## Explicit Skip For Now

These are not priorities until the checklist above is done:

- Full 84-account Twitter sentiment.
- Reddit sentiment.
- Google Trends.
- Whale movement tracker.
- More technical indicators.
- Random influencer sentiment.

Reason: they are noisy or hard to scrape cleanly. They can make the system look more intelligent while making the trade logic harder to test.

## Instruction For Claude

When Claude reads this file, it should:

- Not assume missing scrapers exist.
- Not suggest adding more data before fixing the verified gaps above.
- Treat risk-engine safety as more important than signal generation.
- Remember that the project is still paper trading.
- Prefer robust, auditable rules over clever but fragile model behavior.
- Be explicit when a claim is based on code versus an assumption.

The correct current estimate is:

```text
Core data foundation:         strong
Critical safety layer:        built and wired (all paths)
Daily context layer:          built, latest-non-null fix applied
Freshness gate:               built, shared across all scan paths
Decision logging layer:       built, stored in SQLite
Backtesting layer:            built, latest result not profitable
Event-driven scan layer:      built
Twitter/social live layer:    built — background loop every 30 min, alerts + context wired into Claude
Overall implementation vs agreement: about 97 percent
```
