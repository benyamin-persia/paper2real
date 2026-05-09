# Daily Validation Report

Generated: 2026-05-09T10:00:19.017715+00:00
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

- /system-health: `ok=True` `http=200` `elapsed=11.555s`
- /learning-status: `ok=True` `http=200` `elapsed=0.097s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.002s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.091s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.027s`
- /reports: `ok=True` `http=200` `elapsed=0.039s`

## Learning Counts

- decisions_total: `93`
- claude_buy_count: `1`
- candidate_buy_count: `43`
- risk_blocked_candidates: `43`
- trades_executed: `0`
- shadow_buy_count: `53`
- shadow_smart_money_count: `52`

## Progress Targets

- Blocked BUY candidates: `43 / 30`
- Shadow BUYs: `53 / 100`
- Shadow Smart Money: `52 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `True`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `55`
- Live paper scans total: `38`
- Last learning-only scan: `2026-05-09T09:00:15+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `55`
- Estimated learning API cost daily: `$0.1769`
- Estimated learning API cost monthly: `$5.307`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `2.71`
- Estimated days to 50 Smart Money shadows: `0.0`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `43`
- BB squeeze: `{'count': 35, 'avg_return_1h': 0.0007, 'avg_return_4h': 0.0601, 'avg_return_24h': -0.9254, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 0, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 8, 'verdict': 'neutral'}`

## Smart Money Performance

- Shadow count: `52`
- Ready for bonus: `True`
- Score distribution: `{'0-39': 0, '40-59': 8, '60-79': 44, '80-100': 8}`
- Bias distribution: `{'bullish': 17, 'bearish': 43}`

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
