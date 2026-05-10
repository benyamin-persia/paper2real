# Paper2Real Implementation Log

Last updated: 2026-05-05

## Current Profitability-Learning Layer

This project now has a deterministic learning layer around Claude. Claude is still only an analyst. The deterministic `risk_engine.py` remains final authority and was not weakened.

## What Was Added

### Dashboard Visibility

The dashboard at `http://192.168.1.162:8000/` now shows:

- Trade Quality Score
- Why No Trade?
- Missed Opportunity
- Data Source Trust
- Learning Status
- Trade Quality Threshold Sweep
- Shadow BUY Performance
- Downloads tab for audit/learning artifacts

### Downloadable Artifacts

Available endpoints:

- `/download/all.zip`
- `/download/paper-trader.db`
- `/download/decisions.csv`
- `/download/events.csv`
- `/download/trades.csv`
- `/download/logs.json`

Secrets are intentionally excluded from downloads:

- `.env`
- API keys
- Telegram token
- cookies
- private credentials

### Data Quality Fix

Yahoo live BTC volume can be unreliable. The app now detects this:

- `volume_quality = unreliable`
- `volume_ratio = null`
- zero-volume bars are shown in the dashboard

Claude is explicitly told not to treat unreliable zero volume as bearish evidence.

### Historical Matcher Fix

The historical matcher no longer crashes when `volume_ratio` is `None`.

When volume is unreliable, volume is excluded from similarity matching instead of being treated as `0`.

### Trade Quality Score

New file:

- `trade_quality.py`

Score components:

- trend
- momentum
- volatility
- derivatives
- macro
- historical match
- data quality
- risk safety

The score is stored in SQLite in both JSON and queryable columns.

### Real DB Columns Added

The `decisions` table now keeps:

- `trade_quality_json`
- `tq_score`
- `tq_trend`
- `tq_momentum`
- `tq_volatility`
- `tq_derivatives`
- `tq_macro`
- `tq_historical_match`
- `tq_data_quality`
- `tq_risk_safety`
- `tq_primary_reason`

### Shadow BUY Learning Mode

Shadow BUY does not execute a trade and does not change the paper portfolio.

It logs a hypothetical BUY only when:

- final action is `HOLD`
- Trade Quality Score is above `SHADOW_BUY_SCORE_THRESHOLD`

Stored fields:

- `shadow_action`
- `shadow_entry_price`
- `shadow_score`
- `shadow_reason`
- `shadow_stop_price`
- `shadow_take_profit_price`
- `shadow_future_return_1h`
- `shadow_future_return_4h`
- `shadow_future_return_24h`

Purpose:

Measure whether the system is too conservative without risking safety.

### Trade Quality Sweep Backtest

New file:

- `trade_quality_sweep.py`

It tests thresholds:

- 55
- 60
- 65
- 70
- 75
- 80
- 85

Outputs:

- `data/reports/trade_quality_sweep.json`
- `data/reports/trade_quality_sweep.csv`

Metrics:

- total return
- max drawdown
- win rate
- profit factor
- number of trades
- average trade
- worst trade
- HOLD ratio
- missed upside HOLDs

### AI Feedback Evaluator Update

`decision_evaluator.py` now evaluates:

- Claude decisions
- final risk-engine decisions
- shadow BUY decisions
- missed opportunity HOLDs
- risk-engine blocks

It also writes future shadow returns back into SQLite when enough future price data exists.

### Telegram Rules

Telegram remains notification-only.

It must not receive secrets.

Recommended behavior:

- CRITICAL: immediate
- WARNING: immediate
- INFO: summary/digest only

SQLite/dashboard remain the full source of truth.

## Current Important Endpoints

- `/learning-status`
- `/missed-opportunities`
- `/trade-quality-sweep`
- `/shadow-performance`
- `/market-context`
- `/decisions`
- `/ai-audit`
- `/events`
- `/reports`
- `/system-health`
- `/api-usage`

## Current Known State

The bot is safe but still too conservative:

- many HOLD decisions
- zero real paper trades so far
- shadow BUY layer now measures whether high-score HOLDs would have worked

The next decision is now measurable:

- If shadow BUYs win, loosen analyst prompt/thresholds carefully.
- If shadow BUYs lose, keep the current conservative posture.

No safety rules should be removed until shadow learning and paper trades produce enough evidence.

## Risk Block Outcome Evaluation

Status: implemented as the next audit layer.

Rules frozen:

- `TRADE_QUALITY_BUY_THRESHOLD=65`
- `SHADOW_BUY_SCORE_THRESHOLD=60`
- `TRADE_QUALITY_CAN_PROPOSE_BUY=true`

What changed:

- `risk_engine.py` behavior is unchanged.
- `candidate_action` is now separate from Claude's original `claude_action`.
- `candidate_source` can be `claude`, `trade_quality`, `both`, or `none`.
- `pre_risk_tq_*` fields store the Trade Quality score that created the candidate.
- `post_risk_tq_*` fields store the score after risk-engine context is known.
- A risk-engine block is recorded as `risk_blocked_candidate=1` only when a BUY candidate becomes final HOLD because a risk rule blocked it.
- Blocked BUY candidates are evaluated after 1h, 4h, and 24h.
- Reports are written to `data/reports/risk_block_performance.json` and `.csv`.

Decision rule:

- Do not remove `bb_squeeze` or any other blocker until at least 30 blocked BUY candidates are measured.
- If a blocker saves more losses than blocked winners, keep it.
- If a blocker blocks more winners than saved losses, convert it later from a hard block into a soft penalty.
- Thresholds remain frozen until the risk-block evidence is large enough to tune.

New endpoint:

- `/risk-block-performance`

## Smart Money Structure Layer

Status: implemented as shadow/evidence only.

Safety rule:

- Smart Money does not execute trades.
- Smart Money does not bypass `risk_engine.py`.
- Smart Money does not remove or weaken `bb_squeeze`, daily loss, monthly loss, max drawdown, max open trades, or consecutive loss protection.
- Default config keeps Smart Money in shadow mode: `SMART_MONEY_SHADOW_ONLY=true` and `SMART_MONEY_MAX_TQ_BONUS=0`.

What it detects:

- Swing highs and swing lows from closed candles only.
- BOS: close above prior confirmed swing high or below prior confirmed swing low.
- CHoCH: structure flips direction after breaking the prior opposite structure.
- Liquidity zones: swing highs/lows plus equal highs/lows within 0.2%.
- Liquidity sweeps: wick through a liquidity zone with close back inside.
- Order blocks: last opposite candle before a BOS, filtered by strength.
- Fair Value Gaps: three-candle imbalance gaps, with active/filled state.
- Premium/discount: current price relative to the latest major swing range midpoint.
- Multi-timeframe alignment using 15m, 1h, and 4h candles.

Files added:

- `market_structure.py`
- `liquidity.py`
- `order_blocks.py`
- `fair_value_gaps.py`
- `premium_discount.py`
- `smart_money.py`
- `smart_money_backtest.py`

Reports added:

- `data/reports/market_structure_events.csv/json`
- `data/reports/liquidity_zones.csv/json`
- `data/reports/order_blocks.csv/json`
- `data/reports/fair_value_gaps.csv/json`
- `data/reports/premium_discount_zones.csv/json`
- `data/reports/smart_money_summary.json`
- `data/reports/smart_money_backtest.csv/json`

Database fields added:

- `smart_money_score`
- `smart_money_bias`
- `smart_money_reason`
- `smart_money_json`
- `structure_state`
- `liquidity_state`
- `order_block_state`
- `fvg_state`
- `premium_discount_state`
- `timeframe_alignment`
- `shadow_smart_money_action`
- `shadow_smart_money_score`
- `shadow_smart_money_bias`
- `shadow_smart_money_reason`
- `shadow_smart_money_future_return_1h`
- `shadow_smart_money_future_return_4h`
- `shadow_smart_money_future_return_24h`

Endpoints added:

- `/smart-money`
- `/market-structure`
- `/liquidity-zones`
- `/order-blocks`
- `/fair-value-gaps`
- `/premium-discount`
- `/smart-money-backtest`

Dashboard added:

- New `Smart Money` tab.
- Current Smart Money score and bias.
- Structure, liquidity, order block, FVG, and premium/discount tables.
- Smart Money backtest summary.

Current engineering decision:

- Keep this layer shadow-only until it proves directional edge.
- Use `/smart-money-backtest` and shadow Smart Money future returns to decide later whether it deserves any Trade Quality bonus.
- Do not enable `SMART_MONEY_MAX_TQ_BONUS` until the sample is large enough and profitable directionally.

## Full Application Test Pass

Local verification completed:

- Python compile passed for `main.py`, `trader.py`, `trade_quality.py`, `decision_evaluator.py`, all Smart Money modules, and `smart_money_backtest.py`.
- `trader.init_db()` migration passed.
- `trader.log_decision()` insert passed against a temporary DB.
- `/missed-opportunities` no longer returns invalid NaN JSON.
- Smart Money reports generate successfully from cached live BTC candles.
- `/download/all.zip` includes Smart Money reports and excludes `.env`.
- Dashboard tabs verified with Playwright: Trades, Decisions, Twitter Extracted, AI Brain Audit, Reports, Smart Money, Notifications, Live Logs, Downloads, Money Settings.

## Daily Validation Report

Status: implemented as reporting only.

Safety rule:

- No trading logic changed.
- `risk_engine.py` unchanged.
- Trade Quality thresholds unchanged.
- Smart Money config unchanged.
- Smart Money remains shadow-only and does not affect Trade Quality by default.

Files:

- `daily_validation_report.py`
- `data/reports/daily_validation_report.json`
- `data/reports/daily_validation_report.md`

Endpoint:

- `/daily-validation-report`

Dashboard:

- Added top-level `Daily Validation` card.
- Shows current recommendation, system health, ready-to-tune status, and progress bars for:
  - 30 blocked BUY candidates
  - 100 shadow BUYs
  - 50 Smart Money shadow candidates

Recommendation rules:

- If blocked BUY candidates are below 30, report includes `COLLECT_MORE_DATA`.
- If shadow Smart Money candidates are below 50, Smart Money remains shadow-only.
- If source health fails, report includes `INVESTIGATE_ERROR`.
- Report never recommends changing `risk_engine.py` before minimum sample size.

Download:

- `/download/all.zip` now includes `daily_validation_report.json` and `.md`.
- Secrets remain excluded.

## Unattended Validation Monitoring

Status: implemented as reporting and safe publishing only.

What changed:

- `daily_validation_report.py` now checks local app endpoints directly:
  - `/system-health`
  - `/learning-status`
  - `/risk-block-performance`
  - `/shadow-performance`
  - `/smart-money-backtest`
  - `/reports`
- It verifies `/download/all.zip` by opening the ZIP and scanning filenames plus safe text files for token, cookie, password, credential, private key, and API key patterns.
- It emits flat report fields for scheduled monitoring:
  - `generated_at`
  - `system_health_status`
  - `master_dataset_last_date`
  - `master_dataset_rows`
  - `master_dataset_columns`
  - `stale_dataset_warning`
  - `endpoint_statuses`
  - `decisions_total`
  - `claude_buy_count`
  - `candidate_buy_count`
  - `risk_blocked_candidates`
  - `trades_executed`
  - `shadow_buy_count`
  - `shadow_smart_money_count`
  - `ready_for_risk_block_review`
  - `ready_for_smart_money_review`
  - `download_zip_safe`
  - `secrets_excluded`
  - `errors`
  - `final_recommendation`
- `deploy/run_daily_validation_and_push.sh` runs the report inside the Docker container, then commits and pushes only:
  - `data/reports/daily_validation_report.json`
  - `data/reports/daily_validation_report.md`
- `deploy/install_daily_validation_cron.sh` installs a 6-hour cron entry for the host runner.

Publishing guardrails:

- The scheduled Git push aborts if the report says the download ZIP is unsafe.
- The scheduled Git push aborts if any staged file is outside the two safe report paths.
- `.env`, API keys, Telegram tokens, cookies, private credentials, runtime DB files, logs, and ZIP downloads are never staged by the runner.
- The `/daily-validation-report` dashboard endpoint runs report generation with auto-push disabled, so opening the dashboard cannot create Git commits.

## 1-Hour Learning-Only Scans

Status: implemented as evidence collection only.

Why this exists:

- Normal paper scans are intentionally conservative and run slowly.
- Learning-only scans collect candidate BUY, risk-block, shadow BUY, and Smart Money shadow evidence faster.
- The goal is better measurement, not new trade execution.

Guardrails:

- Learning-only scans never execute BUY.
- Learning-only scans never execute SELL.
- Learning-only scans never change portfolio balance.
- Learning-only scans never open or close paper trades.
- `risk_engine.py` remains final authority for final action labeling.
- `bb_squeeze`, daily loss limit, monthly loss limit, max drawdown, max open trades, and consecutive loss protection remain unchanged.
- Trade Quality thresholds remain unchanged.
- Smart Money remains shadow-only.
- `SMART_MONEY_MAX_TQ_BONUS` remains `0`.

Scheduling:

- `deploy/run_learning_only_scan.sh` triggers the local app endpoint `/learning-only-scan`.
- `deploy/install_learning_only_cron.sh` installs an hourly cron entry.
- The runner uses a host lock directory to avoid overlapping cron runs.
- The app endpoint also uses the existing scan lock, so it will skip if a normal scan is already running.

Claude usage:

- Learning-only scans use selective Claude calls.
- Claude is called only when the scan has meaningful evidence:
  - Trade Quality score >= 55
  - Smart Money score >= 60
  - BTC moved more than 0.75% in the last hour
  - critical event or depeg exists
  - candidate action could become BUY
  - risk blocker changed
  - new BOS/CHoCH appeared
  - new liquidity sweep appeared
- Boring scans use deterministic evidence logging with `claude_called = 0`.

Duplicate suppression:

- Duplicate learning-only scans are not stored as full decision rows.
- Suppressed duplicates are logged as local events with event type `learning_only_scan_skipped_duplicate`.
- Telegram is not used for routine learning-only scans or duplicate suppression.

Daily validation:

- The validation report now tracks learning-only scan count, live paper scan count, duplicate suppression, Claude calls from learning scans, estimated learning API cost, and estimated days to sample targets.
- Tuning remains blocked until minimum sample targets are reached:
  - 30 risk-blocked BUY candidates
  - 100 shadow BUY records
  - 50 Smart Money shadow records
## Shadow BUY Review

The Shadow BUY review layer requires 100 shadow BUY observations before any recommendation can move beyond data collection. The report measures 1h, 4h, and 24h win rate, average return, median return, max favorable move, max adverse move, best/worst horizon, and positive expectancy.

This report is evidence only. It does not change BUY thresholds, Trade Quality scoring, risk engine behavior, paper balance, or portfolio logic.

## Technical Analysis Forecast Layer

The Technical Analysis layer calculates deterministic indicators from closed BTC candles only: EMA20/50/200, SMA20/50/200, RSI14, MACD, Bollinger Bands, ATR14, volume ratio, volume quality, BB squeeze state, trend state, momentum state, volatility state, and trend strength.

Support and resistance zones are detected from recent swing highs/lows, previous day/week highs/lows, psychological round levels, EMA dynamic levels, and Bollinger Band levels. Chart patterns are detected from closed candles only, including engulfing candles, hammer/shooting star, doji, strong candles, breakouts/breakdowns, double top/bottom, higher low/lower high, and simple RSI/MACD divergence.

The TA forecast combines bullish, bearish, and neutral evidence into a 0-100 score, bias, confidence, horizon predictions, nearest support/resistance, invalidation level, and risk level. It is shadow-only first because forecasts must prove future-return edge before any score bonus is considered. TA shadow candidates are logged only when final action is HOLD and TA score/confidence are high enough; future returns are evaluated at 15m, 1h, 4h, and 24h.

TA cannot execute trades, cannot create BUY by itself, cannot change portfolio, and cannot bypass `risk_engine.py`. A later Trade Quality bonus can only be discussed after enough shadow evidence shows positive 4h edge and acceptable drawdown risk.

## AI Technical Analyst Layer

The AI Technical Analyst layer was added to review structured chart facts like a professional analyst without screenshots. Indicators, support/resistance, chart patterns, Smart Money context, Trade Quality, candidate action, and risk-engine result are calculated deterministically before the AI analyst layer sees them.

The AI TA system prompt requires closed-candle evidence only, skepticism, strict JSON output, `should_trade=false`, and `risk_engine_respected=true`. Invalid JSON is handled safely by falling back to neutral score 0, and any `should_trade=true` or risk-engine override is corrected and logged as a violation.

AI TA is shadow-only first. It logs score, bias, confidence, horizon predictions, best horizon, evidence arrays, main reason, invalidation level, nearest support/resistance, and risk level. AI TA shadow candidates are logged only when final action is HOLD and score/confidence are high enough; future returns are evaluated at 15m, 1h, 4h, and 24h.

AI TA cannot execute trades, cannot change portfolio, cannot bypass `risk_engine.py`, and cannot enable any bonus. A later Trade Quality bonus can only be discussed after at least 50 AI TA shadow candidates show positive 4h edge, invalid JSON rate below 5%, and zero safety violations.
