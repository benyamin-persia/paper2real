# Strict Resume Shadow Simulation

Paper test is paused. This is simulation only. No trades can open.

- Generated at: `2026-05-19T16:00:24.294038+00:00`
- Total Shadow BUY records: `325`
- Strict candidates: `81`
- Rejected: `244`
- Failed paper trades filtered out: `4`
- Strict 4h win rate: `41.98%`
- Strict avg 4h return: `-0.1694%`
- Recommendation: `DO_NOT_RESUME_YET`

## Rejected By Reason

- no_bullish_confirmation: `9`
- smart_money_bearish: `167`
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
  "count": 19,
  "scored_15m": 10,
  "win_rate_15m": 30.0,
  "avg_return_15m": -0.2603,
  "median_return_15m": -0.232,
  "min_return_15m": -1.0294,
  "max_return_15m": 0.3057,
  "scored_1h": 19,
  "win_rate_1h": 31.58,
  "avg_return_1h": -0.2554,
  "median_return_1h": -0.154,
  "min_return_1h": -1.1629,
  "max_return_1h": 0.4149,
  "scored_4h": 19,
  "win_rate_4h": 15.79,
  "avg_return_4h": -0.4331,
  "median_return_4h": -0.3389,
  "min_return_4h": -1.5672,
  "max_return_4h": 0.1156,
  "scored_24h": 13,
  "win_rate_24h": 7.69,
  "avg_return_24h": -0.6895,
  "median_return_24h": -0.785,
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
