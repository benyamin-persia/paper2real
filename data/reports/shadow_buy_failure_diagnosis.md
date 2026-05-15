# Shadow BUY Failure Diagnosis

- Generated at: `2026-05-15T06:35:09.367331+00:00`
- Total Shadow BUY records: `209`
- Recent 50 avg 4h / win rate: `-0.006%` / `42.22%`
- Recent 100 avg 4h / win rate: `-0.0346%` / `41.05%`
- Overall avg 4h / win rate: `0.0399%` / `52.94%`
- Paper trades closed / win rate / PnL: `4` / `25.0%` / `$-0.4921`
- Recommended next action: `KEEP_PAPER_TEST_PAUSED, CHANGE_STOP_TAKE_PROFIT_REVIEW_ONLY, COLLECT_MORE_SHADOW_ONLY, DO_NOT_RESUME`

## Worst Filters

- `trade_quality_bucket / 85+`: count `7`, avg 4h `-0.1419%`, win 4h `50.0%`
- `smart_money_bias / neutral`: count `13`, avg 4h `-0.114%`, win 4h `23.08%`
- `market_condition / premium_zone`: count `73`, avg 4h `-0.0813%`, win 4h `50.0%`
- `risk_blocker / exchange_alert`: count `100`, avg 4h `-0.0661%`, win 4h `48.0%`
- `market_condition / no_sweep`: count `9`, avg 4h `-0.0643%`, win 4h `22.22%`
- `risk_blocker / no blocker`: count `2`, avg 4h `-0.0574%`, win 4h `50.0%`
- `trade_quality_bucket / 70 to 74`: count `73`, avg 4h `-0.0564%`, win 4h `41.67%`
- `smart_money_bias / bullish`: count `120`, avg 4h `-0.0059%`, win 4h `51.67%`

## Best Filters

- `combined_alignment / all_bearish_alignment`: count `23`, avg 4h `0.2595%`, win 4h `71.43%`
- `trade_quality_bucket / 80 to 84`: count `31`, avg 4h `0.1714%`, win 4h `62.07%`
- `market_condition / bearish_sweep`: count `32`, avg 4h `0.1555%`, win 4h `68.75%`
- `smart_money_bias / bearish`: count `76`, avg 4h `0.1455%`, win 4h `60.56%`
- `risk_blocker / bb_squeeze`: count `101`, avg 4h `0.1359%`, win 4h `57.29%`
- `market_condition / bb_squeeze_active`: count `101`, avg 4h `0.1359%`, win 4h `57.29%`
- `ai_ta_bias / bearish`: count `37`, avg 4h `0.1318%`, win 4h `57.14%`
- `ai_ta_bias / bullish`: count `35`, avg 4h `0.1203%`, win 4h `52.94%`

## Failure Reasons

- stop_loss_too_tight: `True`
- take_profit_too_far: `True`
- entries_were_against_ta_or_ai_ta: `True`
- bb_squeeze_overrides_are_weak: `True`
- four_hour_horizon_mismatches_stop_loss: `True`
- exchange_or_news_regime_changed: `True`
- sample_became_worse_after_more_data: `True`
- any_bearish_alignment_loses: `False`

No trading logic is changed by this report. Recommendations are not applied automatically.
