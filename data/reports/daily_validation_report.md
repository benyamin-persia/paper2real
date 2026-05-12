# Daily Validation Report

Generated: 2026-05-12T10:00:23.461400+00:00
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

- /system-health: `ok=True` `http=200` `elapsed=7.787s`
- /learning-status: `ok=True` `http=200` `elapsed=0.195s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=8.025s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.327s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.006s`
- /shadow-buy-review: `ok=True` `http=200` `elapsed=0.822s`
- /technical-analysis: `ok=True` `http=200` `elapsed=0.062s`
- /support-resistance: `ok=True` `http=200` `elapsed=0.007s`
- /chart-patterns: `ok=True` `http=200` `elapsed=0.002s`
- /ta-forecast: `ok=True` `http=200` `elapsed=0.002s`
- /ta-backtest: `ok=True` `http=200` `elapsed=0.002s`
- /ai-technical-analyst: `ok=True` `http=200` `elapsed=0.007s`
- /ai-ta-performance: `ok=True` `http=200` `elapsed=0.002s`
- /ai-ta-backtest: `ok=True` `http=200` `elapsed=0.002s`
- /reports: `ok=True` `http=200` `elapsed=0.022s`

## Learning Counts

- decisions_total: `174`
- claude_buy_count: `1`
- candidate_buy_count: `116`
- risk_blocked_candidates: `115`
- trades_executed: `0`
- shadow_buy_count: `133`
- shadow_smart_money_count: `115`

## Progress Targets

- Blocked BUY candidates: `115 / 30`
- Shadow BUYs: `133 / 100`
- Shadow Smart Money: `115 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `True`
- Shadow BUY review: `134 / 100` `SHADOW_BUY_READY_FOR_SMALL_TEST`
- TA shadow progress: `35 / 50` ready_for_bonus=`False`
- AI TA shadow progress: `35 / 50` ready_for_bonus=`False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `121`
- Live paper scans total: `53`
- Last learning-only scan: `2026-05-12T09:00:16+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `121`
- Estimated learning API cost daily: `$0.175576`
- Estimated learning API cost monthly: `$5.26728`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `0.0`
- Estimated days to 50 Smart Money shadows: `0.0`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `116`
- BB squeeze: `{'count': 56, 'avg_return_1h': 0.0757, 'avg_return_4h': 0.1894, 'avg_return_24h': -0.0279, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 1, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 9, 'verdict': 'neutral'}`

## Smart Money Performance

- Shadow count: `115`
- Ready for bonus: `True`
- Score distribution: `{'0-39': 2, '40-59': 23, '60-79': 93, '80-100': 23}`
- Bias distribution: `{'bullish': 94, 'bearish': 44, 'neutral': 3}`

## TA / AI TA Shadow Layers

- TA enabled: `True` shadow_only=`True`
- TA shadow count: `35`
- TA avg future return 4h: `0.0643`
- AI TA enabled: `True` shadow_only=`True`
- AI TA calls total: `64`
- AI TA shadow count: `35`
- AI TA avg future return 4h: `0.0643`
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
