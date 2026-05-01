import sqlite3
import time
from datetime import datetime, timezone
from config import (
    DB_FILE, STARTING_BALANCE, TRADE_SIZE_PCT, MAX_OPEN_TRADES,
    MAX_DRAWDOWN_PCT, MAX_CONSECUTIVE_LOSS, DAILY_LOSS_LIMIT_PCT,
    ATR_INITIAL_STOP_MULT, ATR_TRAIL_STOP_MULT,
)


def init_db():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id      INTEGER PRIMARY KEY,
            balance REAL NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            side         TEXT NOT NULL,
            btc_amount   REAL NOT NULL,
            price        REAL NOT NULL,
            usd_value    REAL NOT NULL,
            reason       TEXT,
            timestamp    INTEGER NOT NULL,
            closed       INTEGER DEFAULT 0,
            close_price  REAL,
            pnl          REAL,
            stop_price   REAL,
            highest_seen REAL
        )
    """)
    # migrate existing DB — safe to run repeatedly, silently ignored if columns exist
    for col in ("stop_price REAL", "highest_seen REAL"):
        try:
            cur.execute(f"ALTER TABLE trades ADD COLUMN {col}")
        except Exception:
            pass
    cur.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp        INTEGER NOT NULL,
            trigger          TEXT DEFAULT 'unknown',
            btc_price        REAL,
            rsi_14           REAL,
            fear_greed       INTEGER,
            funding_rate     REAL,
            claude_action    TEXT,
            claude_conf      INTEGER,
            claude_reason    TEXT,
            final_action     TEXT,
            blocked_by       TEXT,
            block_reason     TEXT,
            position_usd     REAL,
            stop_price       REAL,
            trade_executed   INTEGER DEFAULT 0
        )
    """)
    try:
        cur.execute("ALTER TABLE decisions ADD COLUMN trigger TEXT DEFAULT 'unknown'")
    except Exception:
        pass
    cur.execute("INSERT OR IGNORE INTO portfolio (id, balance) VALUES (1, ?)", (STARTING_BALANCE,))
    con.commit()
    con.close()


def log_decision(
    market: dict,
    claude_out: dict,
    final: dict,
    trade_executed: bool,
    trigger: str = "unknown",
) -> None:
    """Record every scan decision to the decisions table for review."""
    con = sqlite3.connect(DB_FILE)
    con.execute(
        """INSERT INTO decisions
           (timestamp, trigger, btc_price, rsi_14, fear_greed, funding_rate,
            claude_action, claude_conf, claude_reason,
            final_action, blocked_by, block_reason,
            position_usd, stop_price, trade_executed)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            int(time.time()),
            trigger,
            market.get("price"),
            market.get("rsi_14"),
            market.get("fear_greed_index"),
            market.get("funding_rate"),
            claude_out.get("action"),
            claude_out.get("confidence"),
            (claude_out.get("reason") or "")[:500],
            final.get("action"),
            final.get("blocked_by"),
            (final.get("reason") or "")[:500],
            final.get("position_usd"),
            final.get("stop_price"),
            int(trade_executed),
        ),
    )
    con.commit()
    con.close()


def get_decisions(limit: int = 100) -> list[dict]:
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM decisions ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def get_balance() -> float:
    con = sqlite3.connect(DB_FILE)
    row = con.execute("SELECT balance FROM portfolio WHERE id=1").fetchone()
    con.close()
    return row[0] if row else STARTING_BALANCE


def get_open_trades() -> list[dict]:
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM trades WHERE closed=0").fetchall()
    con.close()
    return [dict(r) for r in rows]


def get_all_trades() -> list[dict]:
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 50").fetchall()
    con.close()
    return [dict(r) for r in rows]


def safety_check(current_btc_price: float) -> dict | None:
    """
    Returns a dict with {"blocked": True, "reason": str} if trading should stop.
    Returns None if safe to trade.
    """
    summary = portfolio_summary(current_btc_price)
    total   = summary["total_portfolio_usd"]

    # 1. Max drawdown — stop if portfolio lost more than MAX_DRAWDOWN_PCT
    drawdown_pct = (STARTING_BALANCE - total) / STARTING_BALANCE * 100
    if drawdown_pct >= MAX_DRAWDOWN_PCT:
        return {
            "blocked": True,
            "reason": f"MAX DRAWDOWN reached: portfolio down {drawdown_pct:.1f}% "
                      f"(limit: {MAX_DRAWDOWN_PCT}%). Trading paused to protect capital.",
        }

    # 2. Consecutive losses — stop after MAX_CONSECUTIVE_LOSS losses in a row
    closed = [t for t in get_all_trades() if t["closed"] and t["pnl"] is not None]
    closed_sorted = sorted(closed, key=lambda t: t["timestamp"], reverse=True)
    consecutive = 0
    for t in closed_sorted:
        if t["pnl"] < 0:
            consecutive += 1
        else:
            break
    if consecutive >= MAX_CONSECUTIVE_LOSS:
        return {
            "blocked": True,
            "reason": f"CONSECUTIVE LOSSES: {consecutive} losses in a row "
                      f"(limit: {MAX_CONSECUTIVE_LOSS}). Trading paused — strategy needs review.",
        }

    # 3. Daily loss limit — stop if down more than DAILY_LOSS_LIMIT_PCT today
    today_start = int(datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).timestamp())
    today_trades = [
        t for t in closed
        if t["timestamp"] >= today_start and t["pnl"] is not None
    ]
    daily_pnl = sum(t["pnl"] for t in today_trades)
    daily_loss_pct = abs(daily_pnl) / STARTING_BALANCE * 100
    if daily_pnl < 0 and daily_loss_pct >= DAILY_LOSS_LIMIT_PCT:
        return {
            "blocked": True,
            "reason": f"DAILY LOSS LIMIT: lost ${abs(daily_pnl):.2f} today "
                      f"({daily_loss_pct:.1f}% of balance, limit: {DAILY_LOSS_LIMIT_PCT}%). "
                      f"Resuming tomorrow.",
        }

    return None


def buy(price: float, reason: str, position_usd: float | None = None, stop_price: float | None = None) -> dict:
    block = safety_check(price)
    if block:
        return block

    balance     = get_balance()
    open_trades = get_open_trades()

    if len(open_trades) >= MAX_OPEN_TRADES:
        return {"error": f"Max open trades ({MAX_OPEN_TRADES}) reached"}

    # use risk-engine position size if provided, otherwise fall back to config default
    if position_usd is not None:
        usd_to_spend = round(min(position_usd, balance), 2)
    else:
        usd_to_spend = round(balance * TRADE_SIZE_PCT, 2)

    if usd_to_spend < 10:
        return {"error": "Insufficient balance"}

    btc_amount  = round(usd_to_spend / price, 8)
    initial_stop = round(stop_price, 2) if stop_price else None

    con = sqlite3.connect(DB_FILE)
    con.execute("UPDATE portfolio SET balance = balance - ? WHERE id=1", (usd_to_spend,))
    con.execute(
        """INSERT INTO trades
           (side, btc_amount, price, usd_value, reason, timestamp, stop_price, highest_seen)
           VALUES (?,?,?,?,?,?,?,?)""",
        ("BUY", btc_amount, price, usd_to_spend, reason, int(time.time()), initial_stop, price),
    )
    con.commit()
    con.close()

    return {
        "action":     "BUY",
        "btc_amount": btc_amount,
        "price":      price,
        "usd_spent":  usd_to_spend,
        "stop_price": initial_stop,
        "reason":     reason,
    }


def sell(price: float, reason: str) -> dict:
    open_trades = get_open_trades()
    if not open_trades:
        return {"error": "No open trades to sell"}

    trade        = open_trades[0]  # FIFO
    pnl          = round((price - trade["price"]) * trade["btc_amount"], 2)
    usd_received = round(trade["usd_value"] + pnl, 2)

    con = sqlite3.connect(DB_FILE)
    con.execute("UPDATE portfolio SET balance = balance + ? WHERE id=1", (usd_received,))
    con.execute(
        "UPDATE trades SET closed=1, close_price=?, pnl=? WHERE id=?",
        (price, pnl, trade["id"]),
    )
    con.commit()
    con.close()

    return {
        "action":     "SELL",
        "btc_amount": trade["btc_amount"],
        "buy_price":  trade["price"],
        "sell_price": price,
        "pnl_usd":    pnl,
        "reason":     reason,
    }


def check_trailing_stops(current_price: float, current_atr: float) -> list[dict]:
    """
    Check every open trade against its trailing stop.
    Closes any position where price has fallen from its peak by more than 2×ATR.
    Returns a list of close results (empty if no stops triggered).
    """
    if current_atr <= 0:
        return []

    open_trades = get_open_trades()
    closed = []

    for trade in open_trades:
        entry      = trade["price"]
        highest    = trade.get("highest_seen") or entry
        stop_stored = trade.get("stop_price")

        # update highest seen if price has risen
        new_highest = max(highest, current_price)

        # trailing stop: peak - 2×ATR
        trailing_stop = new_highest - (ATR_TRAIL_STOP_MULT * current_atr)
        # initial stop floor: entry - 1.5×ATR (never move stop below initial)
        initial_stop  = entry - (ATR_INITIAL_STOP_MULT * current_atr)
        # use stored stop if we saved a tighter one from the risk engine
        if stop_stored:
            initial_stop = max(initial_stop, stop_stored)

        effective_stop = max(trailing_stop, initial_stop)

        # update highest_seen in DB regardless of stop trigger
        con = sqlite3.connect(DB_FILE)
        con.execute(
            "UPDATE trades SET highest_seen=? WHERE id=?",
            (new_highest, trade["id"]),
        )
        con.commit()
        con.close()

        if current_price <= effective_stop:
            result = sell(
                current_price,
                f"Trailing stop hit — price ${current_price:,.2f} ≤ stop ${effective_stop:,.2f} "
                f"(peak ${new_highest:,.2f}, ATR ${current_atr:,.2f})",
            )
            result["triggered_by"] = "trailing_stop"
            result["stop_price"]   = round(effective_stop, 2)
            result["peak_price"]   = round(new_highest, 2)
            closed.append(result)

    return closed


def portfolio_summary(current_btc_price: float) -> dict:
    balance     = get_balance()
    open_trades = get_open_trades()
    all_trades  = get_all_trades()

    btc_held       = sum(t["btc_amount"] for t in open_trades)
    unrealized_pnl = sum((current_btc_price - t["price"]) * t["btc_amount"] for t in open_trades)
    realized_pnl   = sum(t["pnl"] for t in all_trades if t["closed"] and t["pnl"] is not None)
    total_value    = round(balance + btc_held * current_btc_price, 2)

    closed_trades  = [t for t in all_trades if t["closed"] and t["pnl"] is not None]
    wins           = sum(1 for t in closed_trades if t["pnl"] > 0)
    losses         = sum(1 for t in closed_trades if t["pnl"] <= 0)
    win_rate       = round(wins / len(closed_trades) * 100, 1) if closed_trades else 0.0

    return {
        "cash_balance_usd":   round(balance, 2),
        "btc_held":           round(btc_held, 8),
        "btc_value_usd":      round(btc_held * current_btc_price, 2),
        "total_portfolio_usd": total_value,
        "unrealized_pnl_usd": round(unrealized_pnl, 2),
        "realized_pnl_usd":   round(realized_pnl, 2),
        "total_pnl_usd":      round(unrealized_pnl + realized_pnl, 2),
        "open_trades":        len(open_trades),
        "total_trades":       len(closed_trades),
        "wins":               wins,
        "losses":             losses,
        "win_rate_pct":       win_rate,
        "starting_balance":   STARTING_BALANCE,
        "return_pct":         round((total_value - STARTING_BALANCE) / STARTING_BALANCE * 100, 2),
    }
