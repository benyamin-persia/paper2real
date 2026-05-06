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
- If source health fails, report includes `INVESTIGATE_DATA_HEALTH`.
- Report never recommends changing `risk_engine.py` before minimum sample size.

Download:

- `/download/all.zip` now includes `daily_validation_report.json` and `.md`.
- Secrets remain excluded.
