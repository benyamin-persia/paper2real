# Paper2Real Build Checklist

Last updated: 2026-05-01

This is the working job list. `CLAUDE_CHATGPT_AGREEMENT.md` explains the rules. This file tells us what to build next.

## Rule For This Checklist

- Do jobs in order unless there is a real blocker.
- Do not add noisy data before risk controls, logs, and backtesting exist.
- Keep Claude as analyst only. `risk_engine.py` remains final authority.
- Prefer Playwright/browser data collection. Direct Python data calls are technical debt unless explicitly accepted.

## Phase 1: Safety And Auditability

- [x] Add monthly loss limiter in `risk_engine.py`.
  - Stop new BUYs if realized losses this month exceed the configured monthly limit.
  - SELL/HOLD must still be allowed.
  - Config value: `MONTHLY_LOSS_LIMIT_PCT = 15`.

- [x] Add decision audit logging.
  - Stored in SQLite `decisions` table.
  - `/decisions` endpoint summarizes Claude actions, final actions, executions, and risk blocks.
  - Applies to auto-scan, manual `/scan`, and `/webhook`.

- [x] Add data-source method audit.
  - Five direct `httpx` calls in `main.py`: Yahoo Finance candles, Coinbase candles fallback, Coinbase spot price, Coinbase USDT/USDC depeg check, alternative.me Fear & Greed.
  - All five are live signal checks (not historical scraping). All accepted under the practical rule.
  - No changes needed. Playwright remains for historical data collection only.

## Phase 2: Proof Before More Signals

- [x] Build real backtest engine.
  - File: `backtest.py`.
  - Replay historical candles.
  - Include fees, slippage, ATR stops, max open trades, daily loss limit, monthly loss limit, and risk-based position sizing.
  - Output win rate, max drawdown, total return, average trade, worst trade, number of trades, and HOLD ratio.

- [x] Add backtest report output.
  - Latest summary: `data/reports/backtest_latest.json`.
  - Trades: `data/reports/backtest_trades.csv`.
  - Equity curve: `data/reports/backtest_equity.csv`.

## Latest Backtest Result

Run date: 2026-05-01

- Period: 2024-11-15 to 2026-04-30.
- Rows replayed: 531.
- Final equity: $9,909.28.
- Return: -0.91%.
- Buy and hold return over same period: -17.18%.
- Max drawdown: 3.35%.
- Closed trades: 10.
- Win rate: 40.0%.
- Average trade: -$9.07.
- Worst trade: -$76.69.
- HOLD ratio: 98.12%.

Conclusion: the system is safer than buy-and-hold in this window, but it is not profitable yet. The main limiter is `consecutive_losses`: after four losses, 46 later BUY signals are blocked. Do not move to real money from this result.

Follow-up test: disabling the consecutive-loss brake made results worse (-2.07% return, 7.66% max drawdown, 49 closed trades, 28.57% win rate). The safety brake is helping; the BUY rule needs improvement.

## Phase 3: Live Reaction Improvements

- [x] Add event-driven scan trigger in `main.py`.
  - If BTC moves 2% or more in 30 minutes, run an emergency scan.
  - Max 3 emergency scans per day.
  - Minimum 30-minute cooldown.
  - Must still pass `risk_engine.evaluate()`.

- [x] Add scan trigger field to logs.
  - Values: `scheduled`, `manual`, `webhook`, `event_price_move`.

## Phase 4: High-Signal New Scrapers

- [ ] Improve strategy profitability before real money.
  - Latest backtest is negative after fees and slippage.
  - Do not optimize by adding noisy data first.
  - First inspect why BUY signals cluster before the consecutive-loss cutoff.

- [ ] Build Tier 1 X/Twitter scraper only.
  - Read `tier1_permanent` from `data/raw/account_tiers.json`.
  - Use Playwright/Nitter or browser scraping.
  - Save `data/raw/twitter_alerts.json`.
  - Only last 4 to 24 hours matter for live alerts.
  - Do not scrape all 84 accounts for every trade scan.

- [ ] Wire Tier 1 alerts into `main.py` and `brain.py`.
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
- [ ] Trade feedback loop after enough paper trades exist.
- [ ] Weekly auto-refresh scheduler for `collect.py`.
- [ ] Dashboard display for decision logs and blocked trades.
- [ ] Full 84-account sentiment run as a daily/weekly context job, only if Tier 1 proves useful.

## Skip For Now

- [ ] Reddit sentiment.
- [ ] Google Trends.
- [ ] Whale movement tracker.
- [ ] More technical indicators.
- [ ] Random influencer sentiment.

Reason: these are noisy, delayed, manipulated, or hard to scrape cleanly. They should not be added before the system can prove whether its current signals trade profitably.

## Current Data We Have

- [x] BTC candles: `data/raw/btc_15m_raw.csv`.
- [x] Fear and Greed: `data/raw/fear_greed.csv`.
- [x] CoinGlass derivatives: `data/raw/coinglass.csv`.
- [x] CoinGecko market structure: `data/raw/coingecko.csv`.
- [x] Macro: `data/raw/macro.csv`.
- [x] On-chain: `data/raw/onchain.csv`.
- [x] Critical events: `data/raw/events.json`.
- [x] X account list: `data/raw/account_tiers.json`.
- [x] Master dataset: `data/processed/master_dataset.csv`.

## Definition Of Ready For Real Money

- [ ] Backtest shows positive expectancy after fees and slippage.
- [ ] Paper trading runs at least 30 days.
- [x] Decision logs explain every trade and every blocked trade.
- [ ] Max drawdown stays within limit.
- [x] Monthly loss limiter exists.
- [ ] Critical event feed is fresh during trading hours.
- [ ] No direct trade execution by Claude.
