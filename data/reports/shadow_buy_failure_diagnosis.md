# Shadow BUY Failure Diagnosis

- Generated at: `2026-05-16T04:00:24.731775+00:00`
- Total Shadow BUY records: `232`
- Recent 50 avg 4h / win rate: `-0.0319%` / `42.22%`
- Recent 100 avg 4h / win rate: `-0.1031%` / `41.05%`
- Overall avg 4h / win rate: `-0.0168%` / `50.22%`
- Paper trades closed / win rate / PnL: `4` / `25.0%` / `$-0.4921`
- Recommended next action: `KEEP_PAPER_TEST_PAUSED, REQUIRE_ALL_CONFIRMATION_NEUTRAL_OR_BETTER, REQUIRE_TA_NOT_BEARISH, CHANGE_STOP_TAKE_PROFIT_REVIEW_ONLY, COLLECT_MORE_SHADOW_ONLY, DO_NOT_RESUME`

## Worst Filters

- `smart_money_bias / neutral`: count `15`, avg 4h `-0.2471%`, win 4h `20.0%`
- `market_condition / premium_zone`: count `81`, avg 4h `-0.2002%`, win 4h `45.68%`
- `trade_quality_bucket / 85+`: count `7`, avg 4h `-0.1474%`, win 4h `42.86%`
- `trade_quality_bucket / 70 to 74`: count `79`, avg 4h `-0.0996%`, win 4h `40.26%`
- `risk_blocker / exchange_alert`: count `100`, avg 4h `-0.0744%`, win 4h `48.0%`
- `market_condition / no_sweep`: count `9`, avg 4h `-0.0643%`, win 4h `22.22%`
- `trade_quality_bucket / 80 to 84`: count `40`, avg 4h `-0.0568%`, win 4h `50.0%`
- `ai_ta_bias / neutral`: count `149`, avg 4h `-0.0502%`, win 4h `48.63%`

## Best Filters

- `market_condition / bearish_sweep`: count `32`, avg 4h `0.1555%`, win 4h `68.75%`
- `ai_ta_bias / bullish`: count `36`, avg 4h `0.095%`, win 4h `51.43%`
- `market_condition / discount_zone`: count `142`, avg 4h `0.0947%`, win 4h `54.74%`
- `trade_quality_bucket / 75 to 79`: count `47`, avg 4h `0.0889%`, win 4h `54.55%`
- `combined_alignment / all_bearish_alignment`: count `32`, avg 4h `0.0858%`, win 4h `64.52%`
- `combined_alignment / Smart Money bullish + TA bullish + AI TA bullish`: count `33`, avg 4h `0.0621%`, win 4h `51.52%`
- `smart_money_bias / bearish`: count `94`, avg 4h `0.0476%`, win 4h `55.06%`
- `risk_blocker / bb_squeeze`: count `112`, avg 4h `0.0149%`, win 4h `51.79%`

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
