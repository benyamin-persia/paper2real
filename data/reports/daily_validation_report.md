# Daily Validation Report

Generated: 2026-05-07T04:00:18.840147+00:00
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

- /system-health: `ok=True` `http=200` `elapsed=16.211s`
- /learning-status: `ok=True` `http=200` `elapsed=0.039s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.002s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.02s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.006s`
- /reports: `ok=True` `http=200` `elapsed=0.01s`

## Learning Counts

- decisions_total: `39`
- claude_buy_count: `1`
- candidate_buy_count: `12`
- risk_blocked_candidates: `12`
- trades_executed: `0`
- shadow_buy_count: `15`
- shadow_smart_money_count: `6`

## Progress Targets

- Blocked BUY candidates: `12 / 30`
- Shadow BUYs: `15 / 100`
- Shadow Smart Money: `6 / 50`
- Ready for risk block review: `False`
- Ready for Smart Money review: `False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `1`
- Live paper scans total: `38`
- Last learning-only scan: `2026-05-07T03:03:35+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `1`
- Estimated learning API cost daily: `$0.213984`
- Estimated learning API cost monthly: `$6.41952`
- Estimated days to 30 blocked BUY candidates: `None`
- Estimated days to 100 shadow BUYs: `None`
- Estimated days to 50 Smart Money shadows: `None`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `12`
- BB squeeze: `{'count': 7, 'avg_return_1h': -0.1445, 'avg_return_4h': -0.0394, 'avg_return_24h': -0.3076, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 0, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 0, 'verdict': 'not_enough_data'}`

## Smart Money Performance

- Shadow count: `6`
- Ready for bonus: `False`
- Score distribution: `{'0-39': 0, '40-59': 0, '60-79': 4, '80-100': 2}`
- Bias distribution: `{'bullish': 3, 'bearish': 3}`

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
