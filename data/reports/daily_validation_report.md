# Daily Validation Report

Generated: 2026-05-08T16:00:19.213562+00:00
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

- /system-health: `ok=True` `http=200` `elapsed=15.857s`
- /learning-status: `ok=True` `http=200` `elapsed=0.099s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.002s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.07s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.006s`
- /reports: `ok=True` `http=200` `elapsed=0.012s`

## Learning Counts

- decisions_total: `75`
- claude_buy_count: `1`
- candidate_buy_count: `26`
- risk_blocked_candidates: `26`
- trades_executed: `0`
- shadow_buy_count: `35`
- shadow_smart_money_count: `39`

## Progress Targets

- Blocked BUY candidates: `26 / 30`
- Shadow BUYs: `35 / 100`
- Shadow Smart Money: `39 / 50`
- Ready for risk block review: `False`
- Ready for Smart Money review: `False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `37`
- Live paper scans total: `38`
- Last learning-only scan: `2026-05-08T15:00:13+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `37`
- Estimated learning API cost daily: `$0.173966`
- Estimated learning API cost monthly: `$5.21898`
- Estimated days to 30 blocked BUY candidates: `0.4`
- Estimated days to 100 shadow BUYs: `4.64`
- Estimated days to 50 Smart Money shadows: `0.48`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `26`
- BB squeeze: `{'count': 20, 'avg_return_1h': 0.0014, 'avg_return_4h': -0.0469, 'avg_return_24h': -1.3869, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 0, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 8, 'verdict': 'not_enough_data'}`

## Smart Money Performance

- Shadow count: `39`
- Ready for bonus: `False`
- Score distribution: `{'0-39': 0, '40-59': 3, '60-79': 31, '80-100': 8}`
- Bias distribution: `{'bullish': 9, 'bearish': 33}`

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
