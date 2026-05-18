# Daily Validation Report

Generated: 2026-05-18T04:00:23.296707+00:00
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

- /system-health: `ok=True` `http=200` `elapsed=1.199s`
- /learning-status: `ok=True` `http=200` `elapsed=1.536s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.003s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.512s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.092s`
- /shadow-buy-review: `ok=True` `http=200` `elapsed=0.141s`
- /technical-analysis: `ok=True` `http=200` `elapsed=0.054s`
- /support-resistance: `ok=True` `http=200` `elapsed=0.008s`
- /chart-patterns: `ok=True` `http=200` `elapsed=0.003s`
- /ta-forecast: `ok=True` `http=200` `elapsed=0.002s`
- /ta-backtest: `ok=True` `http=200` `elapsed=0.002s`
- /ai-technical-analyst: `ok=True` `http=200` `elapsed=0.005s`
- /ai-ta-performance: `ok=True` `http=200` `elapsed=0.002s`
- /ai-ta-backtest: `ok=True` `http=200` `elapsed=0.002s`
- /shadow-paper-test: `ok=True` `http=200` `elapsed=0.153s`
- /shadow-paper-trades: `ok=True` `http=200` `elapsed=0.006s`
- /shadow-buy-failure-diagnosis: `ok=True` `http=200` `elapsed=0.469s`
- /strict-resume-shadow-simulation: `ok=True` `http=200` `elapsed=0.208s`
- /report-file?path=data/reports/chatgpt_supervision_report.json: `ok=True` `http=200` `elapsed=0.003s`
- /reports: `ok=True` `http=200` `elapsed=0.108s`

## Learning Counts

- decisions_total: `330`
- claude_buy_count: `2`
- candidate_buy_count: `209`
- risk_blocked_candidates: `198`
- trades_executed: `1`
- real_trades_executed: `0`
- paper_trades: `1`
- open_trades: `0`
- shadow_buy_count: `279`
- shadow_smart_money_count: `232`

## Execution Incident / Freeze

- Execution frozen: `True`
- Latest incident report: `data/reports/trade_execution_incident_20260518.json`
- Latest incident time: `None`
- Latest incident trade type: `shadow-paper`
- Latest incident recommendation: `None`
- Runtime hard block active: `True`
- Runtime hard block reason: `master_dataset.csv is 105.38h old; max allowed is 36.00h; supervision_verdict=DO_NOT_RESUME_TRADING_OR_PAPER_TEST`
- Paper test entries enabled: `False`
- Open shadow-paper trades: `0`
- Stale dataset hard block status: `not_a_hard_block_at_incident_time`
- Critical alert hard block status: `not_confirmed_hard_block_at_incident_time`

## Progress Targets

- Blocked BUY candidates: `198 / 30`
- Shadow BUYs: `279 / 100`
- Shadow Smart Money: `232 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `True`
- Shadow BUY review: `280 / 100` `SHADOW_BUY_STAYS_SHADOW`
- TA shadow progress: `105 / 50` ready_for_bonus=`False`
- AI TA shadow progress: `105 / 50` ready_for_bonus=`False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `248`
- Live paper scans total: `82`
- Last learning-only scan: `2026-05-18T03:00:12+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `248`
- Estimated learning API cost daily: `$0.174096`
- Estimated learning API cost monthly: `$5.22288`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `0.0`
- Estimated days to 50 Smart Money shadows: `0.0`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `199`
- BB squeeze: `{'count': 112, 'avg_return_1h': -0.0237, 'avg_return_4h': 0.0156, 'avg_return_24h': -0.3697, 'blocked_winners_1h': 1, 'blocked_winners_4h': 5, 'blocked_winners_24h': 15, 'saved_losses_1h': 3, 'saved_losses_4h': 10, 'saved_losses_24h': 41, 'verdict': 'helping'}`

## Smart Money Performance

- Shadow count: `232`
- Ready for bonus: `True`
- Score distribution: `{'0-39': 3, '40-59': 49, '60-79': 211, '80-100': 34}`
- Bias distribution: `{'bullish': 143, 'bearish': 148, 'neutral': 6}`

## TA / AI TA Shadow Layers

- TA enabled: `True` shadow_only=`True`
- TA shadow count: `105`
- TA avg future return 4h: `0.0598`
- AI TA enabled: `True` shadow_only=`True`
- AI TA calls total: `220`
- AI TA shadow count: `105`
- AI TA avg future return 4h: `0.0598`
- AI TA invalid JSON count: `0`
- AI TA safety violations: should_trade=`0`, risk_engine=`0`

## Download Safety

- Download ZIP safe: `True`
- Secrets excluded: `True`
- Files checked: `76`
- Findings: `[]`

## Guardrails

- Trading logic unchanged.
- risk_engine.py unchanged.
- Trade Quality thresholds unchanged.
- Smart Money remains shadow-only until minimum sample size is reached.
- This report never recommends risk_engine changes before 30 blocked BUY candidates.
