# Daily Validation Report

Generated: 2026-05-15T21:50:49.153474+00:00
Probe mode: skipped
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

- decisions_total: `275`
- claude_buy_count: `2`
- candidate_buy_count: `209`
- risk_blocked_candidates: `198`
- trades_executed: `1`
- real_trades_executed: `0`
- paper_trades: `1`
- open_trades: `1`
- shadow_buy_count: `224`
- shadow_smart_money_count: `188`

## Execution Incident / Freeze

- Execution frozen: `True`
- Latest incident report: `data/reports/trade_execution_incident_20260515.json`
- Latest incident time: `2026-05-15T14:35:14+00:00`
- Latest incident trade type: `normal_paper_trade`
- Latest incident recommendation: `BUG_FIX_REQUIRED_BEFORE_RESUME`
- Stale dataset hard block status: `not_a_hard_block_at_incident_time`
- Critical alert hard block status: `twitter_alert_not_mapped_to_events_json_hard_block_at_incident_time`

## Progress Targets

- Blocked BUY candidates: `198 / 30`
- Shadow BUYs: `224 / 100`
- Shadow Smart Money: `188 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `True`
- Shadow BUY review: `224 / 100` `SHADOW_BUY_STAYS_SHADOW`
- TA shadow progress: `80 / 50` ready_for_bonus=`False`
- AI TA shadow progress: `80 / 50` ready_for_bonus=`False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `204`
- Live paper scans total: `71`
- Last learning-only scan: `2026-05-15T21:00:23+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `204`
- Estimated learning API cost daily: `$0.175442`
- Estimated learning API cost monthly: `$5.26326`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `0.0`
- Estimated days to 50 Smart Money shadows: `0.0`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `198`
- BB squeeze: `{'count': 112, 'avg_return_1h': 0.002, 'avg_return_4h': 0.0227, 'avg_return_24h': 0.1244, 'blocked_winners_1h': 1, 'blocked_winners_4h': 4, 'blocked_winners_24h': 15, 'saved_losses_1h': 1, 'saved_losses_4h': 11, 'saved_losses_24h': 22, 'verdict': 'helping'}`

## Smart Money Performance

- Shadow count: `188`
- Ready for bonus: `True`
- Score distribution: `{'0-39': 3, '40-59': 38, '60-79': 171, '80-100': 30}`
- Bias distribution: `{'bullish': 132, 'bearish': 104, 'neutral': 6}`

## TA / AI TA Shadow Layers

- TA enabled: `True` shadow_only=`True`
- TA shadow count: `80`
- TA avg future return 4h: `0.0365`
- AI TA enabled: `True` shadow_only=`True`
- AI TA calls total: `165`
- AI TA shadow count: `80`
- AI TA avg future return 4h: `0.0365`
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
