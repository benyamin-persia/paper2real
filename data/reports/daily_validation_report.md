# Daily Validation Report

Generated: 2026-05-07T22:00:35.072137+00:00
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

- /system-health: `ok=True` `http=200` `elapsed=11.786s`
- /learning-status: `ok=True` `http=200` `elapsed=0.133s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.004s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.083s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.012s`
- /reports: `ok=True` `http=200` `elapsed=0.025s`

## Learning Counts

- decisions_total: `57`
- claude_buy_count: `1`
- candidate_buy_count: `22`
- risk_blocked_candidates: `22`
- trades_executed: `0`
- shadow_buy_count: `28`
- shadow_smart_money_count: `24`

## Progress Targets

- Blocked BUY candidates: `22 / 30`
- Shadow BUYs: `28 / 100`
- Shadow Smart Money: `24 / 50`
- Ready for risk block review: `False`
- Ready for Smart Money review: `False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `19`
- Live paper scans total: `38`
- Last learning-only scan: `2026-05-07T21:00:16+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `19`
- Estimated learning API cost daily: `$0.17097`
- Estimated learning API cost monthly: `$5.1291`
- Estimated days to 30 blocked BUY candidates: `0.54`
- Estimated days to 100 shadow BUYs: `3.85`
- Estimated days to 50 Smart Money shadows: `1.02`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `22`
- BB squeeze: `{'count': 16, 'avg_return_1h': -0.0329, 'avg_return_4h': 0.0464, 'avg_return_24h': -0.3417, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 0, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 0, 'verdict': 'not_enough_data'}`

## Smart Money Performance

- Shadow count: `24`
- Ready for bonus: `False`
- Score distribution: `{'0-39': 0, '40-59': 0, '60-79': 17, '80-100': 7}`
- Bias distribution: `{'bullish': 5, 'bearish': 19}`

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
