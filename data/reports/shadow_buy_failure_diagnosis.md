# Shadow BUY Failure Diagnosis

- Generated at: `2026-05-17T04:00:18.531229+00:00`
- Total Shadow BUY records: `262`
- Recent 50 avg 4h / win rate: `-0.3697%` / `28.89%`
- Recent 100 avg 4h / win rate: `-0.1785%` / `34.74%`
- Overall avg 4h / win rate: `-0.0441%` / `47.47%`
- Paper trades closed / win rate / PnL: `4` / `25.0%` / `$-0.4921`
- Recommended next action: `KEEP_PAPER_TEST_PAUSED, REQUIRE_ALL_CONFIRMATION_NEUTRAL_OR_BETTER, REQUIRE_TA_NOT_BEARISH, REQUIRE_AI_TA_NOT_BEARISH, REQUIRE_SMART_MONEY_CONFIRMATION, CHANGE_STOP_TAKE_PROFIT_REVIEW_ONLY, COLLECT_MORE_SHADOW_ONLY, DO_NOT_RESUME`

## Worst Filters

- `smart_money_bias / neutral`: count `15`, avg 4h `-0.2471%`, win 4h `20.0%`
- `market_condition / premium_zone`: count `81`, avg 4h `-0.2002%`, win 4h `45.68%`
- `risk_blocker / no blocker`: count `44`, avg 4h `-0.1905%`, win 4h `35.9%`
- `trade_quality_bucket / 85+`: count `7`, avg 4h `-0.1474%`, win 4h `42.86%`
- `trade_quality_bucket / 70 to 74`: count `92`, avg 4h `-0.1322%`, win 4h `37.08%`
- `ai_ta_bias / bearish`: count `58`, avg 4h `-0.1045%`, win 4h `45.45%`
- `ta_bias / bearish`: count `103`, avg 4h `-0.0826%`, win 4h `43.88%`
- `combined_alignment / all_bearish_alignment`: count `43`, avg 4h `-0.0819%`, win 4h `50.0%`

## Best Filters

- `market_condition / bearish_sweep`: count `32`, avg 4h `0.1586%`, win 4h `65.62%`
- `ai_ta_bias / bullish`: count `37`, avg 4h `0.0874%`, win 4h `51.35%`
- `combined_alignment / Smart Money bullish + TA bullish + AI TA bullish`: count `34`, avg 4h `0.0627%`, win 4h `52.94%`
- `trade_quality_bucket / 75 to 79`: count `57`, avg 4h `0.0624%`, win 4h `55.36%`
- `market_condition / discount_zone`: count `172`, avg 4h `0.0327%`, win 4h `49.7%`
- `risk_blocker / bb_squeeze`: count `112`, avg 4h `0.013%`, win 4h `50.0%`
- `market_condition / bb_squeeze_active`: count `112`, avg 4h `0.013%`, win 4h `50.0%`
- `ta_bias / bullish`: count `58`, avg 4h `0.0086%`, win 4h `51.72%`

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
