# Strict Resume Shadow Simulation

Paper test is paused. This is simulation only. No trades can open.

- Generated at: `2026-05-18T04:00:20.949733+00:00`
- Total Shadow BUY records: `280`
- Strict candidates: `72`
- Rejected: `208`
- Failed paper trades filtered out: `4`
- Strict 4h win rate: `48.61%`
- Strict avg 4h return: `-0.1037%`
- Recommendation: `DO_NOT_RESUME_YET`

## Rejected By Reason

- no_bullish_confirmation: `9`
- smart_money_bearish: `131`
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
  "count": 10,
  "scored_15m": 3,
  "win_rate_15m": 66.67,
  "avg_return_15m": 0.0475,
  "median_return_15m": 0.0619,
  "min_return_15m": -0.0333,
  "max_return_15m": 0.1138,
  "scored_1h": 10,
  "win_rate_1h": 30.0,
  "avg_return_1h": -0.079,
  "median_return_1h": -0.0427,
  "min_return_1h": -0.4803,
  "max_return_1h": 0.0703,
  "scored_4h": 10,
  "win_rate_4h": 40.0,
  "avg_return_4h": -0.1974,
  "median_return_4h": -0.0683,
  "min_return_4h": -0.6977,
  "max_return_4h": 0.1156,
  "scored_24h": 6,
  "win_rate_24h": 16.67,
  "avg_return_24h": -0.1428,
  "median_return_24h": -0.1438,
  "min_return_24h": -0.2923,
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
