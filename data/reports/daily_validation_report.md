# Daily Validation Report

Generated: 2026-05-07T10:00:19.591522+00:00
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

- /system-health: `ok=True` `http=200` `elapsed=16.515s`
- /learning-status: `ok=True` `http=200` `elapsed=0.072s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.002s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.046s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.007s`
- /reports: `ok=True` `http=200` `elapsed=0.012s`

## Learning Counts

- decisions_total: `45`
- claude_buy_count: `1`
- candidate_buy_count: `18`
- risk_blocked_candidates: `18`
- trades_executed: `0`
- shadow_buy_count: `21`
- shadow_smart_money_count: `12`

## Progress Targets

- Blocked BUY candidates: `18 / 30`
- Shadow BUYs: `21 / 100`
- Shadow Smart Money: `12 / 50`
- Ready for risk block review: `False`
- Ready for Smart Money review: `False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `7`
- Live paper scans total: `38`
- Last learning-only scan: `2026-05-07T09:00:20+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `7`
- Estimated learning API cost daily: `$0.155469`
- Estimated learning API cost monthly: `$4.66407`
- Estimated days to 30 blocked BUY candidates: `0.42`
- Estimated days to 100 shadow BUYs: `2.8`
- Estimated days to 50 Smart Money shadows: `1.34`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `18`
- BB squeeze: `{'count': 12, 'avg_return_1h': -0.0247, 'avg_return_4h': 0.254, 'avg_return_24h': -0.3417, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 0, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 0, 'verdict': 'not_enough_data'}`

## Smart Money Performance

- Shadow count: `12`
- Ready for bonus: `False`
- Score distribution: `{'0-39': 0, '40-59': 0, '60-79': 10, '80-100': 2}`
- Bias distribution: `{'bullish': 4, 'bearish': 8}`

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
