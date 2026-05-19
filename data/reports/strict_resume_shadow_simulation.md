# Strict Resume Shadow Simulation

Paper test is paused. This is simulation only. No trades can open.

- Generated at: `2026-05-19T04:00:36.337703+00:00`
- Total Shadow BUY records: `310`
- Strict candidates: `77`
- Rejected: `233`
- Failed paper trades filtered out: `4`
- Strict 4h win rate: `46.67%`
- Strict avg 4h return: `-0.1564%`
- Recommendation: `DO_NOT_RESUME_YET`

## Rejected By Reason

- no_bullish_confirmation: `9`
- smart_money_bearish: `156`
- bb_squeeze_override_disabled: `40`
- ta_bearish: `28`

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
  "condition": "risk_blocker:no blocker",
  "count": 15,
  "scored_15m": 6,
  "win_rate_15m": 33.33,
  "avg_return_15m": -0.3238,
  "median_return_15m": -0.224,
  "min_return_15m": -1.0294,
  "max_return_15m": 0.1138,
  "scored_1h": 15,
  "win_rate_1h": 26.67,
  "avg_return_1h": -0.2492,
  "median_return_1h": -0.0579,
  "min_return_1h": -1.1629,
  "max_return_1h": 0.4149,
  "scored_4h": 13,
  "win_rate_4h": 30.77,
  "avg_return_4h": -0.48,
  "median_return_4h": -0.3585,
  "min_return_4h": -1.5672,
  "max_return_4h": 0.1156,
  "scored_24h": 10,
  "win_rate_24h": 10.0,
  "avg_return_24h": -0.6434,
  "median_return_24h": -0.2853,
  "min_return_24h": -2.1555,
  "max_return_24h": 0.0188
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
