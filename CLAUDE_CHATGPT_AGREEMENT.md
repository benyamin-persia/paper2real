# Paper2Real Agreement Between Claude And ChatGPT

Last verified from the codebase: 2026-05-01 (session 6)

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
- Clean live X account list in `data/raw/account_tiers.json`.

### Not Built Yet

- Twitter/Nitter scraper.
- Twitter Tier 1 live alert ingestion.
- `daily_context.json` file. Current daily context is loaded directly from CSVs, not saved as JSON.
- Options max pain / put-call ratio.
- Reddit sentiment.
- Google Trends.
- Whale movement tracker.
- Exchange reserves.
- Miner revenue / Puell Multiple.
- Trade feedback loop where Claude learns from our own closed trades.

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
- Twitter/Nitter scraper is not built.

Future rule:

- Tier 1 tweets can become alerts.
- Tier 2 and Tier 3 tweets are context.
- Influencer sentiment should not become an automatic trade trigger.

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
8. Build Tier 1 Twitter/Nitter scraper only.
9. Add options max pain and put-call ratio.
10. Add exchange reserves if a stable Playwright source is found.
11. Add trade feedback loop after enough paper trades exist.

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
Twitter/social live layer:    not built
Overall implementation vs agreement: about 94 percent
```
