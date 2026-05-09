# Daily Validation Report

Generated: 2026-05-09T04:00:19.225172+00:00
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

- /system-health: `ok=True` `http=200` `elapsed=11.421s`
- /learning-status: `ok=True` `http=200` `elapsed=0.069s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.002s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.078s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.022s`
- /reports: `ok=True` `http=200` `elapsed=0.039s`

## Learning Counts

- decisions_total: `87`
- claude_buy_count: `1`
- candidate_buy_count: `38`
- risk_blocked_candidates: `38`
- trades_executed: `0`
- shadow_buy_count: `47`
- shadow_smart_money_count: `46`

## Progress Targets

- Blocked BUY candidates: `38 / 30`
- Shadow BUYs: `47 / 100`
- Shadow Smart Money: `46 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `49`
- Live paper scans total: `38`
- Last learning-only scan: `2026-05-09T03:00:15+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `49`
- Estimated learning API cost daily: `$0.174782`
- Estimated learning API cost monthly: `$5.24346`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `3.21`
- Estimated days to 50 Smart Money shadows: `0.19`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `38`
- BB squeeze: `{'count': 32, 'avg_return_1h': 0.0115, 'avg_return_4h': 0.0611, 'avg_return_24h': -0.9254, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 0, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 8, 'verdict': 'neutral'}`

## Smart Money Performance

- Shadow count: `46`
- Ready for bonus: `False`
- Score distribution: `{'0-39': 0, '40-59': 8, '60-79': 38, '80-100': 8}`
- Bias distribution: `{'bullish': 12, 'bearish': 42}`

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
