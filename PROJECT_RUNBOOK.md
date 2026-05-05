# Paper2Real Project Runbook

Last updated: 2026-05-05

This is the continuity document for another AI or developer. Read this with:

- `CLAUDE.md`
- `CLAUDE_CHATGPT_AGREEMENT.md`
- `CHECKLIST.md`
- `deploy/TRUENAS_VM_DEPLOYMENT.md`

The goal is not to restart from scratch. The goal is to continue from the current running system.

## Current Deployment

The application is running on TrueNAS as a Docker container.

- Dashboard: `http://192.168.1.162:8000/`
- Remote project path: `/mnt/dl/dl/paper2real`
- Container name: `paper2real`
- Runtime image: `paper2real:runtime`
- Container user: UID `1000`
- Restart policy: `unless-stopped`
- App command: `uvicorn main:app --host 0.0.0.0 --port 8000`

Important: the current TrueNAS deployment is Docker directly on the NAS, not the originally planned Ubuntu VM/systemd deployment.

## System Architecture

The live system has six layers.

1. Historical data collection:
   - `collect.py`
   - `data/collector/*.py`
   - Output: `data/raw/*.csv`, `data/processed/master_dataset.csv`

2. Live market context:
   - `main.py:get_market_context()`
   - Pulls live BTC candles, indicators, Fear & Greed, stablecoin peg, daily CSV context, halving math, Twitter cache, and critical event status.

3. AI decision layer:
   - `brain.py`
   - Builds the visible prompt.
   - Calls Claude using `anthropic`.
   - Returns strict JSON: `BUY`, `SELL`, or `HOLD`.

4. Deterministic risk engine:
   - `risk_engine.py`
   - Final authority.
   - Can veto Claude.
   - Applies drawdown, loss limits, event staleness, stablecoin depeg, exchange alerts, confidence threshold, ATR sizing, max trades, macro event-day logic.

5. Paper trader and logging:
   - `trader.py`
   - SQLite database: `paper_trader.db`
   - Tables: `portfolio`, `trades`, `decisions`, `settings`

6. Observability dashboard:
   - `dashboard.html`
   - Endpoints in `main.py`
   - Shows price, portfolio, decisions, Twitter extraction, AI audit, API usage, logs, settings, backtest, and feedback reports.

## Current AI/API Usage

Current model in `brain.py`:

- `AI_MODEL = "claude-sonnet-4-6"`

Current pricing estimator in `config.py`:

- Input: `$3.00 / 1M tokens`
- Output: `$15.00 / 1M tokens`

Current live usage from `/api-usage` at the time of this update:

- Paid Claude calls logged: `5`
- Input tokens: `8,039`
- Output tokens: `1,218`
- Total tokens: `9,257`
- Total estimated cost: `$0.042387`
- Average per call:
  - Input tokens: about `1,608`
  - Output tokens: about `244`
  - Cost: about `$0.008477`

## Monthly Cost Projection

The scheduled scan interval is:

- `SCAN_INTERVAL_HOURS = 4`
- About `6` Claude calls per day
- About `180` scheduled Claude calls per 30-day month

At current prompt size:

| Scenario | Calls / Month | Estimated Monthly Cost |
|---|---:|---:|
| Scheduled scans only | 180 | about `$1.53` |
| Scheduled + max event scans | 270 | about `$2.29` |
| Scheduled + 10 manual scans/day | 480 | about `$4.07` |
| 1,000 calls/month | 1,000 | about `$8.48` |
| 10,000 calls/month | 10,000 | about `$84.77` |
| 100,000 calls/month | 100,000 | about `$847.74` |

At the current prompt size, this system is nowhere near `$1,000/month`, much less `$10,000/month`.

Approximate number of calls needed:

- `$1,000/month`: about `118,000` calls/month at the current prompt size.
- `$10,000/month`: about `1,180,000` calls/month at the current prompt size.

That would require thousands of AI decisions per day, which the current system does not do.

## What Causes Cost

Paid API cost currently comes only from Claude calls in `brain.py`.

Cost does not come from:

- Twitter/X scraping
- Yahoo Finance scraping
- CoinGlass scraping
- CoinGecko scraping
- CryptoPanic scraping
- Dashboard refresh
- `/portfolio`
- `/market-context`
- `/twitter-data`
- `/price-history`
- `/logs`
- `/reports`

Dashboard refresh does not call Claude. The `Scan Market Now` button does call Claude.

## What Is Necessary vs Wasteful

Necessary paid AI usage:

- One Claude decision every scheduled scan.
- One Claude decision for event-driven emergency scans when BTC moves sharply.
- Manual scan only when the user explicitly asks.

Potentially wasteful paid AI usage:

- Calling Claude on every dashboard refresh.
- Calling Claude separately for every tweet.
- Calling Claude separately for every Twitter account.
- Sending all scraped tweets instead of only alerts and recent relevant tweets.
- Sending full raw historical rows instead of summarized historical evidence.
- Running manual scans repeatedly during debugging.

Current system avoids those wasteful patterns.

## Cost Reduction Plan

If cost ever becomes high, reduce it in this order.

1. Keep best model only for final trade decisions.
2. Use local rules for sentiment, freshness, risk vetoes, and pre-filtering.
3. Only call Claude if local rules find a valid candidate setup.
4. Cache daily context and do not repeat it inside every prompt if unchanged.
5. Send top 3 Twitter alerts instead of top 10.
6. Send summarized historical evidence instead of raw examples.
7. Move routine explanations/report summaries to a cheaper model.
8. Reduce scheduled scans from every 4 hours to every 6 hours if signal quality does not drop.
9. Disable manual scan spam.
10. Keep event-driven scans, but cap them.

Recommended model split if switching providers:

- Best model: final trade decision only.
- Cheap model or local logic: tweet summarization, sentiment classification, log summaries, dashboard text.
- Local code only: indicators, risk engine, backtest, position sizing, freshness checks, data collection.

## Twitter/X Extraction

Current live Twitter extraction:

- File: `data/collector/twitter_playwright.py`
- Cache: `data/raw/twitter_playwright.json`
- CSV: `data/raw/twitter_tweets.csv`
- Timing CSV: `data/raw/twitter_timing.csv`
- Frequency: every `30` minutes from `_twitter_refresh_loop()` in `main.py`
- Accounts used live: `tier1_permanent` from `data/raw/account_tiers.json`
- Current tier 1 count: `24`
- Tweets per account: `4`
- Workers: `4`
- Current scrape result: `96` tweets in about `50` seconds, `0` paid API calls.

Extracted per tweet:

- handle
- rank
- tweet id
- timestamp
- text
- url
- pinned flag
- comments / replies
- retweets / reposts
- quotes
- likes
- views
- bookmarks
- media URLs when available
- local sentiment score
- local impact score
- alert keywords
- account elapsed time
- account error

Twitter/X paid API usage:

- `0`

Claude API usage per individual Twitter account:

- `0`

Only selected Twitter alert/recent context is inserted into the Claude trade-decision prompt. Claude is not called once per account.

## Tier 1 Twitter/X Accounts

These are currently extracted every 30 minutes.

| Account | Why Selected |
|---|---|
| `POTUS` | Official US President account; executive policy can move crypto risk sentiment. |
| `WhiteHouse` | Official White House policy announcements; regulation and executive orders. |
| `realDonaldTrump` | US President personal account; crypto policy and market sentiment impact. |
| `federalreserve` | Federal Reserve policy; rates and liquidity drive BTC risk appetite. |
| `SECGov` | SEC enforcement and ETF/regulatory announcements. |
| `USTreasury` | Treasury sanctions, tax, stablecoin, and financial policy. |
| `CFTC` | Derivatives regulator; crypto futures/enforcement relevance. |
| `TheJusticeDept` | DOJ enforcement; exchange/criminal cases can create market shocks. |
| `JPMorgan` | Major bank/institutional sentiment and custody/market commentary. |
| `BlackRock` | Largest asset manager; ETF and institutional Bitcoin flow signal. |
| `iShares` | BlackRock ETF brand; ETF flow and product announcements. |
| `Fidelity` | Major Bitcoin ETF/institutional custody provider. |
| `MicroStrategy` | Largest public corporate BTC treasury buyer. |
| `saylor` | Michael Saylor; MicroStrategy BTC strategy and market-moving commentary. |
| `binance` | Largest crypto exchange; outages, listings, enforcement, reserves. |
| `coinbase` | Major US exchange; regulatory and market structure signal. |
| `Grayscale` | Major crypto fund/ETF issuer. |
| `Tether` | USDT issuer; stablecoin liquidity and depeg/reserve relevance. |
| `paoloardoino` | Tether CEO; direct USDT liquidity/security statements. |
| `zachxbt` | Crypto security investigator; early hacks/scams/exploit alerts. |
| `PeckShieldAlert` | Security alerts for exploits, hacks, suspicious flows. |
| `SlowMist_Team` | Security intelligence and exploit alerts. |
| `CertiKAlert` | Security alerts and phishing/exploit monitoring. |
| `WuBlockchain` | Fast Asia/China crypto news; exchange/regulatory signal. |

The dashboard endpoint `/twitter-accounts` returns per-account chart data:

- account tier
- reason selected
- extracted fields
- frequency
- paid API calls
- paid API cost
- tweet count
- sentiment series
- engagement totals

## How The System Improves Over Time

The system does not magically train a model. It improves by saving decisions and scoring them later against real price movement.

Saved every scan in `paper_trader.db.decisions`:

- timestamp
- trigger type: scheduled, manual, webhook, event price move
- BTC price
- RSI
- Fear & Greed
- funding rate
- Claude action
- Claude confidence
- Claude reason
- final risk-engine action
- blocked rule
- block reason
- position size
- stop price
- trade executed flag
- risk summary
- invalidation rules
- historical summary JSON
- model name
- visible prompt sent to Claude
- visible response from Claude
- input tokens
- output tokens
- estimated API cost

Saved by paper trader in `paper_trader.db.trades`:

- buys
- sells
- BTC amount
- entry price
- exit price
- P&L
- stop price
- highest seen
- close reason

Saved by live candle cache:

- `data/raw/live_btc_15m.csv`

Saved by decision evaluator:

- `data/reports/ai_feedback_summary.json`
- `data/reports/ai_feedback_summary.md`
- `data/reports/decision_evaluations.csv`

`decision_evaluator.py` scores each decision at:

- 1 hour
- 4 hours
- 24 hours

It tracks:

- whether Claude BUYs worked
- whether HOLD missed upside
- whether risk engine blocked bad trades
- whether risk engine blocked winners
- best and worst conditions
- recommendation after enough samples

`brain.py` reads the latest AI feedback summary and includes it in the next prompt. That is the feedback loop.

Minimum useful sample:

- 50 to 100 live decisions before changing strategy.
- More if there are very few BUY/SELL actions.

## Current Data Sources

Working historical/live data:

- BTC OHLCV: Yahoo Finance via Playwright/browser fetch
- Fear & Greed: alternative.me via browser fetch
- Derivatives: CoinGlass via Playwright/browser fetch
- Market structure: CoinGecko via Playwright/browser fetch
- Macro: Yahoo Finance via Playwright/browser fetch
- On-chain: blockchain.com/blockchain.info via browser fetch
- Critical events: CryptoPanic via Playwright
- Twitter/X Tier 1: X.com via Playwright
- Halving cycle: calculated locally
- Live price/candles: Yahoo Finance, fallback Coinbase
- Stablecoin peg: Coinbase public price endpoint

## Key Endpoints

Dashboard:

- `GET /`

Trading:

- `POST /scan`
- `POST /webhook`

State:

- `GET /portfolio`
- `GET /trades`
- `GET /decisions`
- `GET /performance`
- `GET /settings`
- `POST /settings`

Observability:

- `GET /market-context`
- `GET /price-history`
- `GET /twitter-data`
- `GET /twitter-accounts`
- `GET /api-usage`
- `GET /ai-audit`
- `GET /logs`
- `GET /reports`
- `GET /backtest-equity`
- `GET /events`
- `GET /risk-status`
- `GET /system-health`
- `GET /telegram/status`
- `POST /telegram/test`

## Telegram Notifications

Telegram is optional. It is a notification mirror, not the source of truth.
All events are stored locally in SQLite first in the `events` table.

Environment variables:

```bash
TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TELEGRAM_MIN_SEVERITY=WARNING
```

If `TELEGRAM_ENABLED` is false, or the token/chat ID is missing, the app continues
normally and logs events locally only.

Telegram sends only approved notifications:

- scan completed
- trade executed
- risk-engine block
- critical market alert
- stale/missing data
- scraper failure
- app startup/shutdown
- daily summary
- weekly summary
- API cost summary inside daily summary

Telegram messages are redacted automatically. Do not send `.env`, API keys,
tokens, cookies, authorization headers, webhook secrets, private keys, or raw
credentials.

Use `POST /telegram/test` to send a safe test message after configuring the bot.

## Important Files

Core:

- `main.py`: FastAPI app, scheduler loops, live context, dashboard endpoints.
- `brain.py`: Claude prompt and AI decision.
- `risk_engine.py`: deterministic veto and risk sizing.
- `trader.py`: SQLite DB, portfolio, trades, decisions, settings, API accounting.
- `dashboard.html`: control-room dashboard.

Data:

- `collect.py`: full dataset collection.
- `data/collector/*.py`: scrapers.
- `data/processor/*.py`: indicators, labels, matcher.
- `data/raw/account_tiers.json`: Twitter account tiers.
- `data/raw/twitter_playwright.json`: latest Twitter scrape cache.
- `data/raw/twitter_tweets.csv`: latest tweet table.
- `data/raw/live_btc_15m.csv`: live candle cache.
- `data/processed/master_dataset.csv`: historical ML/pattern context.

Validation:

- `backtest.py`
- `decision_evaluator.py`
- `data/reports/backtest_latest.json`
- `data/reports/backtest_equity.csv`
- `data/reports/ai_feedback_summary.json`

Docs:

- `PROJECT_RUNBOOK.md`
- `CLAUDE.md`
- `CLAUDE_CHATGPT_AGREEMENT.md`
- `CHECKLIST.md`
- `deploy/TRUENAS_VM_DEPLOYMENT.md`

## Switching AI Providers

To switch from Anthropic/Claude to another AI provider:

1. Keep the schema in `brain.py` unchanged:
   - action
   - confidence
   - reason
   - risk_summary
   - invalid_if

2. Replace only this part:
   - `client = anthropic.Anthropic(...)`
   - `client.messages.create(...)`

3. Preserve these outputs:
   - `_api_usage.input_tokens`
   - `_api_usage.output_tokens`
   - `_audit.model`
   - `_audit.prompt`
   - `_audit.response`

4. Update pricing in `.env` or `config.py`:
   - `AI_INPUT_USD_PER_MILLION_TOKENS`
   - `AI_OUTPUT_USD_PER_MILLION_TOKENS`

5. Do not change `risk_engine.py` unless risk rules intentionally change.

The risk engine is provider-independent.

## Operational Commands

Check container:

```bash
docker ps --filter name=paper2real
docker logs --tail 100 paper2real
```

Restart app:

```bash
docker restart paper2real
```

Run backtest:

```bash
docker exec -w /app paper2real python backtest.py
```

Run decision evaluator:

```bash
docker exec -w /app paper2real python decision_evaluator.py
```

Run Twitter scraper manually:

```bash
docker exec -w /app paper2real python -m data.collector.twitter_playwright --tier tier1 --workers 4 --max-tweets 4
```

## Current Known Risks

1. TrueNAS ACL issue:
   - `.env` and `paper_trader.db` may show broad permissions because the dataset ACL blocks normal chmod.
   - Fix in TrueNAS WebUI or move project to a dataset with sane POSIX permissions.

2. Twitter/X scraping can break:
   - X.com markup changes.
   - Rate limiting can happen.
   - This does not create paid API cost, but can reduce sentiment quality.

3. Decision sample is still small:
   - The system has only a small number of logged live decisions.
   - Do not trust profitability until enough paper-trading decisions are scored.

4. Backtest is deterministic:
   - It validates label/risk logic, not full live Claude behavior.

5. Hidden chain-of-thought is not available:
   - The dashboard shows visible prompt, visible response, final reason, risk rules, and audit data.
   - It does not and should not expose hidden model reasoning.

## What To Do Next

Priority order:

1. Let paper trader run for 30 days.
2. Review `/api-usage` weekly.
3. Review `/ai-audit` for prompt quality.
4. Run `decision_evaluator.py` daily or every few hours.
5. Use `data/reports/ai_feedback_summary.json` to decide if risk rules are too strict or too loose.
6. Fix any Twitter accounts returning stale/irrelevant data.
7. Only after 50 to 100 scored decisions, consider strategy changes.
