"""Backtest deterministic Trade Quality Score thresholds.

This does not call Claude and does not modify the portfolio. It answers:
which score threshold would have produced the best historical behavior?
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import trade_quality
from backtest import (
    INPUT,
    STARTING_BALANCE,
    MAX_OPEN_TRADES,
    FEE_RATE,
    SLIPPAGE_RATE,
    ATR_INITIAL_STOP_MULT,
    ATR_TRAIL_STOP_MULT,
    MIN_CASH_FOR_BUY,
    Position,
    Trade,
    _close_position,
    _consecutive_losses,
    _date_key,
    _equity,
    _load_data,
    _position_size,
    _realized_pnl_since,
)
from config import MAX_DRAWDOWN_PCT, MAX_CONSECUTIVE_LOSS, DAILY_LOSS_LIMIT_PCT, MONTHLY_LOSS_LIMIT_PCT


THRESHOLDS = [55, 60, 65, 70, 75, 80, 85]
REPORT_JSON = Path("data/reports/trade_quality_sweep.json")
REPORT_CSV = Path("data/reports/trade_quality_sweep.csv")


def _market_from_row(row: pd.Series) -> dict:
    return {
        "price": row.get("close"),
        "rsi_14": row.get("rsi_14"),
        "macd_bullish": int(row.get("macd_bullish", 0)),
        "ema_50": row.get("ema_50"),
        "ema_200": row.get("ema_200"),
        "above_ema200": int(row.get("above_ema200", 0)),
        "above_ema50": int(row.get("above_ema50", 0)),
        "ema_bullish": int(row.get("ema_bullish", 0)),
        "bb_width": row.get("bb_width"),
        "atr_14": row.get("atr_14"),
        "stoch_k": row.get("stoch_k"),
        "funding_rate": row.get("funding_rate"),
        "long_short_ratio": row.get("long_short_ratio"),
        "etf_flow_usd": row.get("etf_flow"),
        "vix": row.get("vix"),
        "dxy": row.get("dxy"),
        "sp500": row.get("sp500"),
        "volume_quality": "reliable",
        "events_unavailable": False,
        "twitter_unavailable": False,
        "fear_greed_index": row.get("fear_greed_index"),
    }


def _historical_from_row(row: pd.Series) -> dict:
    return {
        "historical_win_rate_pct": 100 if int(row.get("hit_tp_before_sl", 0)) else 0,
        "avg_return_4h": row.get("future_return_4h", 0),
        "avg_return_24h": row.get("future_return_24h", 0),
    }


def _can_buy(ts, cash, equity_now, positions, trades, atr) -> tuple[bool, str | None]:
    if (STARTING_BALANCE - equity_now) / STARTING_BALANCE * 100 >= MAX_DRAWDOWN_PCT:
        return False, "max_drawdown"
    if _consecutive_losses(trades) >= MAX_CONSECUTIVE_LOSS:
        return False, "consecutive_losses"
    day_start = ts.normalize()
    daily_pnl = _realized_pnl_since(trades, day_start)
    if daily_pnl < 0 and abs(daily_pnl) / STARTING_BALANCE * 100 >= DAILY_LOSS_LIMIT_PCT:
        return False, "daily_loss_limit"
    month_start = pd.Timestamp(year=ts.year, month=ts.month, day=1)
    monthly_pnl = _realized_pnl_since(trades, month_start)
    if monthly_pnl < 0 and abs(monthly_pnl) / STARTING_BALANCE * 100 >= MONTHLY_LOSS_LIMIT_PCT:
        return False, "monthly_loss_limit"
    if len(positions) >= MAX_OPEN_TRADES:
        return False, "max_open_trades"
    if atr <= 0:
        return False, "missing_atr"
    if cash < MIN_CASH_FOR_BUY:
        return False, "insufficient_balance"
    return True, None


def run_threshold(df: pd.DataFrame, threshold: int) -> dict:
    cash = float(STARTING_BALANCE)
    positions: list[Position] = []
    trades: list[Trade] = []
    next_id = 1
    peak_equity = float(STARTING_BALANCE)
    max_dd = 0.0
    total_fees = 0.0
    holds = buys = sells = 0
    missed_upside_holds = 0
    block_counts: dict[str, int] = {}

    for _, row in df.iterrows():
        ts = row["timestamp"]
        date = _date_key(ts)
        open_price = float(row["open"])
        high = float(row["high"])
        low = float(row["low"])
        close = float(row["close"])
        atr = float(row["atr_14"])

        remaining: list[Position] = []
        for pos in positions:
            pos.highest_seen = max(pos.highest_seen, high)
            trailing = pos.highest_seen - ATR_TRAIL_STOP_MULT * atr
            stop = max(pos.stop_price, trailing)
            if low <= stop:
                exit_raw = open_price if open_price < stop else stop
                trade, net = _close_position(pos, ts, exit_raw * (1 - SLIPPAGE_RATE), "atr_trailing_stop", trades)
                cash += net
                total_fees += trade.sell_fee
            else:
                remaining.append(pos)
        positions = remaining

        equity_now = _equity(cash, positions, close)
        peak_equity = max(peak_equity, equity_now)
        max_dd = max(max_dd, (peak_equity - equity_now) / peak_equity * 100 if peak_equity else 0)

        q = trade_quality.score(_market_from_row(row), _historical_from_row(row), {})
        score = float(q["score"])
        final_action = "HOLD"

        if score >= threshold:
            ok, blocked = _can_buy(ts, cash, equity_now, positions, trades, atr)
            if ok:
                entry = close * (1 + SLIPPAGE_RATE)
                usd_size, stop_price = _position_size(cash, entry, atr)
                if usd_size >= 10:
                    fee = usd_size * FEE_RATE
                    positions.append(
                        Position(
                            id=next_id,
                            entry_date=date,
                            entry_price=entry,
                            btc_amount=usd_size / entry,
                            usd_size=usd_size,
                            buy_fee=fee,
                            stop_price=stop_price,
                            highest_seen=high,
                        )
                    )
                    next_id += 1
                    cash -= usd_size + fee
                    total_fees += fee
                    final_action = "BUY"
                    buys += 1
                else:
                    blocked = "position_too_small"
            if final_action != "BUY":
                block_counts[blocked or "blocked"] = block_counts.get(blocked or "blocked", 0) + 1
        elif positions and score < max(45, threshold - 20):
            pos = positions.pop(0)
            trade, net = _close_position(pos, ts, close * (1 - SLIPPAGE_RATE), "quality_exit", trades)
            cash += net
            total_fees += trade.sell_fee
            final_action = "SELL"
            sells += 1

        if final_action == "HOLD":
            holds += 1
            try:
                if float(row.get("future_return_24h", 0)) > 1.5:
                    missed_upside_holds += 1
            except Exception:
                pass

    final_close = float(df["close"].iloc[-1])
    final_equity = _equity(cash, positions, final_close)
    pnls = [t.pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    rows = len(df)
    return {
        "threshold": threshold,
        "total_return_pct": round((final_equity - STARTING_BALANCE) / STARTING_BALANCE * 100, 2),
        "final_equity": round(final_equity, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "win_rate_pct": round(len(wins) / len(pnls) * 100, 2) if pnls else 0,
        "profit_factor": round(gross_profit / gross_loss, 3) if gross_loss else (round(gross_profit, 3) if gross_profit else 0),
        "number_of_trades": len(trades),
        "executed_buys": buys,
        "executed_sells": sells,
        "average_trade_usd": round(sum(pnls) / len(pnls), 2) if pnls else 0,
        "worst_trade_usd": round(min(pnls), 2) if pnls else 0,
        "hold_ratio_pct": round(holds / rows * 100, 2) if rows else 0,
        "missed_upside_holds": missed_upside_holds,
        "block_breakdown": block_counts,
    }


def run(input_path: Path = INPUT) -> dict:
    df = _load_data(input_path)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    results = [run_threshold(df, t) for t in THRESHOLDS]
    best = sorted(
        results,
        key=lambda r: (r["total_return_pct"], -r["max_drawdown_pct"], r["profit_factor"]),
        reverse=True,
    )[0] if results else None
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": str(input_path),
        "thresholds": THRESHOLDS,
        "best_threshold": best,
        "results": results,
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    pd.DataFrame(results).to_csv(REPORT_CSV, index=False)
    return report


def main() -> None:
    report = run()
    best = report.get("best_threshold") or {}
    print("Trade Quality sweep complete")
    print(f"  Best threshold: {best.get('threshold')}")
    print(f"  Return:         {best.get('total_return_pct')}%")
    print(f"  Max DD:         {best.get('max_drawdown_pct')}%")
    print(f"  Trades:         {best.get('number_of_trades')}")
    print(f"  JSON:           {REPORT_JSON}")
    print(f"  CSV:            {REPORT_CSV}")


if __name__ == "__main__":
    main()
