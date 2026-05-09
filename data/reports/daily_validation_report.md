# Daily Validation Report

Generated: 2026-05-09T16:00:19.070020+00:00
Primary recommendation: **READY_FOR_RISK_BLOCK_REVIEW**
All recommendations: `COLLECT_MORE_DATA, READY_FOR_RISK_BLOCK_REVIEW, READY_FOR_SMART_MONEY_REVIEW`

## System Health

- Status: `ok`
- Master dataset last date: `2026-05-08`
- Rows: `532`
- Columns: `55`
- Stale dataset warning: `False`
- Errors: `[]`

## Endpoint Statuses

- /system-health: `ok=True` `http=200` `elapsed=14.083s`
- /learning-status: `ok=True` `http=200` `elapsed=0.104s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.002s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.095s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.006s`
- /reports: `ok=True` `http=200` `elapsed=0.013s`

## Learning Counts

- decisions_total: `99`
- claude_buy_count: `1`
- candidate_buy_count: `47`
- risk_blocked_candidates: `47`
- trades_executed: `0`
- shadow_buy_count: `59`
- shadow_smart_money_count: `58`

## Progress Targets

- Blocked BUY candidates: `47 / 30`
- Shadow BUYs: `59 / 100`
- Shadow Smart Money: `58 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `True`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `61`
- Live paper scans total: `38`
- Last learning-only scan: `2026-05-09T15:00:14+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `61`
- Estimated learning API cost daily: `$0.174714`
- Estimated learning API cost monthly: `$5.24142`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `2.28`
- Estimated days to 50 Smart Money shadows: `0.0`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `47`
- BB squeeze: `{'count': 35, 'avg_return_1h': 0.0007, 'avg_return_4h': 0.047, 'avg_return_24h': -0.7927, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 0, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 9, 'verdict': 'neutral'}`

## Smart Money Performance

- Shadow count: `58`
- Ready for bonus: `True`
- Score distribution: `{'0-39': 0, '40-59': 8, '60-79': 50, '80-100': 8}`
- Bias distribution: `{'bullish': 23, 'bearish': 43}`

## Download Safety

- Download ZIP safe: `True`
- Secrets excluded: `True`
- Files checked: `40`
- Findings: `[]`

## Guardrails

- Trading logic unchanged.
- risk_engine.py unchanged.
- Trade Quality thresholds unchanged.
- Smart Money remains shadow-only until minimum sample size is reached.
- This report never recommends risk_engine changes before 30 blocked BUY candidates.
