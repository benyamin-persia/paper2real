# Daily Validation Report

Generated: 2026-05-13T16:00:24.038402+00:00
Primary recommendation: **INVESTIGATE_ERROR**
All recommendations: `INVESTIGATE_ERROR, READY_FOR_RISK_BLOCK_REVIEW, READY_FOR_SMART_MONEY_REVIEW`

## System Health

- Status: `warning`
- Master dataset last date: `2026-05-11`
- Rows: `532`
- Columns: `55`
- Stale dataset warning: `True`
- Errors: `[]`

## Endpoint Statuses

- /system-health: `ok=True` `http=200` `elapsed=14.431s`
- /learning-status: `ok=True` `http=200` `elapsed=0.245s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.002s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.323s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.006s`
- /shadow-buy-review: `ok=True` `http=200` `elapsed=0.062s`
- /technical-analysis: `ok=True` `http=200` `elapsed=0.061s`
- /support-resistance: `ok=True` `http=200` `elapsed=0.006s`
- /chart-patterns: `ok=True` `http=200` `elapsed=0.002s`
- /ta-forecast: `ok=True` `http=200` `elapsed=0.002s`
- /ta-backtest: `ok=True` `http=200` `elapsed=0.002s`
- /ai-technical-analyst: `ok=True` `http=200` `elapsed=0.007s`
- /ai-ta-performance: `ok=True` `http=200` `elapsed=0.002s`
- /ai-ta-backtest: `ok=True` `http=200` `elapsed=0.002s`
- /reports: `ok=True` `http=200` `elapsed=0.024s`

## Learning Counts

- decisions_total: `211`
- claude_buy_count: `1`
- candidate_buy_count: `149`
- risk_blocked_candidates: `148`
- trades_executed: `0`
- shadow_buy_count: `170`
- shadow_smart_money_count: `138`

## Progress Targets

- Blocked BUY candidates: `148 / 30`
- Shadow BUYs: `170 / 100`
- Shadow Smart Money: `138 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `True`
- Shadow BUY review: `171 / 100` `SHADOW_BUY_STAYS_SHADOW`
- TA shadow progress: `54 / 50` ready_for_bonus=`False`
- AI TA shadow progress: `54 / 50` ready_for_bonus=`False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `151`
- Live paper scans total: `60`
- Last learning-only scan: `2026-05-13T15:00:12+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `151`
- Estimated learning API cost daily: `$0.178169`
- Estimated learning API cost monthly: `$5.34507`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `0.0`
- Estimated days to 50 Smart Money shadows: `0.0`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `149`
- BB squeeze: `{'count': 66, 'avg_return_1h': 0.0165, 'avg_return_4h': 0.1212, 'avg_return_24h': -0.2583, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 0, 'saved_losses_1h': 0, 'saved_losses_4h': 2, 'saved_losses_24h': 15, 'verdict': 'helping'}`

## Smart Money Performance

- Shadow count: `138`
- Ready for bonus: `True`
- Score distribution: `{'0-39': 3, '40-59': 36, '60-79': 116, '80-100': 23}`
- Bias distribution: `{'bullish': 113, 'bearish': 61, 'neutral': 4}`

## TA / AI TA Shadow Layers

- TA enabled: `True` shadow_only=`True`
- TA shadow count: `54`
- TA avg future return 4h: `-0.0423`
- AI TA enabled: `True` shadow_only=`True`
- AI TA calls total: `101`
- AI TA shadow count: `54`
- AI TA avg future return 4h: `-0.0423`
- AI TA invalid JSON count: `0`
- AI TA safety violations: should_trade=`0`, risk_engine=`0`

## Download Safety

- Download ZIP safe: `True`
- Secrets excluded: `True`
- Files checked: `63`
- Findings: `[]`

## Guardrails

- Trading logic unchanged.
- risk_engine.py unchanged.
- Trade Quality thresholds unchanged.
- Smart Money remains shadow-only until minimum sample size is reached.
- This report never recommends risk_engine changes before 30 blocked BUY candidates.
