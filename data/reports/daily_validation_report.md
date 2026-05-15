# Daily Validation Report

Generated: 2026-05-15T16:00:24.120056+00:00
Probe mode: live
Primary recommendation: **INVESTIGATE_ERROR**
All recommendations: `INVESTIGATE_ERROR, READY_FOR_RISK_BLOCK_REVIEW, READY_FOR_SMART_MONEY_REVIEW`

## System Health

- Status: `warning`
- Master dataset last date: `2026-05-13`
- Rows: `532`
- Columns: `55`
- Stale dataset warning: `True`
- Errors: `[]`

## Endpoint Statuses

- /system-health: `ok=True` `http=200` `elapsed=8.631s`
- /learning-status: `ok=True` `http=200` `elapsed=0.411s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.003s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.415s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.007s`
- /shadow-buy-review: `ok=True` `http=200` `elapsed=0.085s`
- /technical-analysis: `ok=True` `http=200` `elapsed=0.063s`
- /support-resistance: `ok=True` `http=200` `elapsed=0.007s`
- /chart-patterns: `ok=True` `http=200` `elapsed=0.003s`
- /ta-forecast: `ok=True` `http=200` `elapsed=0.003s`
- /ta-backtest: `ok=True` `http=200` `elapsed=0.003s`
- /ai-technical-analyst: `ok=True` `http=200` `elapsed=0.007s`
- /ai-ta-performance: `ok=True` `http=200` `elapsed=0.002s`
- /ai-ta-backtest: `ok=True` `http=200` `elapsed=0.003s`
- /shadow-paper-test: `ok=True` `http=200` `elapsed=0.096s`
- /shadow-paper-trades: `ok=True` `http=200` `elapsed=0.005s`
- /shadow-buy-failure-diagnosis: `ok=True` `http=200` `elapsed=0.163s`
- /strict-resume-shadow-simulation: `ok=True` `http=200` `elapsed=0.159s`
- /report-file?path=data/reports/chatgpt_supervision_report.json: `ok=True` `http=200` `elapsed=0.003s`
- /reports: `ok=True` `http=200` `elapsed=0.076s`

## Learning Counts

- decisions_total: `266`
- claude_buy_count: `2`
- candidate_buy_count: `204`
- risk_blocked_candidates: `195`
- trades_executed: `1`
- shadow_buy_count: `217`
- shadow_smart_money_count: `181`

## Progress Targets

- Blocked BUY candidates: `195 / 30`
- Shadow BUYs: `217 / 100`
- Shadow Smart Money: `181 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `True`
- Shadow BUY review: `217 / 100` `SHADOW_BUY_STAYS_SHADOW`
- TA shadow progress: `76 / 50` ready_for_bonus=`False`
- AI TA shadow progress: `76 / 50` ready_for_bonus=`False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `198`
- Live paper scans total: `68`
- Last learning-only scan: `2026-05-15T15:00:15+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `198`
- Estimated learning API cost daily: `$0.176347`
- Estimated learning API cost monthly: `$5.29041`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `0.0`
- Estimated days to 50 Smart Money shadows: `0.0`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `195`
- BB squeeze: `{'count': 109, 'avg_return_1h': 0.0058, 'avg_return_4h': 0.051, 'avg_return_24h': 0.1897, 'blocked_winners_1h': 1, 'blocked_winners_4h': 4, 'blocked_winners_24h': 15, 'saved_losses_1h': 1, 'saved_losses_4h': 9, 'saved_losses_24h': 20, 'verdict': 'helping'}`

## Smart Money Performance

- Shadow count: `181`
- Ready for bonus: `True`
- Score distribution: `{'0-39': 3, '40-59': 38, '60-79': 162, '80-100': 30}`
- Bias distribution: `{'bullish': 132, 'bearish': 95, 'neutral': 6}`

## TA / AI TA Shadow Layers

- TA enabled: `True` shadow_only=`True`
- TA shadow count: `76`
- TA avg future return 4h: `-0.0032`
- AI TA enabled: `True` shadow_only=`True`
- AI TA calls total: `156`
- AI TA shadow count: `76`
- AI TA avg future return 4h: `-0.0032`
- AI TA invalid JSON count: `0`
- AI TA safety violations: should_trade=`0`, risk_engine=`0`

## Download Safety

- Download ZIP safe: `True`
- Secrets excluded: `True`
- Files checked: `72`
- Findings: `[]`

## Guardrails

- Trading logic unchanged.
- risk_engine.py unchanged.
- Trade Quality thresholds unchanged.
- Smart Money remains shadow-only until minimum sample size is reached.
- This report never recommends risk_engine changes before 30 blocked BUY candidates.
