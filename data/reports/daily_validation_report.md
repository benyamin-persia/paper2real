# Daily Validation Report

Generated: 2026-05-08T04:00:23.777598+00:00
Primary recommendation: **COLLECT_MORE_DATA**
All recommendations: `COLLECT_MORE_DATA`

## System Health

- Status: `ok`
- Master dataset last date: `2026-05-06`
- Rows: `532`
- Columns: `55`
- Stale dataset warning: `False`
- Errors: `[]`

## Endpoint Statuses

- /system-health: `ok=True` `http=200` `elapsed=14.683s`
- /learning-status: `ok=True` `http=200` `elapsed=0.076s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.003s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.089s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.01s`
- /reports: `ok=True` `http=200` `elapsed=0.025s`

## Learning Counts

- decisions_total: `63`
- claude_buy_count: `1`
- candidate_buy_count: `23`
- risk_blocked_candidates: `23`
- trades_executed: `0`
- shadow_buy_count: `30`
- shadow_smart_money_count: `30`

## Progress Targets

- Blocked BUY candidates: `23 / 30`
- Shadow BUYs: `30 / 100`
- Shadow Smart Money: `30 / 50`
- Ready for risk block review: `False`
- Ready for Smart Money review: `False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `25`
- Live paper scans total: `38`
- Last learning-only scan: `2026-05-08T03:00:14+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `25`
- Estimated learning API cost daily: `$0.170476`
- Estimated learning API cost monthly: `$5.11428`
- Estimated days to 30 blocked BUY candidates: `0.58`
- Estimated days to 100 shadow BUYs: `4.36`
- Estimated days to 50 Smart Money shadows: `0.8`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `23`
- BB squeeze: `{'count': 17, 'avg_return_1h': -0.0482, 'avg_return_4h': -0.0355, 'avg_return_24h': -1.0159, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 0, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 3, 'verdict': 'not_enough_data'}`

## Smart Money Performance

- Shadow count: `30`
- Ready for bonus: `False`
- Score distribution: `{'0-39': 0, '40-59': 0, '60-79': 22, '80-100': 8}`
- Bias distribution: `{'bullish': 5, 'bearish': 25}`

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
