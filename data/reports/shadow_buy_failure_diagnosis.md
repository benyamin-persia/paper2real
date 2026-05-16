# Shadow BUY Failure Diagnosis

- Generated at: `2026-05-16T16:00:18.176664+00:00`
- Total Shadow BUY records: `247`
- Recent 50 avg 4h / win rate: `-0.4003%` / `20.45%`
- Recent 100 avg 4h / win rate: `-0.1558%` / `36.17%`
- Overall avg 4h / win rate: `-0.0433%` / `47.72%`
- Paper trades closed / win rate / PnL: `4` / `25.0%` / `$-0.4921`
- Recommended next action: `KEEP_PAPER_TEST_PAUSED, REQUIRE_ALL_CONFIRMATION_NEUTRAL_OR_BETTER, REQUIRE_TA_NOT_BEARISH, REQUIRE_AI_TA_NOT_BEARISH, REQUIRE_SMART_MONEY_CONFIRMATION, CHANGE_STOP_TAKE_PROFIT_REVIEW_ONLY, COLLECT_MORE_SHADOW_ONLY, DO_NOT_RESUME`

## Worst Filters

- `risk_blocker / no blocker`: count `29`, avg 4h `-0.3102%`, win 4h `21.74%`
- `smart_money_bias / neutral`: count `15`, avg 4h `-0.2471%`, win 4h `20.0%`
- `market_condition / premium_zone`: count `81`, avg 4h `-0.2002%`, win 4h `45.68%`
- `trade_quality_bucket / 85+`: count `7`, avg 4h `-0.1474%`, win 4h `42.86%`
- `trade_quality_bucket / 70 to 74`: count `85`, avg 4h `-0.1272%`, win 4h `38.1%`
- `ai_ta_bias / bearish`: count `52`, avg 4h `-0.0899%`, win 4h `48.08%`
- `ta_bias / bearish`: count `95`, avg 4h `-0.0843%`, win 4h `43.96%`
- `market_condition / bullish_sweep`: count `206`, avg 4h `-0.0766%`, win 4h `45.5%`

## Best Filters

- `market_condition / bearish_sweep`: count `32`, avg 4h `0.1704%`, win 4h `68.75%`
- `ai_ta_bias / bullish`: count `36`, avg 4h `0.0876%`, win 4h `50.0%`
- `combined_alignment / Smart Money bullish + TA bullish + AI TA bullish`: count `33`, avg 4h `0.0621%`, win 4h `51.52%`
- `trade_quality_bucket / 75 to 79`: count `52`, avg 4h `0.0492%`, win 4h `51.06%`
- `market_condition / discount_zone`: count `157`, avg 4h `0.0421%`, win 4h `50.33%`
- `risk_blocker / bb_squeeze`: count `112`, avg 4h `0.0184%`, win 4h `51.79%`
- `market_condition / bb_squeeze_active`: count `112`, avg 4h `0.0184%`, win 4h `51.79%`
- `ta_bias / bullish`: count `57`, avg 4h `0.0056%`, win 4h `50.0%`

## Failure Reasons

- stop_loss_too_tight: `True`
- take_profit_too_far: `True`
- entries_were_against_ta_or_ai_ta: `True`
- bb_squeeze_overrides_are_weak: `True`
- four_hour_horizon_mismatches_stop_loss: `True`
- exchange_or_news_regime_changed: `True`
- sample_became_worse_after_more_data: `True`
- any_bearish_alignment_loses: `True`

No trading logic is changed by this report. Recommendations are not applied automatically.
