import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import httpx
import pandas as pd
import pandas_ta as ta
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse

import trader
import brain
import risk_engine
from data.collector import events as events_collector
from config import WEBHOOK_SECRET

EVENTS_REFRESH_MINUTES = 15    # how often to re-scrape CryptoPanic
EVENTS_MAX_AGE_MINUTES = 20    # older than this → treat as missing
MASTER_DATASET_MAX_AGE_HOURS = 36  # warn if training data is very stale
PRICE_MAX_AGE_MINUTES = 20     # warn if latest candle is old

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("paper2real")

SCAN_INTERVAL_HOURS = 4
EVENT_MOVE_TRIGGER_PCT = 2.0
EVENT_SCAN_CHECK_MINUTES = 5
EVENT_SCAN_COOLDOWN_MINUTES = 30
EVENT_SCAN_MAX_PER_DAY = 3
SCAN_LOCK = asyncio.Lock()


def _check_data_freshness(context: dict) -> list[str]:
    """
    Returns warning strings for missing or stale context data.
    Lines starting with CRITICAL → caller must skip the scan.
    Lines starting with WARNING → log and continue with reduced context.
    """

    issues = []

    # ── Critical: live price data ─────────────────────────────────────────────
    if context.get("price", 0) <= 0:
        issues.append("CRITICAL: BTC price is zero or missing")
    if context.get("rsi_14") is None:
        issues.append("CRITICAL: RSI missing — insufficient candle data")
    if context.get("atr_14", 0) <= 0:
        issues.append("CRITICAL: ATR is zero — cannot size positions")

    # Check how old the latest 15m candle is
    latest_candle_ts = context.get("price_timestamp")
    if latest_candle_ts:
        age_minutes = (datetime.now().timestamp() - latest_candle_ts) / 60
        if age_minutes > PRICE_MAX_AGE_MINUTES:
            issues.append(
                f"CRITICAL: Latest price candle is {age_minutes:.0f} min old "
                f"(max {PRICE_MAX_AGE_MINUTES} min) — data feed may be down"
            )

    # ── Warnings: enrichment data ─────────────────────────────────────────────
    if context.get("fear_greed_index") is None:
        issues.append("WARNING: Fear & Greed unavailable — proceeding without sentiment")

    # Check master_dataset.csv age (training data for pattern matching)
    master = Path("data/processed/master_dataset.csv")
    if master.exists():
        age_hours = (datetime.now().timestamp() - os.path.getmtime(master)) / 3600
        if age_hours > MASTER_DATASET_MAX_AGE_HOURS:
            issues.append(
                f"WARNING: Training dataset is {age_hours:.0f}h old "
                f"(max {MASTER_DATASET_MAX_AGE_HOURS}h) — run collect.py to refresh"
            )
    else:
        issues.append("WARNING: master_dataset.csv missing — pattern matching disabled")

    # Check events.json age — stale/missing blocks new BUYs
    events_file = Path("data/raw/events.json")
    if events_file.exists():
        age_min = (datetime.now().timestamp() - os.path.getmtime(events_file)) / 60
        if age_min > EVENTS_MAX_AGE_MINUTES:
            issues.append(
                f"BUY_BLOCK: Events data is {age_min:.0f} min old "
                f"(max {EVENTS_MAX_AGE_MINUTES} min) — cannot verify no critical events, blocking new BUY"
            )
    else:
        issues.append("BUY_BLOCK: events.json missing — critical event detection disabled, blocking new BUY")

    return issues


async def _run_scan(trigger: str = "scheduled"):
    if SCAN_LOCK.locked():
        log.warning("SCAN SKIPPED - another scan is already running")
        return

    async with SCAN_LOCK:
        await _run_scan_unlocked(trigger)


async def _run_scan_unlocked(trigger: str = "scheduled"):
    """One scan cycle — check stops, validate data, ask Claude, run risk engine, execute trade."""
    try:
        context = await get_market_context()
        price   = context["price"]
        atr     = context.get("atr_14", 0)

        # 1. Check data freshness before anything else
        issues = _check_data_freshness(context)
        for w in issues:
            log.warning("DATA: %s", w)
        if any(w.startswith("CRITICAL") for w in issues):
            log.warning("SCAN SKIPPED — critical data missing")
            return
        # events_unavailable already set inside get_market_context() for all paths

        # 2. Check ATR trailing stops on all open positions first
        stops = trader.check_trailing_stops(price, atr)
        for s in stops:
            log.info(
                "TRAILING STOP | closed trade at $%s | stop=$%s | peak=$%s | P&L=$%s",
                f"{price:,.0f}",
                s.get("stop_price", "?"),
                s.get("peak_price", "?"),
                s.get("pnl_usd", "?"),
            )

        # 3. Run brain → risk engine → execute
        summary    = trader.portfolio_summary(price)
        claude_out = brain.decide(context, summary)
        closed     = [t for t in trader.get_all_trades() if t["closed"]]
        final      = risk_engine.evaluate(claude_out, context, summary, closed)

        action  = final["action"]
        reason  = final["reason"]
        blocked = final.get("blocked_by")
        conf    = claude_out.get("confidence", 0)

        log.info(
            "SCAN | BTC=$%s  RSI=%.1f  F&G=%s | Claude=%s(%s%%) → Final=%s%s — %s",
            f"{price:,.0f}",
            context["rsi_14"],
            context.get("fear_greed_index", "?"),
            claude_out.get("action", "?"),
            conf,
            action,
            f" [blocked:{blocked}]" if blocked else "",
            reason[:120],
        )

        trade_executed = False
        if action == "BUY":
            result = trader.buy(
                price, reason,
                position_usd=final.get("position_usd"),
                stop_price=final.get("stop_price"),
            )
            trade_executed = "error" not in result and "blocked" not in result
            log.info("BUY  executed: %s", result)
        elif action == "SELL":
            result = trader.sell(price, reason)
            trade_executed = "error" not in result
            log.info("SELL executed: %s", result)

        trader.log_decision(context, claude_out, final, trade_executed, trigger=trigger)

    except Exception as e:
        log.error("Scan failed: %s", e)


async def _auto_scan_loop():
    """Background loop — scans every SCAN_INTERVAL_HOURS hours."""
    log.info("Auto-scan started — interval: %sh", SCAN_INTERVAL_HOURS)
    while True:
        await _run_scan(trigger="scheduled")
        next_scan = datetime.now().strftime("%H:%M")
        log.info("Next scan in %sh (started at %s)", SCAN_INTERVAL_HOURS, next_scan)
        await asyncio.sleep(SCAN_INTERVAL_HOURS * 3600)


async def _event_price_move_loop():
    """Trigger an emergency scan if BTC moves fast between recent 15m candles."""
    log.info(
        "Event-driven scan loop started - %.1f%% move / 30m, max %s/day",
        EVENT_MOVE_TRIGGER_PCT,
        EVENT_SCAN_MAX_PER_DAY,
    )
    scans_today = 0
    current_day = datetime.utcnow().date()
    last_event_scan_ts = 0.0

    while True:
        try:
            today = datetime.utcnow().date()
            if today != current_day:
                current_day = today
                scans_today = 0

            df = await get_15m_candles()
            if len(df) >= 3:
                previous = df.iloc[-3]
                latest = df.iloc[-1]
                old_price = float(previous["close"])
                new_price = float(latest["close"])
                move_pct = (new_price - old_price) / old_price * 100 if old_price else 0.0
                minutes_since_last = (
                    (datetime.now().timestamp() - last_event_scan_ts) / 60
                    if last_event_scan_ts
                    else EVENT_SCAN_COOLDOWN_MINUTES + 1
                )

                if (
                    abs(move_pct) >= EVENT_MOVE_TRIGGER_PCT
                    and scans_today < EVENT_SCAN_MAX_PER_DAY
                    and minutes_since_last >= EVENT_SCAN_COOLDOWN_MINUTES
                ):
                    log.warning(
                        "EVENT PRICE MOVE | BTC %.2f%% in ~30m ($%s -> $%s) - emergency scan",
                        move_pct,
                        f"{old_price:,.0f}",
                        f"{new_price:,.0f}",
                    )
                    await _run_scan(trigger="event_price_move")
                    scans_today += 1
                    last_event_scan_ts = datetime.now().timestamp()
        except Exception as e:
            log.error("Event-driven scan check failed: %s", e)

        await asyncio.sleep(EVENT_SCAN_CHECK_MINUTES * 60)


async def _events_refresh_loop():
    """Background task — refreshes CryptoPanic events every EVENTS_REFRESH_MINUTES."""
    log.info("Events refresh loop started — interval: %sm", EVENTS_REFRESH_MINUTES)
    while True:
        try:
            data = await events_collector.async_scrape()
            if data.get("has_critical"):
                for alert in data.get("critical_alerts", []):
                    log.warning("CRITICAL EVENT: [%s] %s", alert["alert_type"], alert["headline"][:120])
            else:
                log.info("Events refreshed — no critical alerts")
        except Exception as e:
            log.error("Events refresh failed: %s", e)
        await asyncio.sleep(EVENTS_REFRESH_MINUTES * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scan_task   = asyncio.create_task(_auto_scan_loop())
    events_task = asyncio.create_task(_events_refresh_loop())
    event_scan_task = asyncio.create_task(_event_price_move_loop())
    yield
    scan_task.cancel()
    events_task.cancel()
    event_scan_task.cancel()


app = FastAPI(title="Paper2Real BTC Trader", lifespan=lifespan)
trader.init_db()

YAHOO_15M_URL = "https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=15m&range=5d"
COINBASE_PRICE_URL = "https://api.coinbase.com/v2/prices/BTC-USD/spot"
COINBASE_CANDLES_URL = "https://api.exchange.coinbase.com/products/BTC-USD/candles"

DEPEG_THRESHOLD_PCT = 0.5   # alert if stablecoin deviates > 0.5% from $1.00

# Next BTC halving — update when it passes
_LAST_HALVING = datetime(2024, 4, 19)
_NEXT_HALVING = datetime(2028, 4, 15)


def _latest(df: pd.DataFrame, col: str) -> float | None:
    """Return the latest non-null value in a column, regardless of row order."""
    try:
        series = df.sort_values("date")[col].dropna()
        return float(series.iloc[-1]) if not series.empty else None
    except Exception:
        return None


def _load_daily_context() -> dict:
    """
    Reads the latest non-null value per field from each daily CSV.
    Uses per-column dropna so a sparse last row never masks older good data.
    Falls back gracefully — missing files just leave those keys absent.
    """
    ctx: dict = {}

    # CoinGlass — derivatives
    try:
        df = pd.read_csv("data/raw/coinglass.csv")
        if not df.empty:
            ctx["funding_rate"]       = _latest(df, "funding_rate")
            ctx["open_interest"]      = _latest(df, "open_interest")
            ctx["long_short_ratio"]   = _latest(df, "long_short_ratio")
            ctx["etf_flow_usd"]       = _latest(df, "etf_flow")
            ctx["long_liquidations"]  = _latest(df, "long_liquidations")
            ctx["short_liquidations"] = _latest(df, "short_liquidations")
    except Exception:
        pass

    # CoinGecko — market structure
    try:
        df = pd.read_csv("data/raw/coingecko.csv")
        if not df.empty:
            ctx["btc_dominance"]        = _latest(df, "btc_dominance")
            ctx["btc_market_cap"]       = _latest(df, "btc_market_cap")
            ctx["usdt_market_cap"]      = _latest(df, "usdt_market_cap")
            ctx["altcoin_season_index"] = _latest(df, "altcoin_season_index")
    except Exception:
        pass

    # Macro — S&P500, DXY, VIX, Gold
    try:
        df = pd.read_csv("data/raw/macro.csv")
        if not df.empty:
            ctx["sp500"] = _latest(df, "sp500")
            ctx["dxy"]   = _latest(df, "dxy")
            ctx["vix"]   = _latest(df, "vix")
            ctx["gold"]  = _latest(df, "gold")
    except Exception:
        pass

    # Halving cycle (static calculation)
    now = datetime.now()
    cycle_days   = (_NEXT_HALVING - _LAST_HALVING).days
    elapsed_days = (now - _LAST_HALVING).days
    ctx["days_since_halving"]   = elapsed_days
    ctx["days_to_next_halving"] = max(0, (_NEXT_HALVING - now).days)
    ctx["halving_cycle_pct"]    = round(elapsed_days / cycle_days * 100, 1)

    return ctx


async def _get_stablecoin_status(client: httpx.AsyncClient) -> str | None:
    """
    Returns a depeg alert string if USDT or USDC has moved > 0.5% from $1.00.
    Returns None if both are healthy or if the check fails.
    """
    for symbol in ("USDT", "USDC"):
        try:
            r = await client.get(
                f"https://api.coinbase.com/v2/prices/{symbol}-USD/spot",
                timeout=10,
            )
            r.raise_for_status()
            price = float(r.json()["data"]["amount"])
            deviation_pct = abs(price - 1.0) * 100
            if deviation_pct > DEPEG_THRESHOLD_PCT:
                return (
                    f"{symbol} trading at ${price:.4f} "
                    f"({deviation_pct:.2f}% deviation from $1.00)"
                )
        except Exception:
            continue
    return None


def _get_events_alert() -> tuple[str | None, str | None]:
    """
    Reads cached events.json.
    Returns (exchange_hack_alert, stablecoin_depeg) or (None, None) if stale/missing.
    """
    events_file = Path("data/raw/events.json")
    if not events_file.exists():
        return None, None

    age_minutes = (
        datetime.now().timestamp() - os.path.getmtime(events_file)
    ) / 60

    if age_minutes > EVENTS_MAX_AGE_MINUTES:
        log.warning(
            "Events data is %.0f min old (max %s min) — treating as missing",
            age_minutes,
            EVENTS_MAX_AGE_MINUTES,
        )
        return None, None

    data = events_collector.read_cached()
    if not data:
        return None, None

    return data.get("exchange_hack_alert"), data.get("stablecoin_depeg")


async def get_btc_price() -> float:
    try:
        df = await get_15m_candles()
        if not df.empty:
            return float(df["close"].iloc[-1])
    except Exception:
        pass

    async with httpx.AsyncClient(timeout=20, headers={"user-agent": "Mozilla/5.0"}) as client:
        r = await client.get(COINBASE_PRICE_URL)
        r.raise_for_status()
        return float(r.json()["data"]["amount"])


async def get_15m_candles() -> pd.DataFrame:
    async with httpx.AsyncClient(timeout=30, headers={"user-agent": "Mozilla/5.0"}) as client:
        try:
            r = await client.get(YAHOO_15M_URL)
            r.raise_for_status()
            result = r.json()["chart"]["result"][0]
            timestamps = result.get("timestamp", [])
            quote = result["indicators"]["quote"][0]
            df = pd.DataFrame(
                {
                    "timestamp": pd.to_datetime(timestamps, unit="s"),
                    "open": quote.get("open", []),
                    "high": quote.get("high", []),
                    "low": quote.get("low", []),
                    "close": quote.get("close", []),
                    "volume": quote.get("volume", []),
                }
            )
            df = df.dropna(subset=["timestamp", "open", "high", "low", "close"])
            if len(df) >= 200:
                return df.tail(250).reset_index(drop=True)
        except Exception:
            pass

        r = await client.get(
            COINBASE_CANDLES_URL,
            params={"granularity": 900},
        )
        r.raise_for_status()
        raw = r.json()

    df = pd.DataFrame(raw, columns=["timestamp", "low", "high", "open", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["timestamp", "open", "high", "low", "close"])
    return df.sort_values("timestamp").tail(250).reset_index(drop=True)


def _bb_column(bb: pd.DataFrame, prefix: str) -> str:
    matches = [col for col in bb.columns if col.startswith(prefix)]
    if not matches:
        raise ValueError(f"Missing Bollinger Band column starting with {prefix}")
    return matches[0]


async def get_market_context() -> dict:
    """Fetch real-time market data, indicators, and all critical override signals."""
    async with httpx.AsyncClient(timeout=30) as client:
        df = await get_15m_candles()
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["open", "high", "low", "close", "volume"])
        if len(df) < 200:
            raise HTTPException(status_code=503, detail="Not enough BTC candle data")

        close  = df["close"]
        high   = df["high"]
        low    = df["low"]
        volume = df["volume"]

        rsi    = ta.rsi(close, length=14).iloc[-1]
        macd_r = ta.macd(close, fast=12, slow=26, signal=9)
        macd   = macd_r["MACD_12_26_9"].iloc[-1]
        macd_s = macd_r["MACDs_12_26_9"].iloc[-1]
        macd_h = macd_r["MACDh_12_26_9"].iloc[-1]
        ema20  = ta.ema(close, length=20).iloc[-1]
        ema50  = ta.ema(close, length=50).iloc[-1]
        ema200 = ta.ema(close, length=200).iloc[-1]
        bb     = ta.bbands(close, length=20, std=2)
        bb_u   = _bb_column(bb, "BBU")
        bb_l   = _bb_column(bb, "BBL")
        bb_m   = _bb_column(bb, "BBM")
        bb_w   = ((bb[bb_u] - bb[bb_l]) / bb[bb_m]).iloc[-1]
        atr    = ta.atr(high, low, close, length=14).iloc[-1]
        stoch  = ta.stoch(high, low, close, k=14, d=3)
        stk    = stoch["STOCHk_14_3_3"].iloc[-1]
        vol_sma = ta.sma(volume, length=20).iloc[-1]
        vol_r   = volume.iloc[-1] / vol_sma if vol_sma else 1.0
        price   = close.iloc[-1]

        # timestamp of the latest candle — used by freshness check
        latest_ts = df["timestamp"].iloc[-1]
        price_timestamp = (
            latest_ts.timestamp()
            if hasattr(latest_ts, "timestamp")
            else float(latest_ts)
        )

        context = {
            "price":            round(price, 2),
            "price_timestamp":  price_timestamp,
            "rsi_14":           round(rsi, 1),
            "macd":             round(macd, 2),
            "macd_signal":      round(macd_s, 2),
            "macd_hist":        round(macd_h, 2),
            "macd_bullish":     int(macd > macd_s),
            "ema_20":           round(ema20, 2),
            "ema_50":           round(ema50, 2),
            "ema_200":          round(ema200, 2),
            "above_ema200":     int(price > ema200),
            "above_ema50":      int(price > ema50),
            "ema_bullish":      int(ema20 > ema50),
            "bb_width":         round(bb_w, 4),
            "atr_14":           round(atr, 2),
            "stoch_k":          round(stk, 1),
            "volume_ratio":     round(vol_r, 2),
            "high_volume":      int(vol_r > 1.5),
            # critical override hooks — populated below
            "exchange_hack_alert": None,
            "stablecoin_depeg":    None,
        }

        # Fear & Greed (daily, lightweight API call)
        try:
            fg = await client.get("https://api.alternative.me/fng/?limit=1&format=json")
            fg_data = fg.json()["data"][0]
            context["fear_greed_index"] = int(fg_data["value"])
            context["fear_greed_label"] = fg_data["value_classification"]
        except Exception:
            context["fear_greed_index"] = None
            context["fear_greed_label"] = "Unknown"

        # Daily context — derivatives, macro, market structure from existing CSVs
        context.update(_load_daily_context())

        # Stablecoin depeg — live httpx price check
        depeg = await _get_stablecoin_status(client)
        if depeg:
            context["stablecoin_depeg"] = depeg
            log.warning("DEPEG DETECTED: %s", depeg)

        # Critical events — read from events.json (populated by background loop)
        # Also sets events_unavailable so risk_engine blocks BUY on any path
        hack_alert, events_depeg = _get_events_alert()
        if hack_alert:
            context["exchange_hack_alert"] = hack_alert
        if events_depeg and not context["stablecoin_depeg"]:
            context["stablecoin_depeg"] = events_depeg

        events_file = Path("data/raw/events.json")
        events_stale = (
            not events_file.exists()
            or (datetime.now().timestamp() - os.path.getmtime(events_file)) / 60
               > EVENTS_MAX_AGE_MINUTES
        )
        context["events_unavailable"] = events_stale

        return context


@app.post("/webhook")
async def tradingview_webhook(request: Request):
    payload = await request.json()

    if payload.get("secret") != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    context = await get_market_context()
    context["indicator_signal"] = payload.get("signal", "unknown")
    context["indicator"]        = payload.get("indicator", "TradingView")

    summary    = trader.portfolio_summary(context["price"])
    claude_out = brain.decide(context, summary)
    closed     = [t for t in trader.get_all_trades() if t["closed"]]
    final      = risk_engine.evaluate(claude_out, context, summary, closed)
    action     = final["action"]
    reason     = final["reason"]

    result = {
        "market_context":  context,
        "claude_opinion":  claude_out,
        "risk_engine":     {k: v for k, v in final.items() if k != "claude_opinion"},
        "final_action":    action,
        "confidence":      claude_out.get("confidence"),
    }

    if action == "BUY":
        result["trade"] = trader.buy(
            context["price"], reason,
            position_usd=final.get("position_usd"),
            stop_price=final.get("stop_price"),
        )
    elif action == "SELL":
        result["trade"] = trader.sell(context["price"], reason)

    trader.log_decision(
        context,
        claude_out,
        final,
        bool(result.get("trade")) and "error" not in result["trade"] and "blocked" not in result["trade"],
        trigger="webhook",
    )

    return result


@app.post("/scan")
async def manual_scan():
    """Manually trigger a market scan — no TradingView needed."""
    context    = await get_market_context()
    price      = context["price"]
    atr        = context.get("atr_14", 0)

    stops      = trader.check_trailing_stops(price, atr)
    summary    = trader.portfolio_summary(price)
    claude_out = brain.decide(context, summary)
    closed     = [t for t in trader.get_all_trades() if t["closed"]]
    final      = risk_engine.evaluate(claude_out, context, summary, closed)
    action     = final["action"]
    reason     = final["reason"]

    result = {
        "market_context":    context,
        "trailing_stops":    stops,
        "claude_opinion":    claude_out,
        "risk_engine":       {k: v for k, v in final.items() if k != "claude_opinion"},
        "final_action":      action,
    }

    if action == "BUY":
        result["trade"] = trader.buy(
            price, reason,
            position_usd=final.get("position_usd"),
            stop_price=final.get("stop_price"),
        )
    elif action == "SELL":
        result["trade"] = trader.sell(price, reason)

    trader.log_decision(
        context,
        claude_out,
        final,
        bool(result.get("trade")) and "error" not in result["trade"] and "blocked" not in result["trade"],
        trigger="manual",
    )

    return result


@app.get("/portfolio")
async def portfolio():
    price = await get_btc_price()
    return trader.portfolio_summary(price)


@app.get("/trades")
async def trades():
    return trader.get_all_trades()


@app.get("/decisions")
async def decisions():
    """Full decision log — every scan: what Claude said, what risk engine did, why."""
    rows = trader.get_decisions(limit=200)
    total = len(rows)
    if total == 0:
        return {"message": "No decisions logged yet. Run a scan first.", "decisions": []}

    claude_buys  = sum(1 for r in rows if r["claude_action"] == "BUY")
    claude_sells = sum(1 for r in rows if r["claude_action"] == "SELL")
    claude_holds = sum(1 for r in rows if r["claude_action"] == "HOLD")
    executed     = sum(1 for r in rows if r["trade_executed"])
    blocked      = sum(1 for r in rows if r["blocked_by"])

    block_counts: dict = {}
    trigger_counts: dict = {}
    for r in rows:
        trigger = r.get("trigger") or "unknown"
        trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
        if r["blocked_by"]:
            block_counts[r["blocked_by"]] = block_counts.get(r["blocked_by"], 0) + 1

    return {
        "summary": {
            "total_scans":    total,
            "claude_buy":     claude_buys,
            "claude_sell":    claude_sells,
            "claude_hold":    claude_holds,
            "trades_executed": executed,
            "blocked_by_risk_engine": blocked,
            "block_breakdown": block_counts,
            "trigger_breakdown": trigger_counts,
            "execution_rate_pct": round(executed / total * 100, 1) if total else 0,
        },
        "decisions": rows,
    }


@app.get("/performance")
async def performance():
    price      = await get_btc_price()
    summary    = trader.portfolio_summary(price)
    all_trades = trader.get_all_trades()
    closed     = [t for t in all_trades if t["closed"] and t["pnl"] is not None]

    if not closed:
        return {
            "verdict": "No closed trades yet — check back after first trades complete",
            "portfolio": summary,
        }

    wins   = [t["pnl"] for t in closed if t["pnl"] > 0]
    losses = [t["pnl"] for t in closed if t["pnl"] <= 0]

    avg_win  = round(sum(wins)   / len(wins),   2) if wins   else 0
    avg_loss = round(sum(losses) / len(losses), 2) if losses else 0
    rr_ratio = round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0

    win_rate = summary["win_rate_pct"]

    # is the strategy profitable? need win_rate > 1/(1+rr_ratio)
    breakeven_wr = round(1 / (1 + rr_ratio) * 100, 1) if rr_ratio else 50.0
    profitable   = win_rate > breakeven_wr

    verdict = (
        f"PROFITABLE — win rate {win_rate}% beats breakeven {breakeven_wr}%"
        if profitable else
        f"NOT PROFITABLE — win rate {win_rate}% below breakeven {breakeven_wr}%. "
        f"Need either higher win rate OR bigger wins vs losses."
    )

    return {
        "verdict":              verdict,
        "profitable":           profitable,
        "total_trades":         len(closed),
        "wins":                 len(wins),
        "losses":               len(losses),
        "win_rate_pct":         win_rate,
        "avg_win_usd":          avg_win,
        "avg_loss_usd":         avg_loss,
        "reward_risk_ratio":    rr_ratio,
        "breakeven_win_rate":   breakeven_wr,
        "total_profit_usd":     round(sum(t["pnl"] for t in closed), 2),
        "best_trade_usd":       round(max(t["pnl"] for t in closed), 2),
        "worst_trade_usd":      round(min(t["pnl"] for t in closed), 2),
        "portfolio":            summary,
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    with open("dashboard.html") as f:
        return f.read()
