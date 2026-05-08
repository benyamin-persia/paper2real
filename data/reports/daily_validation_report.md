# Daily Validation Report

Generated: 2026-05-08T10:00:17.483573+00:00
Primary recommendation: **INVESTIGATE_ERROR**
All recommendations: `INVESTIGATE_ERROR, COLLECT_MORE_DATA`

## System Health

- Status: `warning`
- Master dataset last date: `2026-05-06`
- Rows: `532`
- Columns: `55`
- Stale dataset warning: `True`
- Errors: `[]`

## Endpoint Statuses

- /system-health: `ok=True` `http=200` `elapsed=13.79s`
- /learning-status: `ok=True` `http=200` `elapsed=0.09s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.002s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.062s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.007s`
- /reports: `ok=True` `http=200` `elapsed=0.012s`

## Learning Counts

- decisions_total: `69`
- claude_buy_count: `1`
- candidate_buy_count: `23`
- risk_blocked_candidates: `23`
- trades_executed: `0`
- shadow_buy_count: `32`
- shadow_smart_money_count: `35`

## Progress Targets

- Blocked BUY candidates: `23 / 30`
- Shadow BUYs: `32 / 100`
- Shadow Smart Money: `35 / 50`
- Ready for risk block review: `False`
- Ready for Smart Money review: `False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `31`
- Live paper scans total: `38`
- Last learning-only scan: `2026-05-08T09:00:14+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `31`
- Estimated learning API cost daily: `$0.169927`
- Estimated learning API cost monthly: `$5.09781`
- Estimated days to 30 blocked BUY candidates: `0.73`
- Estimated days to 100 shadow BUYs: `4.71`
- Estimated days to 50 Smart Money shadows: `0.62`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `23`
- BB squeeze: `{'count': 17, 'avg_return_1h': -0.0482, 'avg_return_4h': -0.0469, 'avg_return_24h': -1.3869, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 0, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 8, 'verdict': 'not_enough_data'}`

## Smart Money Performance

- Shadow count: `35`
- Ready for bonus: `False`
- Score distribution: `{'0-39': 0, '40-59': 1, '60-79': 27, '80-100': 8}`
- Bias distribution: `{'bullish': 6, 'bearish': 30}`

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
