# Shadow BUY Failure Diagnosis

- Generated at: `2026-05-18T16:00:18.850505+00:00`
- Total Shadow BUY records: `295`
- Recent 50 avg 4h / win rate: `-0.0203%` / `44.44%`
- Recent 100 avg 4h / win rate: `-0.143%` / `35.79%`
- Overall avg 4h / win rate: `-0.0374%` / `46.55%`
- Paper trades closed / win rate / PnL: `4` / `25.0%` / `$-0.4921`
- Recommended next action: `KEEP_PAPER_TEST_PAUSED, REQUIRE_ALL_CONFIRMATION_NEUTRAL_OR_BETTER, REQUIRE_TA_NOT_BEARISH, REQUIRE_AI_TA_NOT_BEARISH, CHANGE_STOP_TAKE_PROFIT_REVIEW_ONLY, COLLECT_MORE_SHADOW_ONLY, DO_NOT_RESUME`

## Worst Filters

- `smart_money_bias / neutral`: count `15`, avg 4h `-0.2471%`, win 4h `20.0%`
- `market_condition / premium_zone`: count `81`, avg 4h `-0.2069%`, win 4h `44.44%`
- `trade_quality_bucket / 85+`: count `7`, avg 4h `-0.1959%`, win 4h `42.86%`
- `risk_blocker / no blocker`: count `75`, avg 4h `-0.1174%`, win 4h `38.57%`
- `trade_quality_bucket / 70 to 74`: count `101`, avg 4h `-0.0916%`, win 4h `40.4%`
- `trade_quality_bucket / 80 to 84`: count `40`, avg 4h `-0.0826%`, win 4h `45.0%`
- `combined_alignment / Smart Money bullish + TA neutral + AI TA neutral`: count `57`, avg 4h `-0.0757%`, win 4h `47.37%`
- `ai_ta_bias / bearish`: count `71`, avg 4h `-0.0746%`, win 4h `46.38%`

## Best Filters

- `market_condition / bearish_sweep`: count `32`, avg 4h `0.1586%`, win 4h `65.62%`
- `trade_quality_bucket / 75 to 79`: count `71`, avg 4h `0.0596%`, win 4h `52.11%`
- `ai_ta_bias / bullish`: count `43`, avg 4h `0.0578%`, win 4h `48.78%`
- `market_condition / discount_zone`: count `205`, avg 4h `0.0325%`, win 4h `48.5%`
- `risk_blocker / bb_squeeze`: count `112`, avg 4h `0.0153%`, win 4h `48.21%`
- `market_condition / bb_squeeze_active`: count `112`, avg 4h `0.0153%`, win 4h `48.21%`
- `smart_money_bias / bearish`: count `143`, avg 4h `0.0128%`, win 4h `49.29%`
- `combined_alignment / Smart Money bullish + TA bullish + AI TA bullish`: count `38`, avg 4h `0.0091%`, win 4h `47.22%`

## Failure Reasons

- stop_loss_too_tight: `True`
- take_profit_too_far: `True`
- entries_were_against_ta_or_ai_ta: `True`
- bb_squeeze_overrides_are_weak: `True`
- four_hour_horizon_mismatches_stop_loss: `True`
- exchange_or_news_regime_changed: `True`
- sample_became_worse_after_more_data: `False`
- any_bearish_alignment_loses: `True`

No trading logic is changed by this report. Recommendations are not applied automatically.
