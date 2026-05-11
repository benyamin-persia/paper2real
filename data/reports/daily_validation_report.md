# Daily Validation Report

Generated: 2026-05-11T10:00:14.259391+00:00
Primary recommendation: **READY_FOR_RISK_BLOCK_REVIEW**
All recommendations: `READY_FOR_RISK_BLOCK_REVIEW, READY_FOR_SMART_MONEY_REVIEW`

## System Health

- Status: `ok`
- Master dataset last date: `2026-05-10`
- Rows: `531`
- Columns: `55`
- Stale dataset warning: `False`
- Errors: `[]`

## Endpoint Statuses

- /system-health: `ok=True` `http=200` `elapsed=9.705s`
- /learning-status: `ok=True` `http=200` `elapsed=0.182s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.002s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.228s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.006s`
- /shadow-buy-review: `ok=True` `http=200` `elapsed=0.002s`
- /technical-analysis: `ok=True` `http=200` `elapsed=0.033s`
- /support-resistance: `ok=True` `http=200` `elapsed=0.005s`
- /chart-patterns: `ok=True` `http=200` `elapsed=0.002s`
- /ta-forecast: `ok=True` `http=200` `elapsed=0.002s`
- /ta-backtest: `ok=True` `http=200` `elapsed=0.002s`
- /ai-technical-analyst: `ok=True` `http=200` `elapsed=0.005s`
- /ai-ta-performance: `ok=True` `http=200` `elapsed=0.002s`
- /ai-ta-backtest: `ok=True` `http=200` `elapsed=0.002s`
- /reports: `ok=True` `http=200` `elapsed=0.015s`

## Learning Counts

- decisions_total: `142`
- claude_buy_count: `1`
- candidate_buy_count: `88`
- risk_blocked_candidates: `88`
- trades_executed: `0`
- shadow_buy_count: `102`
- shadow_smart_money_count: `98`

## Progress Targets

- Blocked BUY candidates: `88 / 30`
- Shadow BUYs: `102 / 100`
- Shadow Smart Money: `98 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `True`
- Shadow BUY review: `72 / 100` `COLLECT_MORE_DATA`
- TA shadow progress: `15 / 50` ready_for_bonus=`False`
- AI TA shadow progress: `15 / 50` ready_for_bonus=`False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `96`
- Live paper scans total: `46`
- Last learning-only scan: `2026-05-11T09:00:11+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `96`
- Estimated learning API cost daily: `$0.175805`
- Estimated learning API cost monthly: `$5.27415`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `0.0`
- Estimated days to 50 Smart Money shadows: `0.0`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `88`
- BB squeeze: `{'count': 47, 'avg_return_1h': 0.0362, 'avg_return_4h': 0.1233, 'avg_return_24h': -0.1034, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 1, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 9, 'verdict': 'neutral'}`

## Smart Money Performance

- Shadow count: `98`
- Ready for bonus: `True`
- Score distribution: `{'0-39': 0, '40-59': 11, '60-79': 80, '80-100': 18}`
- Bias distribution: `{'bullish': 65, 'bearish': 44}`

## TA / AI TA Shadow Layers

- TA enabled: `True` shadow_only=`True`
- TA shadow count: `15`
- TA avg future return 4h: `0.0724`
- AI TA enabled: `True` shadow_only=`True`
- AI TA calls total: `32`
- AI TA shadow count: `15`
- AI TA avg future return 4h: `0.0724`
- AI TA invalid JSON count: `0`
- AI TA safety violations: should_trade=`0`, risk_engine=`0`

## Download Safety

- Download ZIP safe: `True`
- Secrets excluded: `True`
- Files checked: `61`
- Findings: `[]`

## Guardrails

- Trading logic unchanged.
- risk_engine.py unchanged.
- Trade Quality thresholds unchanged.
- Smart Money remains shadow-only until minimum sample size is reached.
- This report never recommends risk_engine changes before 30 blocked BUY candidates.
