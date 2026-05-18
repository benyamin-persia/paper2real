# Shadow BUY Failure Diagnosis

- Generated at: `2026-05-18T04:00:20.767839+00:00`
- Total Shadow BUY records: `280`
- Recent 50 avg 4h / win rate: `-0.136%` / `44.44%`
- Recent 100 avg 4h / win rate: `-0.0888%` / `37.89%`
- Overall avg 4h / win rate: `-0.0367%` / `47.27%`
- Paper trades closed / win rate / PnL: `4` / `25.0%` / `$-0.4921`
- Recommended next action: `KEEP_PAPER_TEST_PAUSED, REQUIRE_ALL_CONFIRMATION_NEUTRAL_OR_BETTER, REQUIRE_TA_NOT_BEARISH, REQUIRE_AI_TA_NOT_BEARISH, CHANGE_STOP_TAKE_PROFIT_REVIEW_ONLY, COLLECT_MORE_SHADOW_ONLY, DO_NOT_RESUME`

## Worst Filters

- `smart_money_bias / neutral`: count `15`, avg 4h `-0.2471%`, win 4h `20.0%`
- `market_condition / premium_zone`: count `81`, avg 4h `-0.2064%`, win 4h `44.44%`
- `trade_quality_bucket / 85+`: count `7`, avg 4h `-0.1959%`, win 4h `42.86%`
- `risk_blocker / no blocker`: count `61`, avg 4h `-0.1137%`, win 4h `42.11%`
- `trade_quality_bucket / 70 to 74`: count `97`, avg 4h `-0.0914%`, win 4h `39.58%`
- `trade_quality_bucket / 80 to 84`: count `40`, avg 4h `-0.0795%`, win 4h `45.0%`
- `risk_blocker / exchange_alert`: count `100`, avg 4h `-0.0744%`, win 4h `48.0%`
- `ai_ta_bias / bearish`: count `66`, avg 4h `-0.0662%`, win 4h `49.18%`

## Best Filters

- `market_condition / bearish_sweep`: count `32`, avg 4h `0.1586%`, win 4h `65.62%`
- `ai_ta_bias / bullish`: count `40`, avg 4h `0.0501%`, win 4h `47.5%`
- `trade_quality_bucket / 75 to 79`: count `64`, avg 4h `0.0469%`, win 4h `53.97%`
- `market_condition / discount_zone`: count `190`, avg 4h `0.0389%`, win 4h `49.73%`
- `risk_blocker / bb_squeeze`: count `112`, avg 4h `0.0156%`, win 4h `48.21%`
- `market_condition / bb_squeeze_active`: count `112`, avg 4h `0.0156%`, win 4h `48.21%`
- `smart_money_bias / bearish`: count `131`, avg 4h `0.0107%`, win 4h `50.79%`
- `combined_alignment / Smart Money bullish + TA bullish + AI TA bullish`: count `36`, avg 4h `0.0091%`, win 4h `47.22%`

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
