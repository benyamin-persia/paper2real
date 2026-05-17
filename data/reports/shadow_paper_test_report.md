# Shadow Paper Test Report

- Generated at: `2026-05-17T04:00:18.345262+00:00`
- Enabled: `False`
- Paper test entries enabled: `False`
- Current status: `Paper Test Paused`
- Pause reason: `Supervision forbids trading: DO_NOT_RESUME_TRADING_OR_PAPER_TEST`
- Strict rules staged: `True`
- Shadow BUY review recommendation: `SHADOW_BUY_STAYS_SHADOW`
- Mode: `paper_only`
- Paper only: `True`
- Recommendation: `PAPER_TEST_COLLECT_MORE`
- Total trades: `4`
- Open trades: `0`
- Closed trades: `4`
- Wins / losses: `1 / 3`
- Win rate: `25.0%`
- Average PnL: `-0.246%`, `$-0.123`
- Total PnL: `$-0.4921`
- Max drawdown: `$0.622`
- Take profit / stop loss / time / emergency exits: `0 / 2 / 1 / 1`

## Guardrails

- Paper test only; no real exchange order.
- Normal risk_engine.py is unchanged.
- Normal portfolio trades table is unchanged.
- Smart Money, TA, and AI TA remain shadow-only.

## Proposed Resume Rules

```json
{
  "smart_money_not_bearish": true,
  "ta_not_bearish": true,
  "ai_ta_not_bearish": true,
  "at_least_one_bullish_confirmation": true,
  "bb_squeeze_override_disabled": true,
  "bearish_sweep_confirmation_optional": true,
  "bearish_sweep_confirmation_active": false
}
```

## Config

```json
{
  "max_position_usd": 50.0,
  "max_open_trades": 1,
  "min_tq_score": 70.0,
  "min_shadow_review_count": 100,
  "stop_after_trades": 20,
  "max_daily_loss_usd": 25.0,
  "max_total_loss_usd": 50.0,
  "cooldown_minutes": 240,
  "horizon_hours": 4.0,
  "take_profit_pct": 0.5,
  "stop_loss_pct": -0.35,
  "strict_rules_staged": true,
  "require_smart_money_not_bearish": true,
  "require_ta_not_bearish": true,
  "require_ai_ta_not_bearish": true,
  "require_at_least_one_bullish_confirmation": true,
  "allow_bb_squeeze_override": false,
  "require_bearish_sweep_confirmation": false
}
```
