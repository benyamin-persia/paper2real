# Daily Validation Report

Generated: 2026-05-15T06:35:09.925701+00:00
Probe mode: skipped
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

- /system-health: `ok=True` `http=200` `elapsed=0.0s`
- /learning-status: `ok=True` `http=200` `elapsed=0.0s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.0s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.0s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.0s`
- /shadow-buy-review: `ok=True` `http=200` `elapsed=0.0s`
- /technical-analysis: `ok=True` `http=200` `elapsed=0.0s`
- /support-resistance: `ok=True` `http=200` `elapsed=0.0s`
- /chart-patterns: `ok=True` `http=200` `elapsed=0.0s`
- /ta-forecast: `ok=True` `http=200` `elapsed=0.0s`
- /ta-backtest: `ok=True` `http=200` `elapsed=0.0s`
- /ai-technical-analyst: `ok=True` `http=200` `elapsed=0.0s`
- /ai-ta-performance: `ok=True` `http=200` `elapsed=0.0s`
- /ai-ta-backtest: `ok=True` `http=200` `elapsed=0.0s`
- /shadow-paper-test: `ok=True` `http=200` `elapsed=0.0s`
- /shadow-paper-trades: `ok=True` `http=200` `elapsed=0.0s`
- /shadow-buy-failure-diagnosis: `ok=True` `http=200` `elapsed=0.0s`
- /strict-resume-shadow-simulation: `ok=True` `http=200` `elapsed=0.0s`
- /report-file?path=data/reports/chatgpt_supervision_report.json: `ok=True` `http=200` `elapsed=0.0s`
- /reports: `ok=True` `http=200` `elapsed=0.0s`

## Learning Counts

- decisions_total: `255`
- claude_buy_count: `2`
- candidate_buy_count: `193`
- risk_blocked_candidates: `187`
- trades_executed: `0`
- shadow_buy_count: `209`
- shadow_smart_money_count: `175`

## Progress Targets

- Blocked BUY candidates: `187 / 30`
- Shadow BUYs: `209 / 100`
- Shadow Smart Money: `175 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `True`
- Shadow BUY review: `209 / 100` `SHADOW_BUY_STAYS_SHADOW`
- TA shadow progress: `72 / 50` ready_for_bonus=`False`
- AI TA shadow progress: `72 / 50` ready_for_bonus=`False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `189`
- Live paper scans total: `66`
- Last learning-only scan: `2026-05-15T06:00:12+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `189`
- Estimated learning API cost daily: `$0.175459`
- Estimated learning API cost monthly: `$5.26377`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `0.0`
- Estimated days to 50 Smart Money shadows: `0.0`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `187`
- BB squeeze: `{'count': 101, 'avg_return_1h': 0.0252, 'avg_return_4h': 0.1359, 'avg_return_24h': 0.1132, 'blocked_winners_1h': 1, 'blocked_winners_4h': 4, 'blocked_winners_24h': 14, 'saved_losses_1h': 0, 'saved_losses_4h': 6, 'saved_losses_24h': 20, 'verdict': 'helping'}`

## Smart Money Performance

- Shadow count: `175`
- Ready for bonus: `True`
- Score distribution: `{'0-39': 3, '40-59': 38, '60-79': 152, '80-100': 29}`
- Bias distribution: `{'bullish': 129, 'bearish': 89, 'neutral': 4}`

## TA / AI TA Shadow Layers

- TA enabled: `True` shadow_only=`True`
- TA shadow count: `72`
- TA avg future return 4h: `-0.0076`
- AI TA enabled: `True` shadow_only=`True`
- AI TA calls total: `145`
- AI TA shadow count: `72`
- AI TA avg future return 4h: `-0.0076`
- AI TA invalid JSON count: `0`
- AI TA safety violations: should_trade=`0`, risk_engine=`0`

## Download Safety

- Download ZIP safe: `True`
- Secrets excluded: `True`
- Files checked: `0`
- Findings: `[]`

## Guardrails

- Trading logic unchanged.
- risk_engine.py unchanged.
- Trade Quality thresholds unchanged.
- Smart Money remains shadow-only until minimum sample size is reached.
- This report never recommends risk_engine changes before 30 blocked BUY candidates.
