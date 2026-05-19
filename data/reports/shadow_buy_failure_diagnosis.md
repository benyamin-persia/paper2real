# Shadow BUY Failure Diagnosis

- Generated at: `2026-05-19T16:00:24.084102+00:00`
- Total Shadow BUY records: `325`
- Recent 50 avg 4h / win rate: `-0.0863%` / `35.56%`
- Recent 100 avg 4h / win rate: `-0.1134%` / `36.84%`
- Overall avg 4h / win rate: `-0.0451%` / `45.31%`
- Paper trades closed / win rate / PnL: `4` / `25.0%` / `$-0.4921`
- Recommended next action: `KEEP_PAPER_TEST_PAUSED, REQUIRE_ALL_CONFIRMATION_NEUTRAL_OR_BETTER, REQUIRE_TA_NOT_BEARISH, REQUIRE_AI_TA_NOT_BEARISH, CHANGE_STOP_TAKE_PROFIT_REVIEW_ONLY, COLLECT_MORE_SHADOW_ONLY, DO_NOT_RESUME`

## Worst Filters

- `smart_money_bias / neutral`: count `15`, avg 4h `-0.2471%`, win 4h `20.0%`
- `market_condition / premium_zone`: count `81`, avg 4h `-0.2069%`, win 4h `44.44%`
- `trade_quality_bucket / 85+`: count `7`, avg 4h `-0.1959%`, win 4h `42.86%`
- `risk_blocker / no blocker`: count `105`, avg 4h `-0.1181%`, win 4h `37.0%`
- `combined_alignment / Smart Money bullish + TA bullish + AI TA bullish`: count `43`, avg 4h `-0.1024%`, win 4h `39.53%`
- `trade_quality_bucket / 80 to 84`: count `41`, avg 4h `-0.0992%`, win 4h `46.34%`
- `smart_money_bias / bullish`: count `143`, avg 4h `-0.0981%`, win 4h `43.36%`
- `trade_quality_bucket / 70 to 74`: count `114`, avg 4h `-0.0844%`, win 4h `38.74%`

## Best Filters

- `market_condition / bearish_sweep`: count `32`, avg 4h `0.1586%`, win 4h `65.62%`
- `trade_quality_bucket / 75 to 79`: count `81`, avg 4h `0.0335%`, win 4h `48.1%`
- `smart_money_bias / bearish`: count `167`, avg 4h `0.0204%`, win 4h `49.38%`
- `risk_blocker / bb_squeeze`: count `112`, avg 4h `0.0153%`, win 4h `48.21%`
- `market_condition / bb_squeeze_active`: count `112`, avg 4h `0.0153%`, win 4h `48.21%`
- `market_condition / discount_zone`: count `235`, avg 4h `0.0126%`, win 4h `46.52%`
- `combined_alignment / all_bearish_alignment`: count `61`, avg 4h `-0.0068%`, win 4h `54.24%`
- `combined_alignment / any_bearish_alignment`: count `195`, avg 4h `-0.01%`, win 4h `47.37%`

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
