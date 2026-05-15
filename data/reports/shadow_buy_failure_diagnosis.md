# Shadow BUY Failure Diagnosis

- Generated at: `2026-05-15T16:00:22.177225+00:00`
- Total Shadow BUY records: `217`
- Recent 50 avg 4h / win rate: `0.0374%` / `45.83%`
- Recent 100 avg 4h / win rate: `-0.1309%` / `38.78%`
- Overall avg 4h / win rate: `-0.0015%` / `51.63%`
- Paper trades closed / win rate / PnL: `4` / `25.0%` / `$-0.4921`
- Recommended next action: `KEEP_PAPER_TEST_PAUSED, CHANGE_STOP_TAKE_PROFIT_REVIEW_ONLY, COLLECT_MORE_SHADOW_ONLY, DO_NOT_RESUME`

## Worst Filters

- `smart_money_bias / neutral`: count `15`, avg 4h `-0.2471%`, win 4h `20.0%`
- `market_condition / premium_zone`: count `81`, avg 4h `-0.1676%`, win 4h `46.84%`
- `trade_quality_bucket / 85+`: count `7`, avg 4h `-0.1474%`, win 4h `42.86%`
- `trade_quality_bucket / 70 to 74`: count `75`, avg 4h `-0.0788%`, win 4h `41.89%`
- `risk_blocker / exchange_alert`: count `100`, avg 4h `-0.0747%`, win 4h `48.0%`
- `market_condition / no_sweep`: count `9`, avg 4h `-0.0643%`, win 4h `22.22%`
- `risk_blocker / no blocker`: count `2`, avg 4h `-0.0574%`, win 4h `50.0%`
- `ai_ta_bias / neutral`: count `141`, avg 4h `-0.0493%`, win 4h `49.65%`

## Best Filters

- `combined_alignment / all_bearish_alignment`: count `26`, avg 4h `0.1711%`, win 4h `72.0%`
- `market_condition / bearish_sweep`: count `32`, avg 4h `0.1555%`, win 4h `68.75%`
- `market_condition / discount_zone`: count `127`, avg 4h `0.1063%`, win 4h `56.69%`
- `trade_quality_bucket / 75 to 79`: count `40`, avg 4h `0.0955%`, win 4h `55.0%`
- `ai_ta_bias / bullish`: count `35`, avg 4h `0.0915%`, win 4h `51.43%`
- `ai_ta_bias / bearish`: count `41`, avg 4h `0.0882%`, win 4h `58.97%`
- `smart_money_bias / bearish`: count `79`, avg 4h `0.0798%`, win 4h `58.97%`
- `combined_alignment / Smart Money bullish + TA bullish + AI TA bullish`: count `33`, avg 4h `0.0584%`, win 4h `51.52%`

## Failure Reasons

- stop_loss_too_tight: `True`
- take_profit_too_far: `True`
- entries_were_against_ta_or_ai_ta: `True`
- bb_squeeze_overrides_are_weak: `True`
- four_hour_horizon_mismatches_stop_loss: `True`
- exchange_or_news_regime_changed: `True`
- sample_became_worse_after_more_data: `False`
- any_bearish_alignment_loses: `False`

No trading logic is changed by this report. Recommendations are not applied automatically.
