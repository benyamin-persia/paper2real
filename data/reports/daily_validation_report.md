# Daily Validation Report

Generated: 2026-05-12T16:00:17.034746+00:00
Primary recommendation: **READY_FOR_RISK_BLOCK_REVIEW**
All recommendations: `READY_FOR_RISK_BLOCK_REVIEW, READY_FOR_SMART_MONEY_REVIEW`

## System Health

- Status: `ok`
- Master dataset last date: `2026-05-11`
- Rows: `532`
- Columns: `55`
- Stale dataset warning: `False`
- Errors: `[]`

## Endpoint Statuses

- /system-health: `ok=True` `http=200` `elapsed=9.488s`
- /learning-status: `ok=True` `http=200` `elapsed=0.5s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.003s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.272s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.006s`
- /shadow-buy-review: `ok=True` `http=200` `elapsed=0.421s`
- /technical-analysis: `ok=True` `http=200` `elapsed=0.062s`
- /support-resistance: `ok=True` `http=200` `elapsed=0.007s`
- /chart-patterns: `ok=True` `http=200` `elapsed=0.002s`
- /ta-forecast: `ok=True` `http=200` `elapsed=0.002s`
- /ta-backtest: `ok=True` `http=200` `elapsed=0.002s`
- /ai-technical-analyst: `ok=True` `http=200` `elapsed=0.007s`
- /ai-ta-performance: `ok=True` `http=200` `elapsed=0.002s`
- /ai-ta-backtest: `ok=True` `http=200` `elapsed=0.002s`
- /reports: `ok=True` `http=200` `elapsed=0.024s`

## Learning Counts

- decisions_total: `181`
- claude_buy_count: `1`
- candidate_buy_count: `122`
- risk_blocked_candidates: `121`
- trades_executed: `0`
- shadow_buy_count: `140`
- shadow_smart_money_count: `117`

## Progress Targets

- Blocked BUY candidates: `121 / 30`
- Shadow BUYs: `140 / 100`
- Shadow Smart Money: `117 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `True`
- Shadow BUY review: `141 / 100` `SHADOW_BUY_READY_FOR_SMALL_TEST`
- TA shadow progress: `40 / 50` ready_for_bonus=`False`
- AI TA shadow progress: `40 / 50` ready_for_bonus=`False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `127`
- Live paper scans total: `54`
- Last learning-only scan: `2026-05-12T15:00:11+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `127`
- Estimated learning API cost daily: `$0.176118`
- Estimated learning API cost monthly: `$5.28354`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `0.0`
- Estimated days to 50 Smart Money shadows: `0.0`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `122`
- BB squeeze: `{'count': 59, 'avg_return_1h': 0.0738, 'avg_return_4h': 0.1765, 'avg_return_24h': -0.1079, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 1, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 10, 'verdict': 'neutral'}`

## Smart Money Performance

- Shadow count: `117`
- Ready for bonus: `True`
- Score distribution: `{'0-39': 3, '40-59': 27, '60-79': 95, '80-100': 23}`
- Bias distribution: `{'bullish': 97, 'bearish': 47, 'neutral': 4}`

## TA / AI TA Shadow Layers

- TA enabled: `True` shadow_only=`True`
- TA shadow count: `40`
- TA avg future return 4h: `0.0925`
- AI TA enabled: `True` shadow_only=`True`
- AI TA calls total: `71`
- AI TA shadow count: `40`
- AI TA avg future return 4h: `0.0925`
- AI TA invalid JSON count: `0`
- AI TA safety violations: should_trade=`0`, risk_engine=`0`

## Download Safety

- Download ZIP safe: `True`
- Secrets excluded: `True`
- Files checked: `63`
- Findings: `[]`

## Guardrails

- Trading logic unchanged.
- risk_engine.py unchanged.
- Trade Quality thresholds unchanged.
- Smart Money remains shadow-only until minimum sample size is reached.
- This report never recommends risk_engine changes before 30 blocked BUY candidates.
