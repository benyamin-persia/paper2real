# Shadow BUY Failure Diagnosis

- Generated at: `2026-05-19T04:00:36.113273+00:00`
- Total Shadow BUY records: `310`
- Recent 50 avg 4h / win rate: `-0.0402%` / `42.22%`
- Recent 100 avg 4h / win rate: `-0.1897%` / `36.84%`
- Overall avg 4h / win rate: `-0.0387%` / `46.56%`
- Paper trades closed / win rate / PnL: `4` / `25.0%` / `$-0.4921`
- Recommended next action: `KEEP_PAPER_TEST_PAUSED, REQUIRE_ALL_CONFIRMATION_NEUTRAL_OR_BETTER, REQUIRE_TA_NOT_BEARISH, REQUIRE_AI_TA_NOT_BEARISH, CHANGE_STOP_TAKE_PROFIT_REVIEW_ONLY, COLLECT_MORE_SHADOW_ONLY, DO_NOT_RESUME`

## Worst Filters

- `smart_money_bias / neutral`: count `15`, avg 4h `-0.2471%`, win 4h `20.0%`
- `market_condition / premium_zone`: count `81`, avg 4h `-0.2069%`, win 4h `44.44%`
- `trade_quality_bucket / 85+`: count `7`, avg 4h `-0.1959%`, win 4h `42.86%`
- `risk_blocker / no blocker`: count `90`, avg 4h `-0.1083%`, win 4h `40.0%`
- `smart_money_bias / bullish`: count `139`, avg 4h `-0.0879%`, win 4h `45.99%`
- `trade_quality_bucket / 70 to 74`: count `106`, avg 4h `-0.0843%`, win 4h `40.38%`
- `trade_quality_bucket / 80 to 84`: count `40`, avg 4h `-0.08%`, win 4h `47.5%`
- `combined_alignment / Smart Money bullish + TA neutral + AI TA neutral`: count `57`, avg 4h `-0.0757%`, win 4h `47.37%`

## Best Filters

- `market_condition / bearish_sweep`: count `32`, avg 4h `0.1586%`, win 4h `65.62%`
- `trade_quality_bucket / 75 to 79`: count `75`, avg 4h `0.0526%`, win 4h `50.0%`
- `smart_money_bias / bearish`: count `156`, avg 4h `0.0257%`, win 4h `49.67%`
- `market_condition / discount_zone`: count `220`, avg 4h `0.0257%`, win 4h `48.37%`
- `risk_blocker / bb_squeeze`: count `112`, avg 4h `0.0153%`, win 4h `48.21%`
- `market_condition / bb_squeeze_active`: count `112`, avg 4h `0.0153%`, win 4h `48.21%`
- `combined_alignment / any_bearish_alignment`: count `184`, avg 4h `-0.0071%`, win 4h `47.51%`
- `ta_bias / bearish`: count `126`, avg 4h `-0.0154%`, win 4h `47.15%`

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
