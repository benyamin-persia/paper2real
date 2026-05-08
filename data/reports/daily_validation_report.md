# Daily Validation Report

Generated: 2026-05-08T22:00:17.500975+00:00
Primary recommendation: **READY_FOR_RISK_BLOCK_REVIEW**
All recommendations: `COLLECT_MORE_DATA, READY_FOR_RISK_BLOCK_REVIEW`

## System Health

- Status: `ok`
- Master dataset last date: `2026-05-08`
- Rows: `532`
- Columns: `55`
- Stale dataset warning: `False`
- Errors: `[]`

## Endpoint Statuses

- /system-health: `ok=True` `http=200` `elapsed=14.175s`
- /learning-status: `ok=True` `http=200` `elapsed=0.098s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.002s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.079s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.007s`
- /reports: `ok=True` `http=200` `elapsed=0.013s`

## Learning Counts

- decisions_total: `81`
- claude_buy_count: `1`
- candidate_buy_count: `32`
- risk_blocked_candidates: `32`
- trades_executed: `0`
- shadow_buy_count: `41`
- shadow_smart_money_count: `45`

## Progress Targets

- Blocked BUY candidates: `32 / 30`
- Shadow BUYs: `41 / 100`
- Shadow Smart Money: `45 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `43`
- Live paper scans total: `38`
- Last learning-only scan: `2026-05-08T21:00:17+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `43`
- Estimated learning API cost daily: `$0.176825`
- Estimated learning API cost monthly: `$5.30475`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `3.82`
- Estimated days to 50 Smart Money shadows: `0.22`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `32`
- BB squeeze: `{'count': 26, 'avg_return_1h': 0.0011, 'avg_return_4h': 0.026, 'avg_return_24h': -1.0172, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 0, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 8, 'verdict': 'not_enough_data'}`

## Smart Money Performance

- Shadow count: `45`
- Ready for bonus: `False`
- Score distribution: `{'0-39': 0, '40-59': 3, '60-79': 37, '80-100': 8}`
- Bias distribution: `{'bullish': 9, 'bearish': 39}`

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
