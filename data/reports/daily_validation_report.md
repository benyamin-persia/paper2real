# Daily Validation Report

Generated: 2026-05-08T14:21:13.294944+00:00
Primary recommendation: **COLLECT_MORE_DATA**
All recommendations: `COLLECT_MORE_DATA`

## System Health

- Status: `ok`
- Master dataset last date: `2026-05-08`
- Rows: `532`
- Columns: `55`
- Stale dataset warning: `False`
- Errors: `[]`

## Endpoint Statuses

- /system-health: `ok=True` `http=200` `elapsed=6.642s`
- /learning-status: `ok=True` `http=200` `elapsed=0.082s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.002s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.063s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.006s`
- /reports: `ok=True` `http=200` `elapsed=0.012s`

## Learning Counts

- decisions_total: `74`
- claude_buy_count: `1`
- candidate_buy_count: `25`
- risk_blocked_candidates: `25`
- trades_executed: `0`
- shadow_buy_count: `34`
- shadow_smart_money_count: `38`

## Progress Targets

- Blocked BUY candidates: `25 / 30`
- Shadow BUYs: `34 / 100`
- Shadow Smart Money: `38 / 50`
- Ready for risk block review: `False`
- Ready for Smart Money review: `False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `36`
- Live paper scans total: `38`
- Last learning-only scan: `2026-05-08T14:00:14+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `36`
- Estimated learning API cost daily: `$0.173548`
- Estimated learning API cost monthly: `$5.20644`
- Estimated days to 30 blocked BUY candidates: `0.52`
- Estimated days to 100 shadow BUYs: `4.8`
- Estimated days to 50 Smart Money shadows: `0.53`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `25`
- BB squeeze: `{'count': 19, 'avg_return_1h': -0.0329, 'avg_return_4h': -0.0469, 'avg_return_24h': -1.3869, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 0, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 8, 'verdict': 'not_enough_data'}`

## Smart Money Performance

- Shadow count: `38`
- Ready for bonus: `False`
- Score distribution: `{'0-39': 0, '40-59': 3, '60-79': 30, '80-100': 8}`
- Bias distribution: `{'bullish': 9, 'bearish': 32}`

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
