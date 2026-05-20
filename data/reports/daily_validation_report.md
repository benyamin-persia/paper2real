# Daily Validation Report

Generated: 2026-05-20T04:00:22.122846+00:00
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

- /system-health: `ok=True` `http=200` `elapsed=6.394s`
- /learning-status: `ok=True` `http=200` `elapsed=0.526s`
- /risk-block-performance: `ok=True` `http=200` `elapsed=0.003s`
- /shadow-performance: `ok=True` `http=200` `elapsed=0.484s`
- /smart-money-backtest: `ok=True` `http=200` `elapsed=0.007s`
- /shadow-buy-review: `ok=True` `http=200` `elapsed=0.163s`
- /technical-analysis: `ok=True` `http=200` `elapsed=0.061s`
- /support-resistance: `ok=True` `http=200` `elapsed=0.007s`
- /chart-patterns: `ok=True` `http=200` `elapsed=0.002s`
- /ta-forecast: `ok=True` `http=200` `elapsed=0.002s`
- /ta-backtest: `ok=True` `http=200` `elapsed=0.002s`
- /ai-technical-analyst: `ok=True` `http=200` `elapsed=0.007s`
- /ai-ta-performance: `ok=True` `http=200` `elapsed=0.002s`
- /ai-ta-backtest: `ok=True` `http=200` `elapsed=0.003s`
- /shadow-paper-test: `ok=True` `http=200` `elapsed=0.205s`
- /shadow-paper-trades: `ok=True` `http=200` `elapsed=0.005s`
- /shadow-buy-failure-diagnosis: `ok=True` `http=200` `elapsed=0.284s`
- /strict-resume-shadow-simulation: `ok=True` `http=200` `elapsed=0.258s`
- /report-file?path=data/reports/chatgpt_supervision_report.json: `ok=True` `http=200` `elapsed=0.003s`
- /reports: `ok=True` `http=200` `elapsed=0.081s`

## Learning Counts

- decisions_total: `390`
- claude_buy_count: `5`
- candidate_buy_count: `212`
- risk_blocked_candidates: `201`
- trades_executed: `1`
- real_trades_executed: `0`
- paper_trades: `1`
- open_trades: `0`
- shadow_buy_count: `339`
- shadow_smart_money_count: `278`

## Execution Incident / Freeze

- Execution frozen: `True`
- Latest incident report: `data/reports/trade_execution_incident_20260519.json`
- Latest incident time: `None`
- Latest incident trade type: `shadow-paper`
- Latest incident recommendation: `None`
- Runtime hard block active: `True`
- Runtime hard block reason: `master_dataset.csv is 153.38h old; max allowed is 36.00h; supervision_verdict=DO_NOT_RESUME_TRADING_OR_PAPER_TEST`
- Paper test entries enabled: `False`
- Open shadow-paper trades: `0`
- Stale dataset hard block status: `not_a_hard_block_at_incident_time`
- Critical alert hard block status: `not_confirmed_hard_block_at_incident_time`

## Progress Targets

- Blocked BUY candidates: `201 / 30`
- Shadow BUYs: `339 / 100`
- Shadow Smart Money: `278 / 50`
- Ready for risk block review: `True`
- Ready for Smart Money review: `True`
- Shadow BUY review: `340 / 100` `SHADOW_BUY_STAYS_SHADOW`
- TA shadow progress: `137 / 50` ready_for_bonus=`False`
- AI TA shadow progress: `137 / 50` ready_for_bonus=`False`

## Learning-Only Scans

- Enabled: `True`
- Interval minutes: `60`
- Learning-only scans total: `296`
- Live paper scans total: `94`
- Last learning-only scan: `2026-05-20T03:00:11+00:00`
- Duplicate scans suppressed: `4`
- Claude calls from learning scans: `296`
- Estimated learning API cost daily: `$0.172222`
- Estimated learning API cost monthly: `$5.16666`
- Estimated days to 30 blocked BUY candidates: `0.0`
- Estimated days to 100 shadow BUYs: `0.0`
- Estimated days to 50 Smart Money shadows: `0.0`
- Learning-only scans do not execute trades or mutate portfolio balance.

## Risk Block Performance

- Total blocked candidates: `201`
- BB squeeze: `{'count': 112, 'avg_return_1h': -0.0288, 'avg_return_4h': 0.0153, 'avg_return_24h': -0.3743, 'blocked_winners_1h': 1, 'blocked_winners_4h': 5, 'blocked_winners_24h': 15, 'saved_losses_1h': 3, 'saved_losses_4h': 10, 'saved_losses_24h': 42, 'verdict': 'helping'}`

## Smart Money Performance

- Shadow count: `278`
- Ready for bonus: `True`
- Score distribution: `{'0-39': 3, '40-59': 63, '60-79': 257, '80-100': 34}`
- Bias distribution: `{'bullish': 156, 'bearish': 195, 'neutral': 6}`

## TA / AI TA Shadow Layers

- TA enabled: `True` shadow_only=`True`
- TA shadow count: `137`
- TA avg future return 4h: `-0.0079`
- AI TA enabled: `True` shadow_only=`True`
- AI TA calls total: `280`
- AI TA shadow count: `137`
- AI TA avg future return 4h: `-0.0079`
- AI TA invalid JSON count: `0`
- AI TA safety violations: should_trade=`0`, risk_engine=`0`

## Download Safety

- Download ZIP safe: `True`
- Secrets excluded: `True`
- Files checked: `78`
- Findings: `[]`

## Guardrails

- Trading logic unchanged.
- risk_engine.py unchanged.
- Trade Quality thresholds unchanged.
- Smart Money remains shadow-only until minimum sample size is reached.
- This report never recommends risk_engine changes before 30 blocked BUY candidates.
