# Daily Validation Report

Generated: 2026-05-10T16:01:04.477416+00:00
Primary recommendation: **READY_FOR_RISK_BLOCK_REVIEW**
All recommendations: `COLLECT_MORE_DATA, READY_FOR_RISK_BLOCK_REVIEW, READY_FOR_SMART_MONEY_REVIEW`

## System Health

- Status: `ok`
- Master dataset last date: `2026-05-10`
- Rows: `531`
- Columns: `55`
- Stale dataset warning: `False`
- Errors: `[]`

## Endpoint Statuses

- /system-health: `ok=True` `http=200` `elapsed=49.476s`
- /learning-status: `ok=True` `http=200` `elapsed=0.304s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.293s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.334s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.535s`
- /shadow-buy-review: `ok=True` `http=200` `elapsed=0.054s`
- /technical-analysis: `ok=True` `http=200` `elapsed=0.524s`
- /support-resistance: `ok=True` `http=200` `elapsed=0.069s`
- /chart-patterns: `ok=True` `http=200` `elapsed=0.01s`
- /ta-forecast: `ok=True` `http=200` `elapsed=0.333s`
- /ta-backtest: `ok=True` `http=200` `elapsed=0.048s`
- /ai-technical-analyst: `ok=True` `http=200` `elapsed=0.015s`
- /ai-ta-performance: `ok=True` `http=200` `elapsed=0.007s`
- /ai-ta-backtest: `ok=True` `http=200` `elapsed=0.003s`
- /reports: `ok=True` `http=200` `elapsed=0.037s`

## Learning Counts

- decisions_total: `128`
- claude_buy_count: `1`
- candidate_buy_count: `76`
- risk_blocked_candidates: `76`
- trades_executed: `0`
- shadow_buy_count: `88`
- shadow_smart_money_count: `87`

## Progress Targets

- Blocked BUY candidates: `76 / 30`
- Shadow BUYs: `88 / 100`
- Shadow Smart Money: `87 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `True`
- Shadow BUY review: `72 / 100` `COLLECT_MORE_DATA`
- TA shadow progress: `9 / 50` ready_for_bonus=`False`
- AI TA shadow progress: `9 / 50` ready_for_bonus=`False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `86`
- Live paper scans total: `42`
- Last learning-only scan: `2026-05-10T15:00:16+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `86`
- Estimated learning API cost daily: `$0.179228`
- Estimated learning API cost monthly: `$5.37684`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `0.6`
- Estimated days to 50 Smart Money shadows: `0.0`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `76`
- BB squeeze: `{'count': 45, 'avg_return_1h': -0.0034, 'avg_return_4h': 0.0767, 'avg_return_24h': -0.1622, 'blocked_winners_1h': 0, 'blocked_winners_4h': 0, 'blocked_winners_24h': 0, 'saved_losses_1h': 0, 'saved_losses_4h': 0, 'saved_losses_24h': 9, 'verdict': 'neutral'}`

## Smart Money Performance

- Shadow count: `87`
- Ready for bonus: `True`
- Score distribution: `{'0-39': 0, '40-59': 8, '60-79': 69, '80-100': 18}`
- Bias distribution: `{'bullish': 52, 'bearish': 43}`

## TA / AI TA Shadow Layers

- TA enabled: `True` shadow_only=`True`
- TA shadow count: `9`
- TA avg future return 4h: `0.0779`
- AI TA enabled: `True` shadow_only=`True`
- AI TA calls total: `18`
- AI TA shadow count: `9`
- AI TA avg future return 4h: `0.0779`
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
