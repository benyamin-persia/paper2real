# Strict Resume Shadow Simulation

Paper test is paused. This is simulation only. No trades can open.

- Generated at: `2026-05-15T06:35:09.791131+00:00`
- Total Shadow BUY records: `209`
- Strict candidates: `62`
- Rejected: `147`
- Failed paper trades filtered out: `4`
- Strict 4h win rate: `50.0%`
- Strict avg 4h return: `-0.0916%`
- Recommendation: `DO_NOT_RESUME_YET`

## Rejected By Reason

- no_bullish_confirmation: `9`
- smart_money_bearish: `76`
- bb_squeeze_override_disabled: `38`
- ta_bearish: `24`

## Best Condition

```json
{
  "condition": "market:bearish_sweep",
  "count": 9,
  "scored_15m": 5,
  "win_rate_15m": 40.0,
  "avg_return_15m": -0.2152,
  "median_return_15m": -0.2151,
  "min_return_15m": -0.7571,
  "max_return_15m": 0.1629,
  "scored_1h": 9,
  "win_rate_1h": 44.44,
  "avg_return_1h": -0.1142,
  "median_return_1h": -0.0904,
  "min_return_1h": -0.8012,
  "max_return_1h": 0.5323,
  "scored_4h": 9,
  "win_rate_4h": 77.78,
  "avg_return_4h": 0.0756,
  "median_return_4h": 0.1778,
  "min_return_4h": -0.7554,
  "max_return_4h": 0.5885,
  "scored_24h": 9,
  "win_rate_24h": 100.0,
  "avg_return_24h": 0.5332,
  "median_return_24h": 0.5335,
  "min_return_24h": 0.0145,
  "max_return_24h": 0.8769
}
```

## Worst Condition

```json
{
  "condition": "alignment:ta_bullish",
  "count": 29,
  "scored_15m": 17,
  "win_rate_15m": 35.29,
  "avg_return_15m": -0.0963,
  "median_return_15m": -0.0173,
  "min_return_15m": -0.7571,
  "max_return_15m": 0.1933,
  "scored_1h": 29,
  "win_rate_1h": 27.59,
  "avg_return_1h": -0.1093,
  "median_return_1h": -0.0952,
  "min_return_1h": -0.8012,
  "max_return_1h": 0.5323,
  "scored_4h": 29,
  "win_rate_4h": 41.38,
  "avg_return_4h": -0.1701,
  "median_return_4h": -0.0544,
  "min_return_4h": -1.2435,
  "max_return_4h": 0.7873,
  "scored_24h": 29,
  "win_rate_24h": 48.28,
  "avg_return_24h": -0.6301,
  "median_return_24h": -0.1891,
  "min_return_24h": -2.6983,
  "max_return_24h": 0.8769
}
```

## Minimum Resume Requirements

```json
{
  "strict_candidates_count_gte_50": true,
  "strict_candidate_4h_win_rate_gte_55": false,
  "strict_candidate_avg_return_4h_positive": false,
  "twenty_four_hour_not_strongly_negative": false,
  "failed_paper_trades_filtered_out_gte_3": true,
  "note": "These requirements are informational only; the paper test remains paused."
}
```

No recommendations are applied automatically.
