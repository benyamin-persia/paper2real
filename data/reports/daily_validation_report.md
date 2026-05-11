# Daily Validation Report

Generated: 2026-05-11T17:24:56.213136+00:00
Primary recommendation: **READY_FOR_RISK_BLOCK_REVIEW**
All recommendations: `READY_FOR_RISK_BLOCK_REVIEW, READY_FOR_SMART_MONEY_REVIEW`

## System Health

- Status: `ok`
- Master dataset last date: `2026-05-11`
- Rows: `532`
- Columns: `55`
- Stale dataset warning: `False`
- Errors: `[]`

## Endpoint Statuses

- /system-health: `ok=True` `http=200` `elapsed=0.0s`
- /learning-status: `ok=True` `http=200` `elapsed=0.0s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.0s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.0s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.0s`
- /shadow-buy-review: `ok=True` `http=200` `elapsed=0.0s`
- /technical-analysis: `ok=True` `http=200` `elapsed=0.0s`
- /support-resistance: `ok=True` `http=200` `elapsed=0.0s`
- /chart-patterns: `ok=True` `http=200` `elapsed=0.0s`
- /ta-forecast: `ok=True` `http=200` `elapsed=0.0s`
- /ta-backtest: `ok=True` `http=200` `elapsed=0.0s`
- /ai-technical-analyst: `ok=True` `http=200` `elapsed=0.0s`
- /ai-ta-performance: `ok=True` `http=200` `elapsed=0.0s`
- /ai-ta-backtest: `ok=True` `http=200` `elapsed=0.0s`
- /reports: `ok=True` `http=200` `elapsed=0.0s`

## Learning Counts

- decisions_total: `153`
- claude_buy_count: `1`
- candidate_buy_count: `99`
- risk_blocked_candidates: `99`
- trades_executed: `0`
- shadow_buy_count: `113`
- shadow_smart_money_count: `109`

## Progress Targets

- Blocked BUY candidates: `99 / 30`
- Shadow BUYs: `113 / 100`
- Shadow Smart Money: `109 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `True`
- Shadow BUY review: `113 / 100` `SHADOW_BUY_READY_FOR_SMALL_TEST`
- TA shadow progress: `24 / 50` ready_for_bonus=`False`
- AI TA shadow progress: `24 / 50` ready_for_bonus=`False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `104`
- Live paper scans total: `49`
- Last learning-only scan: `2026-05-11T17:00:10+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `104`
- Estimated learning API cost daily: `$0.177119`
- Estimated learning API cost monthly: `$5.31357`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `0.0`
- Estimated days to 50 Smart Money shadows: `0.0`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `99`
- BB squeeze: `{'count': 55, 'avg_return_1h': 0.0702, 'avg_return_4h': 0.1261, 'avg_return_24h': -0.0534, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 1, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 9, 'verdict': 'neutral'}`

## Smart Money Performance

- Shadow count: `109`
- Ready for bonus: `True`
- Score distribution: `{'0-39': 0, '40-59': 11, '60-79': 86, '80-100': 23}`
- Bias distribution: `{'bullish': 76, 'bearish': 44}`

## TA / AI TA Shadow Layers

- TA enabled: `True` shadow_only=`True`
- TA shadow count: `24`
- TA avg future return 4h: `0.098`
- AI TA enabled: `True` shadow_only=`True`
- AI TA calls total: `43`
- AI TA shadow count: `24`
- AI TA avg future return 4h: `0.098`
- AI TA invalid JSON count: `0`
- AI TA safety violations: should_trade=`0`, risk_engine=`0`

## Download Safety

- Download ZIP safe: `True`
- Secrets excluded: `True`
- Files checked: `0`
- Findings: `[]`

## Guardrails

- Trading logic unchanged.
- risk_engine.py unchanged.
- Trade Quality thresholds unchanged.
- Smart Money remains shadow-only until minimum sample size is reached.
- This report never recommends risk_engine changes before 30 blocked BUY candidates.
