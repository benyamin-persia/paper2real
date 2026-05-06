# Daily Validation Report

Generated: 2026-05-06T22:10:16.257126+00:00
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

- /system-health: `ok=True` `http=200` `elapsed=12.886s`
- /learning-status: `ok=True` `http=200` `elapsed=0.037s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.002s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.013s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.006s`
- /reports: `ok=True` `http=200` `elapsed=0.011s`

## Learning Counts

- decisions_total: `35`
- claude_buy_count: `1`
- candidate_buy_count: `8`
- risk_blocked_candidates: `8`
- trades_executed: `0`
- shadow_buy_count: `11`
- shadow_smart_money_count: `2`

## Progress Targets

- Blocked BUY candidates: `8 / 30`
- Shadow BUYs: `11 / 100`
- Shadow Smart Money: `2 / 50`
- Ready for risk block review: `False`
- Ready for Smart Money review: `False`

## Risk Block Performance

- Total blocked candidates: `8`
- BB squeeze: `{'count': 4, 'avg_return_1h': -0.1445, 'avg_return_4h': -0.0394, 'avg_return_24h': -0.2747, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 0, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 0, 'verdict': 'not_enough_data'}`

## Smart Money Performance

- Shadow count: `2`
- Ready for bonus: `False`
- Score distribution: `{'0-39': 0, '40-59': 0, '60-79': 0, '80-100': 2}`
- Bias distribution: `{'bullish': 2}`

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
