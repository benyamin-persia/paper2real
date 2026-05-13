# Daily Validation Report

Generated: 2026-05-13T10:00:18.261309+00:00
Primary recommendation: **INVESTIGATE_ERROR**
All recommendations: `INVESTIGATE_ERROR, READY_FOR_RISK_BLOCK_REVIEW, READY_FOR_SMART_MONEY_REVIEW`

## System Health

- Status: `warning`
- Master dataset last date: `2026-05-11`
- Rows: `532`
- Columns: `55`
- Stale dataset warning: `True`
- Errors: `[]`

## Endpoint Statuses

- /system-health: `ok=True` `http=200` `elapsed=9.271s`
- /learning-status: `ok=True` `http=200` `elapsed=1.023s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.122s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.319s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.008s`
- /shadow-buy-review: `ok=True` `http=200` `elapsed=0.106s`
- /technical-analysis: `ok=True` `http=200` `elapsed=0.062s`
- /support-resistance: `ok=True` `http=200` `elapsed=0.007s`
- /chart-patterns: `ok=True` `http=200` `elapsed=0.002s`
- /ta-forecast: `ok=True` `http=200` `elapsed=0.003s`
- /ta-backtest: `ok=True` `http=200` `elapsed=0.003s`
- /ai-technical-analyst: `ok=True` `http=200` `elapsed=0.007s`
- /ai-ta-performance: `ok=True` `http=200` `elapsed=0.002s`
- /ai-ta-backtest: `ok=True` `http=200` `elapsed=0.002s`
- /reports: `ok=True` `http=200` `elapsed=0.023s`

## Learning Counts

- decisions_total: `204`
- claude_buy_count: `1`
- candidate_buy_count: `142`
- risk_blocked_candidates: `141`
- trades_executed: `0`
- shadow_buy_count: `163`
- shadow_smart_money_count: `133`

## Progress Targets

- Blocked BUY candidates: `141 / 30`
- Shadow BUYs: `163 / 100`
- Shadow Smart Money: `133 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `True`
- Shadow BUY review: `164 / 100` `SHADOW_BUY_READY_FOR_SMALL_TEST`
- TA shadow progress: `50 / 50` ready_for_bonus=`False`
- AI TA shadow progress: `50 / 50` ready_for_bonus=`False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `145`
- Live paper scans total: `59`
- Last learning-only scan: `2026-05-13T09:00:16+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `145`
- Estimated learning API cost daily: `$0.177933`
- Estimated learning API cost monthly: `$5.33799`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `0.0`
- Estimated days to 50 Smart Money shadows: `0.0`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `142`
- BB squeeze: `{'count': 62, 'avg_return_1h': 0.0585, 'avg_return_4h': 0.1863, 'avg_return_24h': -0.2084, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 1, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 13, 'verdict': 'neutral'}`

## Smart Money Performance

- Shadow count: `133`
- Ready for bonus: `True`
- Score distribution: `{'0-39': 3, '40-59': 34, '60-79': 111, '80-100': 23}`
- Bias distribution: `{'bullish': 112, 'bearish': 55, 'neutral': 4}`

## TA / AI TA Shadow Layers

- TA enabled: `True` shadow_only=`True`
- TA shadow count: `50`
- TA avg future return 4h: `-0.0292`
- AI TA enabled: `True` shadow_only=`True`
- AI TA calls total: `94`
- AI TA shadow count: `50`
- AI TA avg future return 4h: `-0.0292`
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
