# Shadow Paper Resume Plan

- Generated at: `2026-05-17T04:00:18.357241+00:00`
- Current status: `Paper Test Paused`
- Why paused: `Supervision forbids trading: DO_NOT_RESUME_TRADING_OR_PAPER_TEST`
- Recommendation: `KEEP_PAUSED_AND_COLLECT_SHADOW, DO_NOT_RESUME_YET`

## Diagnosis Summary

```json
{
  "source_report": "data/reports/shadow_buy_failure_diagnosis.json",
  "recommended_next_action": [
    "KEEP_PAPER_TEST_PAUSED",
    "REQUIRE_ALL_CONFIRMATION_NEUTRAL_OR_BETTER",
    "REQUIRE_TA_NOT_BEARISH",
    "REQUIRE_AI_TA_NOT_BEARISH",
    "REQUIRE_SMART_MONEY_CONFIRMATION",
    "CHANGE_STOP_TAKE_PROFIT_REVIEW_ONLY",
    "COLLECT_MORE_SHADOW_ONLY",
    "DO_NOT_RESUME"
  ],
  "paper_trade_count": 4,
  "closed_paper_trades": 4,
  "paper_test_win_rate": 25.0,
  "paper_test_total_pnl_usd": -0.4921,
  "bb_squeeze_override_trades": 4,
  "entries_against_ta": 3,
  "entries_against_ai_ta": 2,
  "failure_reasons": {
    "stop_loss_too_tight": true,
    "take_profit_too_far": true,
    "entries_were_against_ta_or_ai_ta": true,
    "bb_squeeze_overrides_are_weak": true,
    "four_hour_horizon_mismatches_stop_loss": true,
    "exchange_or_news_regime_changed": true,
    "sample_became_worse_after_more_data": true,
    "any_bearish_alignment_loses": true
  },
  "best_condition": {
    "section": "market_condition",
    "filter": "bearish_sweep",
    "avg_return_4h": 0.1586,
    "win_rate_4h": 65.62,
    "count": 32
  },
  "worst_condition": {
    "section": "smart_money_bias",
    "filter": "neutral",
    "avg_return_4h": -0.2471,
    "win_rate_4h": 20.0,
    "count": 15
  }
}
```

## Proposed Filters

- smart_money_not_bearish: `True`
- ta_not_bearish: `True`
- ai_ta_not_bearish: `True`
- at_least_one_bullish_confirmation: `True`
- bb_squeeze_override_disabled: `True`
- bearish_sweep_confirmation_optional: `True`
- bearish_sweep_confirmation_active: `False`

## Expected Effect

- Reject staged resume candidates when Smart Money, TA, or AI TA are bearish.
- Require at least one bullish confirmation so high Trade Quality alone is not enough.
- Keep bb_squeeze overrides disabled because the first four paper trades all came from that path and total PnL is negative.
- Track bearish_sweep confirmation as optional evidence only until more shadow-only samples exist.

## Risks

- Sample size is still small, especially for bearish_sweep and high Trade Quality buckets.
- Making filters too strict could remove future valid recovery setups.
- Stop/take-profit behavior still needs review because paper losses hit before the 4h horizon could mature.
- This plan does not resume paper entries or change execution behavior automatically.

Staged only. This report does not resume paper entries, enable bonuses, place real trades, or change risk_engine.py.
