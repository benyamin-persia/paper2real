# Daily Validation Report

Generated: 2026-05-07T16:00:40.752753+00:00
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

- /system-health: `ok=True` `http=200` `elapsed=18.708s`
- /learning-status: `ok=True` `http=200` `elapsed=0.127s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.017s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.119s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.357s`
- /reports: `ok=True` `http=200` `elapsed=0.043s`

## Learning Counts

- decisions_total: `51`
- claude_buy_count: `1`
- candidate_buy_count: `18`
- risk_blocked_candidates: `18`
- trades_executed: `0`
- shadow_buy_count: `24`
- shadow_smart_money_count: `18`

## Progress Targets

- Blocked BUY candidates: `18 / 30`
- Shadow BUYs: `24 / 100`
- Shadow Smart Money: `18 / 50`
- Ready for risk block review: `False`
- Ready for Smart Money review: `False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `13`
- Live paper scans total: `38`
- Last learning-only scan: `2026-05-07T15:00:21+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `13`
- Estimated learning API cost daily: `$0.149838`
- Estimated learning API cost monthly: `$4.49514`
- Estimated days to 30 blocked BUY candidates: `0.85`
- Estimated days to 100 shadow BUYs: `3.78`
- Estimated days to 50 Smart Money shadows: `1.23`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `18`
- BB squeeze: `{'count': 12, 'avg_return_1h': -0.0247, 'avg_return_4h': 0.0464, 'avg_return_24h': -0.3417, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 0, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 0, 'verdict': 'not_enough_data'}`

## Smart Money Performance

- Shadow count: `18`
- Ready for bonus: `False`
- Score distribution: `{'0-39': 0, '40-59': 0, '60-79': 13, '80-100': 5}`
- Bias distribution: `{'bullish': 5, 'bearish': 13}`

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
