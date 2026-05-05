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
