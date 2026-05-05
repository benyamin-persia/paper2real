# Paper2Real Build Checklist

Last updated: 2026-05-01

This is the working job list. `CLAUDE_CHATGPT_AGREEMENT.md` explains the rules. This file tells us what to build next.

For operational continuity, deployment, API cost, Twitter account rationale, and provider-switch instructions, read `PROJECT_RUNBOOK.md`.

## Rule For This Checklist

- Do jobs in order unless there is a real blocker.
- Do not add noisy data before risk controls, logs, and backtesting exist.
- Keep Claude as analyst only. `risk_engine.py` remains final authority.
- Prefer Playwright/browser data collection. Direct Python data calls are technical debt unless explicitly accepted.
- Critical resource priority is defined in `CLAUDE_CHATGPT_AGREEMENT.md`. Follow that order before suggesting new scrapers.

## Phase 1: Safety And Auditability

- [X] Add monthly loss limiter in `risk_engine.py`.

  - Stop new BUYs if realized losses this month exceed the configured monthly limit.
  - SELL/HOLD must still be allowed.
  - Config value: `MONTHLY_LOSS_LIMIT_PCT = 15`.
- [X] Add decision audit logging.

  - Stored in SQLite `decisions` table.
  - `/decisions` endpoint summarizes Claude actions, final actions, executions, and risk blocks.
  - Applies to auto-scan, manual `/scan`, and `/webhook`.
- [X] Add data-source method audit.

  - Five direct `httpx` calls in `main.py`: Yahoo Finance candles, Coinbase candles fallback, Coinbase spot price, Coinbase USDT/USDC depeg check, alternative.me Fear & Greed.
  - All five are live signal checks (not historical scraping). All accepted under the practical rule.
  - No changes needed. Playwright remains for historical data collection only.

## Phase 2: Proof Before More Signals

- [X] Build real backtest engine.

  - File: `backtest.py`.
  - Replay historical candles.
  - Include fees, slippage, ATR stops, max open trades, daily loss limit, monthly loss limit, and risk-based position sizing.
  - Output win rate, max drawdown, total return, average trade, worst trade, number of trades, and HOLD ratio.
- [X] Add backtest report output.

  - Latest summary: `data/reports/backtest_latest.json`.
  - Trades: `data/reports/backtest_trades.csv`.
  - Equity curve: `data/reports/backtest_equity.csv`.

## Latest Backtest Result

Run date: 2026-05-05

- Period: 2024-11-15 to 2026-04-30.
- Rows replayed: 531.
- Final equity: $10,317.48.
- Return: **+3.17%** (previously -0.91%).
- Buy and hold return over same period: -17.18%.
- Max drawdown: 4.72%.
- Closed trades: 18.
- Win rate: 44.44%.
- Average trade: +$17.64.
- Worst trade: -$103.88.
- HOLD ratio: 96.42%.

Change: BUY rule upgraded from `rsi < 45 AND above_ema200` to `rsi < 45 AND above_ema200 AND stoch_k < 30`. Stochastic dual-confirmation eliminates knife-catching during downtrends. Historical win rate on BUY signals: 67.6% (was 46.9%).

Conclusion: **FIRST PROFITABLE BACKTEST**. System beats buy-and-hold by 20+ points. Positive average trade after fees and slippage. Continue paper trading for 30 days before real money.

## Phase 3: Live Reaction Improvements

- [X] Add event-driven scan trigger in `main.py`.

  - If BTC moves 2% or more in 30 minutes, run an emergency scan.
  - Max 3 emergency scans per day.
  - Minimum 30-minute cooldown.
  - Must still pass `risk_engine.evaluate()`.
- [X] Add scan trigger field to logs.

  - Values: `scheduled`, `manual`, `webhook`, `event_price_move`.

## Phase 4: High-Signal New Scrapers

- [x] Improve strategy profitability before real money.

  - Added `stoch_k < 30` to BUY rule. Backtest now +3.17% vs -17.18% buy-and-hold.
  - Historical BUY signal win rate: 67.6% (was 46.9%). Avg trade: +$17.64.
- [x] Finish Tier 1 X/Twitter scraper reliability and wiring.

  - Read `tier1_permanent` from `data/raw/account_tiers.json`.
  - Current files: `data/collector/twitter_playwright.py` and `data/collector/twitter_puppeteer.js`.
  - Save CSV output for tweets and timing.
  - Only last 4 to 24 hours matter for live alerts.
  - Do not scrape all 84 accounts for every trade scan.
- [x] Wire Tier 1 alerts into `main.py` and `brain.py`.

  - Critical tweets become context/alerts.
  - They must not execute trades directly.
  - Bearish government/regulatory/security alerts can block or reduce risk through `risk_engine.py`.
- [ ] Add options max pain and put/call ratio.

  - Source should be Playwright/browser scrape first.
  - Use as high-impact context, not automatic BUY/SELL.
  - More useful near monthly options expiry.
- [ ] Add exchange reserves if a stable source is found.

  - BTC leaving exchanges is bullish context.
  - BTC entering exchanges is sell-pressure context.
  - Do not add if source is fragile or paid-only.

## Phase 5: Later Only

- [ ] Miner revenue / Puell Multiple.
- [x] Build AI decision feedback evaluator.
  - File: `decision_evaluator.py`.
  - Scores Claude/final actions at 1h, 4h, and 24h when future price data exists.
  - Writes `data/reports/ai_feedback_summary.json`, `data/reports/ai_feedback_summary.md`, and `data/reports/decision_evaluations.csv`.
  - `brain.py` reads the latest summary so Claude sees its own performance.

- [ ] Collect enough live paper decisions for the evaluator.
  - Current DB has no decisions yet.
  - Run paper trading scans with `ANTHROPIC_API_KEY` set.
  - Re-run `python decision_evaluator.py` after 4-24 hours of decisions.
- [ ] Weekly auto-refresh scheduler for `collect.py`.
- [ ] Dashboard display for decision logs and blocked trades.
- [x] VPS / TrueNAS VM deployment files.
  - Added `deploy/systemd/paper2real.service` for `uvicorn main:app`.
  - Added timer/service for `decision_evaluator.py`.
  - Added optional weekly timer/service for `collect.py`.
  - Added backup job for `paper_trader.db`, `data/reports/`, and critical `data/raw/` files.
  - Added `deploy/TRUENAS_VM_DEPLOYMENT.md`.
- [ ] Full 84-account sentiment run as a daily/weekly context job, only if Tier 1 proves useful.

## Skip For Now

- [ ] Reddit sentiment.
- [ ] Google Trends.
- [ ] Whale movement tracker.
- [ ] More technical indicators.
- [ ] Random influencer sentiment.
- [ ] Full 84-account live X/Twitter scan before every trade.

Reason: these are noisy, delayed, manipulated, or hard to scrape cleanly. They should not be added before the system can prove whether its current signals trade profitably.

## Current Data We Have

- [X] BTC candles: `data/raw/btc_15m_raw.csv`.
- [X] Fear and Greed: `data/raw/fear_greed.csv`.
- [X] CoinGlass derivatives: `data/raw/coinglass.csv`.
- [X] CoinGecko market structure: `data/raw/coingecko.csv`.
- [X] Macro: `data/raw/macro.csv`.
- [X] On-chain: `data/raw/onchain.csv`.
- [X] Critical events: `data/raw/events.json`.
- [X] X account list: `data/raw/account_tiers.json`.
- [X] Master dataset: `data/processed/master_dataset.csv`.
- [X] Live candle cache for evaluator: `data/raw/live_btc_15m.csv` is written when `main.py` runs live scans.
- [X] AI feedback reports: `data/reports/ai_feedback_summary.json`, `data/reports/ai_feedback_summary.md`, `data/reports/decision_evaluations.csv`.

## Definition Of Ready For Real Money

- [ ] Backtest shows positive expectancy after fees and slippage.
- [ ] Paper trading runs at least 30 days.
- [X] Decision logs explain every trade and every blocked trade.
- [ ] Max drawdown stays within limit.
- [X] Monthly loss limiter exists.
- [ ] Critical event feed is fresh during trading hours.
- [ ] No direct trade execution by Claude.
