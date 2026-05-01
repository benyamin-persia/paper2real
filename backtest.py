"""
Backtest the current Paper2Real labeled strategy.

This is a deterministic replay of data/processed/master_dataset.csv. It does
not call Claude. It uses the current labeler signal column as the proposed
BUY/SELL/HOLD decision, then applies trading frictions, risk-based position
sizing, ATR stops, trailing stops, and portfolio safety limits.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config import (
    STARTING_BALANCE,
    MAX_OPEN_TRADES,
    MAX_DRAWDOWN_PCT,
    MAX_CONSECUTIVE_LOSS,
    DAILY_LOSS_LIMIT_PCT,
    MONTHLY_LOSS_LIMIT_PCT,
    ATR_INITIAL_STOP_MULT,
    ATR_TRAIL_STOP_MULT,
)


INPUT = Path("data/processed/master_dataset.csv")
REPORT_JSON = Path("data/reports/backtest_latest.json")
TRADES_CSV = Path("data/reports/backtest_trades.csv")
EQUITY_CSV = Path("data/reports/backtest_equity.csv")

FEE_RATE = 0.001       # 0.10% per fill
SLIPPAGE_RATE = 0.0005 # 0.05% per fill
RISK_PER_TRADE_PCT = 1.0
MAX_BB_WIDTH_SQUEEZE = 0.02
MIN_CASH_FOR_BUY = 100.0


@dataclass
class Position:
    id: int
    entry_date: str
    entry_price: float
    btc_amount: float
    usd_size: float
    buy_fee: float
    stop_price: float
    highest_seen: float


@dataclass
class Trade:
    id: int
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    btc_amount: float
    usd_size: float
    buy_fee: float
    sell_fee: float
    pnl: float
    pnl_pct: float
    exit_reason: str
    holding_days: int


def _load_data(path: Path = INPUT) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run python collect.py first.")

    df = pd.read_csv(path, parse_dates=["timestamp"])
    required = {
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "atr_14",
        "bb_width",
        "signal",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{path} missing required columns: {missing}")

    df = df.dropna(subset=list(required)).copy()
    df = df.sort_values("timestamp").reset_index(drop=True)
    if df.empty:
        raise ValueError(f"{path} has no usable rows")
    return df


def _position_size(cash: float, entry_price: float, atr: float) -> tuple[float, float]:
    stop_distance = ATR_INITIAL_STOP_MULT * atr
    stop_price = entry_price - stop_distance
    stop_pct = stop_distance / entry_price if entry_price else 0
    if stop_pct <= 0:
        return 0.0, stop_price

    risk_amount = cash * (RISK_PER_TRADE_PCT / 100)
    usd_size = risk_amount / stop_pct
    usd_size = min(usd_size, cash * 0.30)
    usd_size = min(usd_size, cash / (1 + FEE_RATE))
    return round(usd_size, 2), round(stop_price, 2)


def _month_key(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m")


def _date_key(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m-%d")


def _realized_pnl_since(trades: list[Trade], start: pd.Timestamp) -> float:
    return sum(
        trade.pnl
        for trade in trades
        if pd.Timestamp(trade.exit_date) >= start
    )


def _consecutive_losses(trades: list[Trade]) -> int:
    streak = 0
    for trade in reversed(trades):
        if trade.pnl < 0:
            streak += 1
        else:
            break
    return streak


def _equity(cash: float, positions: list[Position], mark_price: float) -> float:
    return cash + sum(pos.btc_amount * mark_price for pos in positions)


def _close_position(
    position: Position,
    exit_date: pd.Timestamp,
    exit_price: float,
    exit_reason: str,
    trades: list[Trade],
) -> tuple[Trade, float]:
    gross = position.btc_amount * exit_price
    sell_fee = gross * FEE_RATE
    net = gross - sell_fee
    cost = position.usd_size + position.buy_fee
    pnl = net - cost
    holding_days = max(0, (exit_date - pd.Timestamp(position.entry_date)).days)
    trade = Trade(
        id=position.id,
        entry_date=position.entry_date,
        exit_date=_date_key(exit_date),
        entry_price=round(position.entry_price, 2),
        exit_price=round(exit_price, 2),
        btc_amount=round(position.btc_amount, 8),
        usd_size=round(position.usd_size, 2),
        buy_fee=round(position.buy_fee, 2),
        sell_fee=round(sell_fee, 2),
        pnl=round(pnl, 2),
        pnl_pct=round((pnl / cost) * 100, 2) if cost else 0.0,
        exit_reason=exit_reason,
        holding_days=holding_days,
    )
    trades.append(trade)
    return trade, net


def run_backtest(input_path: Path = INPUT) -> dict:
    df = _load_data(input_path)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)

    cash = float(STARTING_BALANCE)
    positions: list[Position] = []
    trades: list[Trade] = []
    decisions: list[dict] = []
    equity_rows: list[dict] = []
    block_counts: dict[str, int] = {}

    next_position_id = 1
    peak_equity = float(STARTING_BALANCE)
    max_drawdown_pct = 0.0
    total_fees = 0.0
    buy_signals = sell_signals = hold_signals = 0
    executed_buys = executed_sells = stop_sells = 0

    for _, row in df.iterrows():
        ts = row["timestamp"]
        date = _date_key(ts)
        signal = str(row["signal"]).upper()
        open_price = float(row["open"])
        high = float(row["high"])
        low = float(row["low"])
        close = float(row["close"])
        atr = float(row["atr_14"])
        bb_width = float(row["bb_width"])

        if signal == "BUY":
            buy_signals += 1
        elif signal == "SELL":
            sell_signals += 1
        else:
            hold_signals += 1

        # First process stops, matching live behavior where stops are checked
        # before asking Claude/risk engine for a new decision.
        remaining: list[Position] = []
        for position in positions:
            position.highest_seen = max(position.highest_seen, high)
            trailing_stop = position.highest_seen - (ATR_TRAIL_STOP_MULT * atr)
            effective_stop = max(position.stop_price, trailing_stop)

            if low <= effective_stop:
                raw_exit = open_price if open_price < effective_stop else effective_stop
                exit_price = raw_exit * (1 - SLIPPAGE_RATE)
                trade, net = _close_position(position, ts, exit_price, "atr_trailing_stop", trades)
                cash += net
                total_fees += trade.sell_fee
                stop_sells += 1
            else:
                remaining.append(position)
        positions = remaining

        equity_now = _equity(cash, positions, close)
        peak_equity = max(peak_equity, equity_now)
        drawdown_pct = (peak_equity - equity_now) / peak_equity * 100 if peak_equity else 0
        max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)

        final_action = "HOLD"
        blocked_by = None
        reason = "No signal"
        trade_executed = False

        if signal == "BUY":
            final_action, blocked_by, reason = _evaluate_buy(
                ts=ts,
                cash=cash,
                equity_now=equity_now,
                positions=positions,
                trades=trades,
                atr=atr,
                bb_width=bb_width,
            )
            if final_action == "BUY":
                entry_price = close * (1 + SLIPPAGE_RATE)
                usd_size, stop_price = _position_size(cash, entry_price, atr)
                if usd_size < 10:
                    final_action = "HOLD"
                    blocked_by = "position_too_small"
                    reason = "Calculated position size too small"
                else:
                    buy_fee = usd_size * FEE_RATE
                    btc_amount = usd_size / entry_price
                    cash -= usd_size + buy_fee
                    total_fees += buy_fee
                    positions.append(
                        Position(
                            id=next_position_id,
                            entry_date=date,
                            entry_price=entry_price,
                            btc_amount=btc_amount,
                            usd_size=usd_size,
                            buy_fee=buy_fee,
                            stop_price=stop_price,
                            highest_seen=high,
                        )
                    )
                    next_position_id += 1
                    executed_buys += 1
                    trade_executed = True
                    reason = "BUY signal passed backtest risk checks"

        elif signal == "SELL":
            if positions:
                position = positions.pop(0)
                exit_price = close * (1 - SLIPPAGE_RATE)
                trade, net = _close_position(position, ts, exit_price, "sell_signal", trades)
                cash += net
                total_fees += trade.sell_fee
                executed_sells += 1
                final_action = "SELL"
                trade_executed = True
                reason = "SELL signal closed oldest position"
            else:
                blocked_by = "no_open_position"
                reason = "SELL signal ignored because no position is open"

        if blocked_by:
            block_counts[blocked_by] = block_counts.get(blocked_by, 0) + 1

        equity_after = _equity(cash, positions, close)
        equity_rows.append(
            {
                "date": date,
                "close": round(close, 2),
                "cash": round(cash, 2),
                "open_positions": len(positions),
                "equity": round(equity_after, 2),
                "drawdown_pct": round((peak_equity - equity_after) / peak_equity * 100, 2)
                if peak_equity
                else 0.0,
            }
        )
        decisions.append(
            {
                "date": date,
                "signal": signal,
                "final_action": final_action,
                "blocked_by": blocked_by,
                "reason": reason,
                "price": round(close, 2),
                "equity": round(equity_after, 2),
                "cash": round(cash, 2),
                "open_positions": len(positions),
            }
        )

    final_close = float(df["close"].iloc[-1])
    final_equity = _equity(cash, positions, final_close)
    wins = [trade for trade in trades if trade.pnl > 0]
    losses = [trade for trade in trades if trade.pnl <= 0]
    trade_pnls = [trade.pnl for trade in trades]
    total_rows = len(df)
    hold_ratio = sum(1 for d in decisions if d["final_action"] == "HOLD") / total_rows * 100
    buy_and_hold = (final_close - float(df["close"].iloc[0])) / float(df["close"].iloc[0]) * 100

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": str(input_path),
        "period_start": _date_key(df["timestamp"].iloc[0]),
        "period_end": _date_key(df["timestamp"].iloc[-1]),
        "rows": total_rows,
        "assumptions": {
            "fee_rate_pct_per_fill": FEE_RATE * 100,
            "slippage_pct_per_fill": SLIPPAGE_RATE * 100,
            "risk_per_trade_pct": RISK_PER_TRADE_PCT,
            "atr_initial_stop_mult": ATR_INITIAL_STOP_MULT,
            "atr_trailing_stop_mult": ATR_TRAIL_STOP_MULT,
            "note": "Backtest replays daily master_dataset signals, not live 15-minute Claude decisions.",
        },
        "summary": {
            "starting_balance": round(float(STARTING_BALANCE), 2),
            "final_cash": round(cash, 2),
            "final_equity": round(final_equity, 2),
            "return_pct": round((final_equity - STARTING_BALANCE) / STARTING_BALANCE * 100, 2),
            "buy_and_hold_return_pct": round(buy_and_hold, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "total_fees_usd": round(total_fees, 2),
            "signals_buy": buy_signals,
            "signals_sell": sell_signals,
            "signals_hold": hold_signals,
            "executed_buys": executed_buys,
            "executed_sells": executed_sells,
            "stop_sells": stop_sells,
            "trades_closed": len(trades),
            "open_positions": len(positions),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate_pct": round(len(wins) / len(trades) * 100, 2) if trades else 0.0,
            "avg_trade_usd": round(sum(trade_pnls) / len(trade_pnls), 2) if trade_pnls else 0.0,
            "best_trade_usd": round(max(trade_pnls), 2) if trade_pnls else 0.0,
            "worst_trade_usd": round(min(trade_pnls), 2) if trade_pnls else 0.0,
            "hold_ratio_pct": round(hold_ratio, 2),
        },
        "block_breakdown": block_counts,
    }

    REPORT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pd.DataFrame([asdict(trade) for trade in trades]).to_csv(TRADES_CSV, index=False)
    pd.DataFrame(equity_rows).to_csv(EQUITY_CSV, index=False)
    return summary


def _evaluate_buy(
    ts: pd.Timestamp,
    cash: float,
    equity_now: float,
    positions: list[Position],
    trades: list[Trade],
    atr: float,
    bb_width: float,
) -> tuple[str, str | None, str]:
    drawdown_from_start = (STARTING_BALANCE - equity_now) / STARTING_BALANCE * 100
    if drawdown_from_start >= MAX_DRAWDOWN_PCT:
        return "HOLD", "max_drawdown", "Portfolio drawdown limit reached"

    streak = _consecutive_losses(trades)
    if streak >= MAX_CONSECUTIVE_LOSS:
        return "HOLD", "consecutive_losses", "Consecutive loss limit reached"

    day_start = ts.normalize()
    daily_pnl = _realized_pnl_since(trades, day_start)
    daily_loss_pct = abs(daily_pnl) / STARTING_BALANCE * 100
    if daily_pnl < 0 and daily_loss_pct >= DAILY_LOSS_LIMIT_PCT:
        return "HOLD", "daily_loss_limit", "Daily loss limit reached"

    month_start = pd.Timestamp(year=ts.year, month=ts.month, day=1)
    monthly_pnl = _realized_pnl_since(trades, month_start)
    monthly_loss_pct = abs(monthly_pnl) / STARTING_BALANCE * 100
    if monthly_pnl < 0 and monthly_loss_pct >= MONTHLY_LOSS_LIMIT_PCT:
        return "HOLD", "monthly_loss_limit", "Monthly loss limit reached"

    if len(positions) >= MAX_OPEN_TRADES:
        return "HOLD", "max_open_trades", "Maximum open trades reached"

    if atr <= 0:
        return "HOLD", "missing_atr", "ATR missing"

    if bb_width < MAX_BB_WIDTH_SQUEEZE:
        return "HOLD", "bb_squeeze", "Bollinger Band squeeze"

    if cash < MIN_CASH_FOR_BUY:
        return "HOLD", "insufficient_balance", "Insufficient cash"

    return "BUY", None, "BUY passed risk checks"


def main() -> None:
    report = run_backtest()
    s = report["summary"]
    print("Backtest complete")
    print(f"  Period:       {report['period_start']} -> {report['period_end']} ({report['rows']} rows)")
    print(f"  Final equity: ${s['final_equity']:,.2f}")
    print(f"  Return:       {s['return_pct']}%  (buy & hold: {s['buy_and_hold_return_pct']}%)")
    print(f"  Max DD:       {s['max_drawdown_pct']}%")
    print(f"  Trades:       {s['trades_closed']} closed, {s['open_positions']} open")
    print(f"  Win rate:     {s['win_rate_pct']}%")
    print(f"  Avg trade:    ${s['avg_trade_usd']:,.2f}")
    print(f"  Worst trade:  ${s['worst_trade_usd']:,.2f}")
    print(f"  HOLD ratio:   {s['hold_ratio_pct']}%")
    print(f"  Report:       {REPORT_JSON}")
    print(f"  Trades:       {TRADES_CSV}")
    print(f"  Equity:       {EQUITY_CSV}")


if __name__ == "__main__":
    main()
