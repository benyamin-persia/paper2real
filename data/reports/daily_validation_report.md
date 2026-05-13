# Daily Validation Report

Generated: 2026-05-13T22:00:20.170568+00:00
Primary recommendation: **READY_FOR_RISK_BLOCK_REVIEW**
All recommendations: `READY_FOR_RISK_BLOCK_REVIEW, READY_FOR_SMART_MONEY_REVIEW`

## System Health

- Status: `ok`
- Master dataset last date: `2026-05-13`
- Rows: `532`
- Columns: `55`
- Stale dataset warning: `False`
- Errors: `[]`

## Endpoint Statuses

- /system-health: `ok=True` `http=200` `elapsed=11.409s`
- /learning-status: `ok=True` `http=200` `elapsed=0.314s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.003s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.32s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.007s`
- /shadow-buy-review: `ok=True` `http=200` `elapsed=0.066s`
- /technical-analysis: `ok=True` `http=200` `elapsed=0.062s`
- /support-resistance: `ok=True` `http=200` `elapsed=0.006s`
- /chart-patterns: `ok=True` `http=200` `elapsed=0.002s`
- /ta-forecast: `ok=True` `http=200` `elapsed=0.003s`
- /ta-backtest: `ok=True` `http=200` `elapsed=0.003s`
- /ai-technical-analyst: `ok=True` `http=200` `elapsed=0.007s`
- /ai-ta-performance: `ok=True` `http=200` `elapsed=0.002s`
- /ai-ta-backtest: `ok=True` `http=200` `elapsed=0.003s`
- /reports: `ok=True` `http=200` `elapsed=0.051s`

## Learning Counts

- decisions_total: `220`
- claude_buy_count: `2`
- candidate_buy_count: `158`
- risk_blocked_candidates: `157`
- trades_executed: `0`
- shadow_buy_count: `179`
- shadow_smart_money_count: `147`

## Progress Targets

- Blocked BUY candidates: `157 / 30`
- Shadow BUYs: `179 / 100`
- Shadow Smart Money: `147 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `True`
- Shadow BUY review: `180 / 100` `SHADOW_BUY_STAYS_SHADOW`
- TA shadow progress: `59 / 50` ready_for_bonus=`False`
- AI TA shadow progress: `59 / 50` ready_for_bonus=`False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `157`
- Live paper scans total: `63`
- Last learning-only scan: `2026-05-13T21:00:11+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `157`
- Estimated learning API cost daily: `$0.178255`
- Estimated learning API cost monthly: `$5.34765`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `0.0`
- Estimated days to 50 Smart Money shadows: `0.0`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `158`
- BB squeeze: `{'count': 72, 'avg_return_1h': 0.0057, 'avg_return_4h': 0.0524, 'avg_return_24h': -0.2754, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 0, 'saved_losses_1h': 0, 'saved_losses_4h': 5, 'saved_losses_24h': 16, 'verdict': 'helping'}`

## Smart Money Performance

- Shadow count: `147`
- Ready for bonus: `True`
- Score distribution: `{'0-39': 3, '40-59': 36, '60-79': 123, '80-100': 25}`
- Bias distribution: `{'bullish': 113, 'bearish': 70, 'neutral': 4}`

## TA / AI TA Shadow Layers

- TA enabled: `True` shadow_only=`True`
- TA shadow count: `59`
- TA avg future return 4h: `-0.0678`
- AI TA enabled: `True` shadow_only=`True`
- AI TA calls total: `110`
- AI TA shadow count: `59`
- AI TA avg future return 4h: `-0.0678`
- AI TA invalid JSON count: `0`
- AI TA safety violations: should_trade=`0`, risk_engine=`0`

## Download Safety

- Download ZIP safe: `True`
- Secrets excluded: `True`
- Files checked: `69`
- Findings: `[]`

## Guardrails

- Trading logic unchanged.
- risk_engine.py unchanged.
- Trade Quality thresholds unchanged.
- Smart Money remains shadow-only until minimum sample size is reached.
- This report never recommends risk_engine changes before 30 blocked BUY candidates.
