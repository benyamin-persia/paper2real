# Trade Execution Incident 2026-05-15

Generated: `2026-05-15T20:54:16Z`
Incident time UTC: `2026-05-15T14:35:14Z`
Trade ID: `1`
Decision ID: `265`
Trade type: `normal_paper_trade`
Real order sent: `false`
Paper order: `true`
Entry price: `79039.0`
Position USD: `3000.0`
Risk blocker: `none`
Stale dataset age hours: `44.0`
Critical alerts active: `true`
Exchange risk active: `true`
Structured exchange risk seen by risk engine: `false`
Supervision verdict at last report: `DO_NOT_RESUME_TRADING_OR_PAPER_TEST`
Execution frozen: `true`
Recommended action: `BUG_FIX_REQUIRED_BEFORE_RESUME`

## Current Position

- Open trades: `1`
- Open trade IDs: `[1]`
- Cash balance USD: `7000.0`
- BTC held: `0.03795595`
- Current BTC price: `79017.9`
- Unrealized PnL USD: `-0.8`

## Why Execution Was Allowed

- Trade Quality produced candidate_action=BUY and final_action=BUY at the scheduled scan.
- The stale master dataset condition was recorded as a freshness warning, not a hard risk-engine blocker.
- The THORChain/BTC_DIRECT evidence was present in Twitter/playwright alert context and DB events, but events.json did not expose exchange_hack_alert/stablecoin_depeg/has_critical to risk_engine.py at execution time.
- The latest supervision verdict was reporting/audit evidence only and was not wired as a runtime execution gate.
- At execution time MAX_OPEN_TRADES allowed entries; runtime freeze was applied after discovery by setting MAX_OPEN_TRADES=0 and disabling Trade Quality BUY proposals/shadow paper entries.

## Safety Failure Points

- `stale_dataset_warning_not_hard_blocking`
- `twitter_critical_alert_not_mapped_to_risk_engine_exchange_blocker`
- `supervision_verdict_not_runtime_execution_gate`
- `paper_execution_allowed_while_expected_paused`

## Freeze Controls

- MAX_OPEN_TRADES: `0`
- TRADE_QUALITY_CAN_PROPOSE_BUY: `false`
- SHADOW_BUY_PAPER_TEST_ENABLED: `false`
- LEARNING_ONLY_SCAN_EXECUTES_TRADES: `false`
- EXECUTION_FREEZE: `true`
