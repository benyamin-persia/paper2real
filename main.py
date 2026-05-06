import asyncio
import csv
import io
import json
import logging
import os
import re
import zipfile
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import httpx
import pandas as pd
import pandas_ta as ta
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

import trader
import brain
import risk_engine
import notifier
import decision_evaluator
import trade_quality
import trade_quality_sweep
import smart_money
import daily_validation_report
from data.collector import live_btc
from data.collector import events as events_collector
from config import (
    WEBHOOK_SECRET,
    SMART_MONEY_ENABLED,
    TRADE_QUALITY_BUY_THRESHOLD,
    TRADE_QUALITY_CAN_PROPOSE_BUY,
    STRATEGY_VERSION,
)

EVENTS_REFRESH_MINUTES = 15    # how often to re-scrape CryptoPanic
EVENTS_MAX_AGE_MINUTES = 20    # older than this → treat as missing
MASTER_DATASET_MAX_AGE_HOURS = 36  # warn if training data is very stale
PRICE_MAX_AGE_MINUTES = 20     # warn if latest candle is old
LIVE_CANDLES_FILE = Path("data/raw/live_btc_15m.csv")
LIVE_BTC_STATUS_FILE = Path("data/raw/live_btc_source_status.json")
EVALUATOR_REFRESH_MINUTES = 60  # refresh AI feedback from completed decisions
SCHEDULED_SCAN_COOLDOWN_MINUTES = 30

TWITTER_REFRESH_MINUTES = 30   # how often to re-scrape Tier 1 Twitter accounts
TWITTER_MAX_AGE_MINUTES = 60   # older than this → mark unavailable
TWITTER_TWEET_MAX_AGE_HOURS = 24  # only recent tweets are useful live context

_TWITTER_ALERT_KEYWORDS = {
    "ban", "bans", "banned", "hack", "hacked", "exploit", "breach", "seized",
    "insolvent", "bankrupt", "collapse", "depeg", "emergency", "shutdown",
    "arrested", "indicted", "enforcement action", "cease and desist",
    "sec sues", "cftc charges", "doj", "criminal charges",
    "exchange down", "exchange halted", "trading suspended",
}


def _twitter_keyword_matches(text: str) -> list[str]:
    lower = (text or "").lower()
    matches: list[str] = []
    for kw in sorted(_TWITTER_ALERT_KEYWORDS, key=len, reverse=True):
        if " " in kw:
            if kw in lower:
                matches.append(kw)
        elif re.search(rf"\b{re.escape(kw)}\b", lower):
            matches.append(kw)
    return matches


def _build_candidate_decision(context: dict, claude_out: dict) -> tuple[dict, dict, dict]:
    """Build a clean BUY/HOLD candidate without mutating Claude's original decision."""
    pre_risk_tq = trade_quality.score(context, claude_out.get("historical_summary"), {})
    score = float(pre_risk_tq.get("score") or 0)
    claude_action = (claude_out.get("action") or "HOLD").upper()
    claude_conf = int(claude_out.get("confidence") or 0)

    candidate = {
        "action": "HOLD",
        "source": "none",
        "confidence": claude_conf,
        "reason": claude_out.get("reason") or "",
    }

    if claude_action == "BUY" and claude_conf >= 60:
        candidate.update(
            {
                "action": "BUY",
                "source": "claude",
                "reason": claude_out.get("reason") or "",
            }
        )

    if TRADE_QUALITY_CAN_PROPOSE_BUY and score >= TRADE_QUALITY_BUY_THRESHOLD:
        if candidate["action"] == "BUY":
            candidate["source"] = "both"
        else:
            candidate["action"] = "BUY"
            candidate["source"] = "trade_quality"
            candidate["confidence"] = max(claude_conf, 65)
            candidate["reason"] = (
                f"Trade Quality Score {score}/100 is above BUY threshold {TRADE_QUALITY_BUY_THRESHOLD}. "
                f"Primary reason: {pre_risk_tq.get('primary_reason')}. "
                f"Original Claude {claude_action} reason: {claude_out.get('reason', '')}"
            )[:700]

    risk_input_decision = {
        "action": candidate["action"],
        "confidence": candidate["confidence"],
        "reason": candidate["reason"],
        "risk_summary": claude_out.get("risk_summary"),
        "invalid_if": claude_out.get("invalid_if"),
        "historical_summary": claude_out.get("historical_summary"),
        "_audit": claude_out.get("_audit"),
        "_api_usage": claude_out.get("_api_usage"),
    }
    return pre_risk_tq, candidate, risk_input_decision


def _classify_twitter_alert(text: str) -> tuple[str, bool]:
    lower = (text or "").lower()
    btc_terms = {"bitcoin", "btc", "$btc", "satoshi", "bitcoin etf", "spot bitcoin"}
    exchange_terms = {"binance", "coinbase", "kraken", "okx", "bybit", "gemini", "withdrawals", "halted"}
    stable_terms = {"usdt", "usdc", "tether", "stablecoin", "depeg", "peg"}
    regulatory_terms = {"sec", "cftc", "doj", "treasury", "irs", "fincen", "ban", "lawsuit", "enforcement", "etf approved", "etf rejected"}
    macro_terms = {"fed", "fomc", "cpi", "inflation", "rates", "treasury yield", "jobs report"}
    security_terms = {"hack", "exploit", "breach", "compromised", "stolen", "drained"}

    if any(t in lower for t in stable_terms) and any(t in lower for t in {"depeg", "peg", "below $1", "lost peg"}):
        return "STABLECOIN_RISK", True
    if any(t in lower for t in exchange_terms) and any(t in lower for t in security_terms | {"withdrawals", "halted", "bankrupt", "insolvent"}):
        return "EXCHANGE_RISK", True
    if any(t in lower for t in btc_terms):
        return "BTC_DIRECT", True
    if any(t in lower for t in regulatory_terms) and any(t in lower for t in {"crypto", "bitcoin", "btc", "exchange", "stablecoin", "etf"}):
        return "REGULATORY_CRYPTO", True
    if any(t in lower for t in macro_terms):
        return "MACRO_MARKET", False
    if any(t in lower for t in security_terms) and any(t in lower for t in {"crypto", "defi", "protocol", "wallet", "chain"}):
        return "CRYPTO_SECURITY", False
    return "IRRELEVANT", False


def _tweet_sentiment(text: str) -> dict:
    lower = (text or "").lower()
    bullish = {
        "approved", "approval", "buy", "bought", "bull", "bullish", "adopt",
        "reserve", "inflow", "ath", "surge", "rally", "support", "accumulate",
    }
    bearish = {
        "ban", "banned", "hack", "hacked", "exploit", "sell", "sold", "bear",
        "bearish", "fraud", "lawsuit", "sues", "collapse", "bankrupt", "depeg",
        "outflow", "crash", "seized",
    }
    pos = sum(1 for w in bullish if re.search(rf"\b{re.escape(w)}\b", lower))
    neg = sum(1 for w in bearish if re.search(rf"\b{re.escape(w)}\b", lower))
    score = max(-100, min(100, (pos - neg) * 25))
    label = "bullish" if score > 0 else "bearish" if score < 0 else "neutral"
    return {"sentiment_score": score, "sentiment_label": label, "positive_hits": pos, "negative_hits": neg}


def _tweet_engagement(row: dict) -> dict:
    comments = int(row.get("comments") or row.get("replies") or 0)
    retweets = int(row.get("retweets") or row.get("reposts") or 0)
    quotes = int(row.get("quotes") or 0)
    likes = int(row.get("likes") or 0)
    bookmarks = int(row.get("bookmarks") or 0)
    views = int(row.get("views") or 0)
    raw = likes + (2 * retweets) + (2 * quotes) + (3 * comments) + (3 * bookmarks)
    rate = round(raw / views * 1000, 2) if views > 0 else 0.0
    score = min(100.0, round((raw ** 0.5) + min(35, rate * 2) + min(25, views ** 0.25), 2))
    return {
        "engagement_raw": raw,
        "engagement_rate_per_1k_views": rate,
        "impact_score": score,
    }


def _json_list(value) -> list:
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _safe_json_records(df: pd.DataFrame) -> list[dict]:
    """Return JSON-safe records with NaN/Inf converted to null."""
    if df is None or df.empty:
        return []
    clean = df.replace([float("inf"), float("-inf")], pd.NA)
    return json.loads(clean.to_json(orient="records", date_format="iso"))


def _read_json_file(path: str | Path, fallback=None):
    p = Path(path)
    if not p.exists():
        return fallback
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _save_live_candles(df: pd.DataFrame) -> None:
    """Cache latest live 15m candles so decision_evaluator.py can score outcomes."""
    try:
        LIVE_CANDLES_FILE.parent.mkdir(parents=True, exist_ok=True)
        out = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
        out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
        out = out.dropna(subset=["timestamp", "close"])
        out.to_csv(LIVE_CANDLES_FILE, index=False)
    except Exception as e:
        log.warning("Could not save live candle cache: %s", e)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("paper2real")
LOG_BUFFER = deque(maxlen=500)


class _DashboardLogHandler(logging.Handler):
    def emit(self, record):
        try:
            LOG_BUFFER.append(
                {
                    "time": datetime.fromtimestamp(record.created).isoformat(timespec="seconds"),
                    "level": record.levelname,
                    "message": self.format(record),
                }
            )
        except Exception:
            pass


_dash_handler = _DashboardLogHandler()
_dash_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S"))
log.addHandler(_dash_handler)

SCAN_INTERVAL_HOURS = 4
EVENT_MOVE_TRIGGER_PCT = 2.0
EVENT_SCAN_CHECK_MINUTES = 5
EVENT_SCAN_COOLDOWN_MINUTES = 30
EVENT_SCAN_MAX_PER_DAY = 3
SCAN_LOCK = asyncio.Lock()


async def _notify_scan_result(trigger: str, context: dict, claude_out: dict, final: dict, trade_result: dict | None = None):
    blocked = final.get("blocked_by")
    trade_executed = bool(trade_result and "error" not in trade_result and "blocked" not in trade_result)
    severity = "INFO"
    event_type = "scan_completed"
    if blocked:
        severity = "WARNING"
        event_type = "trade_blocked_by_risk_engine"
    if trade_executed:
        severity = "CRITICAL"
        event_type = "trade_executed"
    msg = (
        f"BTC: ${context.get('price', 0):,.2f}\n"
        f"Claude: {claude_out.get('action')} {claude_out.get('confidence')}%\n"
        f"Final: {final.get('action')}\n"
        f"Reason: {final.get('reason') or claude_out.get('reason')}\n"
        f"Risk block: {blocked or 'none'}"
    )
    await notifier.notify(
        severity,
        event_type,
        msg,
        source=trigger,
        status_text="executed" if trade_executed else "blocked" if blocked else "completed",
        metadata={
            "price": context.get("price"),
            "rsi": context.get("rsi_14"),
            "fear_greed": context.get("fear_greed_index"),
            "final_action": final.get("action"),
            "blocked_by": blocked,
            "position_usd": final.get("position_usd"),
            "api_cost_today": trader.api_usage_summary().get("today_cost_usd"),
        },
    )


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
    if context.get("volume_quality") != "reliable":
        issues.append("WARNING: Live BTC volume is unreliable - volume_ratio ignored as bearish evidence")
    if (context.get("live_btc_source_status") or {}).get("buy_block"):
        issues.append("BUY_BLOCK: Live BTC provider is using cached candles - blocking new BUY")

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
            await notifier.notify(
                "CRITICAL" if w.startswith("CRITICAL") else "WARNING",
                "data_freshness_failure" if w.startswith(("CRITICAL", "BUY_BLOCK")) else "data_freshness_warning",
                w,
                source="freshness_check",
                status_text="failed" if w.startswith("CRITICAL") else "warning",
                metadata={"trigger": trigger, "price": context.get("price")},
            )
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
            await notifier.notify(
                "CRITICAL",
                "trailing_stop_hit",
                f"Trailing stop closed trade at ${price:,.2f}. P&L: ${s.get('pnl_usd', '?')}",
                source="trailing_stop",
                status_text="executed",
                metadata=s,
            )

        # 3. Run brain → risk engine → execute
        summary    = trader.portfolio_summary(price)
        claude_out = brain.decide(context, summary)
        pre_risk_tq, candidate, risk_input_decision = _build_candidate_decision(context, claude_out)
        context["pre_risk_trade_quality"] = pre_risk_tq
        closed     = [t for t in trader.get_all_trades() if t["closed"]]
        final      = risk_engine.evaluate(risk_input_decision, context, summary, closed)
        post_risk_tq = trade_quality.score(context, claude_out.get("historical_summary"), final)
        context["post_risk_trade_quality"] = post_risk_tq
        context["trade_quality"] = post_risk_tq

        action  = final["action"]
        reason  = final["reason"]
        blocked = final.get("blocked_by")
        conf    = candidate.get("confidence", 0)

        log.info(
            "SCAN | BTC=$%s  RSI=%.1f  F&G=%s | Claude=%s(%s%%) → Final=%s%s — %s",
            f"{price:,.0f}",
            context["rsi_14"],
            context.get("fear_greed_index", "?"),
            f"{claude_out.get('action', '?')}->{candidate.get('action', '?')}/{candidate.get('source', '?')}",
            conf,
            action,
            f" [blocked:{blocked}]" if blocked else "",
            reason[:120],
        )

        trade_executed = False
        result = None
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

        trader.log_decision(
            context,
            claude_out,
            final,
            trade_executed,
            trigger=trigger,
            candidate=candidate,
            pre_risk_tq=pre_risk_tq,
            post_risk_tq=post_risk_tq,
            strategy_version=STRATEGY_VERSION,
        )
        await _notify_scan_result(trigger, context, risk_input_decision, final, result)

    except Exception as e:
        log.error("Scan failed: %s", e)
        await notifier.notify("CRITICAL", "app_scan_failed", f"Scan failed: {e}", source=trigger, status_text="failed")


async def _auto_scan_loop():
    """Background loop — scans every SCAN_INTERVAL_HOURS hours."""
    log.info("Auto-scan started — interval: %sh", SCAN_INTERVAL_HOURS)
    while True:
        recent = trader.get_decisions(limit=1)
        last_ts = recent[0]["timestamp"] if recent else 0
        age_min = (datetime.now().timestamp() - last_ts) / 60 if last_ts else None
        if age_min is not None and age_min < SCHEDULED_SCAN_COOLDOWN_MINUTES:
            log.info(
                "Scheduled scan skipped - last scan %.1f min ago (cooldown %s min)",
                age_min,
                SCHEDULED_SCAN_COOLDOWN_MINUTES,
            )
        else:
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
                    await notifier.notify(
                        "WARNING",
                        "price_move_trigger",
                        f"BTC moved {move_pct:.2f}% in about 30 minutes. Emergency scan triggered.",
                        source="event_price_move_loop",
                        status_text="triggered",
                        metadata={"old_price": old_price, "new_price": new_price, "move_pct": round(move_pct, 3)},
                    )
                    await _run_scan(trigger="event_price_move")
                    scans_today += 1
                    last_event_scan_ts = datetime.now().timestamp()
        except Exception as e:
            log.error("Event-driven scan check failed: %s", e)
            await notifier.notify("WARNING", "scraper_failure", f"Event-driven scan check failed: {e}", source="event_price_move_loop", status_text="failed")

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
                    await notifier.notify(
                        "CRITICAL",
                        "critical_market_alert",
                        f"{alert.get('alert_type')}: {alert.get('headline')}",
                        source="events_collector",
                        status_text="active",
                        metadata=alert,
                    )
            else:
                log.info("Events refreshed — no critical alerts")
        except Exception as e:
            log.error("Events refresh failed: %s", e)
            await notifier.notify("WARNING", "scraper_failure", f"Events refresh failed: {e}", source="events_collector", status_text="failed")
        await asyncio.sleep(EVENTS_REFRESH_MINUTES * 60)


async def _twitter_refresh_loop():
    """Background task — scrapes Tier 1 Twitter accounts every TWITTER_REFRESH_MINUTES."""
    log.info("Twitter refresh loop started — interval: %sm", TWITTER_REFRESH_MINUTES)

    try:
        import argparse as _ap
        from data.collector.twitter_playwright import run as _twitter_run
    except ImportError:
        log.warning("twitter_playwright not importable — Twitter refresh loop disabled")
        return

    args = _ap.Namespace(
        account=None,
        tier="tier1",
        workers=4,
        max_tweets=4,
        max_scrolls=5,
        timeout_ms=30000,
        no_retry_missing=False,
        skip_pinned=False,
        no_detail_hydration=False,
        hydrate_all_details=True,
        hydrate_media_details=True,
        block_images=False,
        headed=False,
    )

    while True:
        try:
            data = await _twitter_run(args)
            total = data.get("tweets_total", 0)
            # check for alert keywords in fresh tweets
            alert_tweets = [
                (acc.get("handle", "?"), tw.get("text", ""))
                for acc in data.get("results", [])
                for tw in acc.get("tweets", [])
                if _twitter_keyword_matches(tw.get("text", ""))
            ]
            if alert_tweets:
                for handle, text in alert_tweets[:5]:
                    category, trading_relevant = _classify_twitter_alert(text)
                    log.warning("TWITTER ALERT [%s]: @%s: %s", category, handle, text[:120])
                    if trading_relevant:
                        await notifier.notify(
                            "WARNING",
                            "critical_market_alert",
                            f"Twitter alert [{category}] @{handle}: {text[:500]}",
                            source="twitter_playwright",
                            status_text="active",
                            metadata={"category": category, "trading_relevant": trading_relevant},
                        )
            else:
                log.info("Twitter refreshed — %d tweets, no alerts", total)
        except Exception as e:
            log.error("Twitter refresh failed: %s", e)
            await notifier.notify("WARNING", "scraper_failure", f"Twitter refresh failed: {e}", source="twitter_playwright", status_text="failed")
        await asyncio.sleep(TWITTER_REFRESH_MINUTES * 60)


async def _summary_notification_loop():
    """Periodic Telegram summaries. Local event is recorded even if Telegram is disabled."""
    await asyncio.sleep(60)
    last_week = None
    while True:
        try:
            price = await get_btc_price()
            portfolio = trader.portfolio_summary(price)
            usage = trader.api_usage_summary()
            perf = {
                "portfolio": portfolio.get("total_portfolio_usd"),
                "return_pct": portfolio.get("return_pct"),
                "open_trades": portfolio.get("open_trades"),
                "api_cost_today": usage.get("today_cost_usd"),
                "api_cost_month": usage.get("month_cost_usd"),
                "api_calls_today": usage.get("today_calls"),
            }
            await notifier.notify(
                "INFO",
                "daily_summary",
                (
                    f"Daily Paper2Real summary\n"
                    f"Portfolio: ${portfolio.get('total_portfolio_usd', 0):,.2f}\n"
                    f"Return: {portfolio.get('return_pct')}%\n"
                    f"Open trades: {portfolio.get('open_trades')}\n"
                    f"API cost today: ${usage.get('today_cost_usd', 0):.4f}\n"
                    f"API cost month: ${usage.get('month_cost_usd', 0):.4f}"
                ),
                source="summary_loop",
                status_text="completed",
                metadata=perf,
            )
            week = datetime.utcnow().isocalendar().week
            if week != last_week and datetime.utcnow().weekday() == 0:
                last_week = week
                await notifier.notify("INFO", "weekly_summary", "Weekly Paper2Real summary generated.", source="summary_loop", status_text="completed", metadata=perf)
        except Exception as e:
            log.error("Summary notification failed: %s", e)
        await asyncio.sleep(24 * 3600)


async def _decision_evaluator_loop():
    """Keep the AI feedback report fresh so future Claude prompts can use it."""
    await asyncio.sleep(120)
    while True:
        try:
            summary = await asyncio.to_thread(decision_evaluator.run)
            await asyncio.to_thread(trade_quality_sweep.run)
            await notifier.notify(
                "INFO",
                "ai_feedback_refreshed",
                (
                    f"AI feedback refreshed: {summary.get('decisions_total', 0)} decisions, "
                    f"{summary.get('rows_scored', 0)} scored outcome rows."
                ),
                source="decision_evaluator",
                status_text="completed",
                metadata={
                    "decisions_total": summary.get("decisions_total"),
                    "rows_scored": summary.get("rows_scored"),
                    "rows_pending": summary.get("rows_pending"),
                    "recommendation": summary.get("recommendation"),
                },
            )
        except Exception as e:
            log.error("Decision evaluator failed: %s", e)
            await notifier.notify("WARNING", "scraper_failure", f"Decision evaluator failed: {e}", source="decision_evaluator", status_text="failed")
        await asyncio.sleep(EVALUATOR_REFRESH_MINUTES * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await notifier.notify("INFO", "app_startup", "Paper2Real app started.", source="lifespan", status_text="started")
    scan_task        = asyncio.create_task(_auto_scan_loop())
    events_task      = asyncio.create_task(_events_refresh_loop())
    event_scan_task  = asyncio.create_task(_event_price_move_loop())
    twitter_task     = asyncio.create_task(_twitter_refresh_loop())
    summary_task     = asyncio.create_task(_summary_notification_loop())
    evaluator_task   = asyncio.create_task(_decision_evaluator_loop())
    yield
    await notifier.notify("INFO", "app_shutdown", "Paper2Real app shutting down.", source="lifespan", status_text="shutdown")
    scan_task.cancel()
    events_task.cancel()
    event_scan_task.cancel()
    twitter_task.cancel()
    summary_task.cancel()
    evaluator_task.cancel()


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


def _get_twitter_context() -> dict:
    """
    Reads cached twitter_playwright.json written by the background refresh loop.
    Returns scored alert tweets + recent context tweets from Tier 1 accounts.
    twitter_unavailable=True if file is missing or older than TWITTER_MAX_AGE_MINUTES.
    """
    _empty = {"twitter_unavailable": True, "twitter_alerts": [], "twitter_recent": [],
               "twitter_last_updated": None, "twitter_accounts_scraped": 0}

    twitter_file = Path("data/raw/twitter_playwright.json")
    if not twitter_file.exists():
        return _empty

    age_minutes = (datetime.now().timestamp() - os.path.getmtime(twitter_file)) / 60
    if age_minutes > TWITTER_MAX_AGE_MINUTES:
        return {**_empty, "twitter_age_minutes": round(age_minutes)}

    try:
        data = json.loads(twitter_file.read_text(encoding="utf-8"))
    except Exception:
        return _empty

    alerts: list[dict] = []
    recent: list[dict] = []
    seen: set[str] = set()
    newest_allowed_ts = datetime.now().timestamp() - (TWITTER_TWEET_MAX_AGE_HOURS * 3600)

    for account in data.get("results", []):
        handle = account.get("handle", "")
        for tweet in account.get("tweets", []):
            text = (tweet.get("text") or "").strip()
            if not text or text in seen:
                continue
            ts = tweet.get("timestamp", "")
            if ts:
                try:
                    tweet_ts = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                    if tweet_ts < newest_allowed_ts:
                        continue
                except ValueError:
                    continue
            seen.add(text)
            row = {
                "handle": handle,
                "text": text,
                "timestamp": ts,
                "url": tweet.get("url", ""),
                "is_pinned": tweet.get("is_pinned", 0),
                "comments": tweet.get("comments", tweet.get("replies", 0)),
                "replies": tweet.get("replies", 0),
                "likes": tweet.get("likes", 0),
                "retweets": tweet.get("retweets", 0),
                "reposts": tweet.get("reposts", 0),
                "quotes": tweet.get("quotes", 0),
                "views": tweet.get("views", 0),
                "bookmarks": tweet.get("bookmarks", 0),
            }
            matched = _twitter_keyword_matches(text)
            if matched:
                row["alert_keywords"] = matched
                alerts.append(row)
            else:
                recent.append(row)

    return {
        "twitter_unavailable": False,
        "twitter_alerts": alerts[:10],
        "twitter_recent": recent[:10],
        "twitter_last_updated": data.get("finished_at"),
        "twitter_accounts_scraped": data.get("accounts_with_tweets", 0),
        "twitter_age_minutes": round(age_minutes),
    }


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
    return await live_btc.get_live_candles()


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
        _save_live_candles(df)

        close  = df["close"]
        high   = df["high"]
        low    = df["low"]
        volume = df["volume"]
        zero_volume_ratio = float((volume.fillna(0) <= 0).mean())
        recent_zero_volume_ratio = float((volume.tail(50).fillna(0) <= 0).mean())
        volume_quality = (
            "unreliable"
            if zero_volume_ratio > 0.10 or recent_zero_volume_ratio > 0.20
            else "reliable"
        )

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
        if volume_quality != "reliable":
            vol_r = None
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
            "live_candle_source": str(df.get("source", pd.Series(["unknown"])).iloc[-1]) if "source" in df.columns else "unknown",
            "live_btc_source_status": live_btc.read_status(),
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
            "volume_ratio":     round(vol_r, 2) if vol_r is not None else None,
            "high_volume":      int(vol_r is not None and vol_r > 1.5),
            "volume_quality":   volume_quality,
            "zero_volume_ratio": round(zero_volume_ratio, 3),
            "recent_zero_volume_ratio": round(recent_zero_volume_ratio, 3),
            # critical override hooks — populated below
            "exchange_hack_alert": None,
            "stablecoin_depeg":    None,
        }
        if (context["live_btc_source_status"] or {}).get("buy_block"):
            context["events_unavailable"] = True
            context.setdefault("data_warnings", []).append("Live BTC provider is using cached candles - blocking new BUY")

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

        # Smart Money Structure Layer. Evidence only; it never executes or bypasses risk_engine.
        if SMART_MONEY_ENABLED:
            try:
                sm = smart_money.analyze(df, context=context, save=True)
            except Exception as e:
                log.warning("Smart Money analysis failed: %s", e)
                sm = {
                    "smart_money_score": 0,
                    "smart_money_bias": "neutral",
                    "smart_money_reason": f"analysis_failed: {e}",
                    "structure_state": "unknown",
                    "liquidity_state": "unknown",
                    "order_block_state": "unknown",
                    "fvg_state": "unknown",
                    "premium_discount_state": "unknown",
                    "timeframe_alignment": "unknown",
                }
            context["smart_money"] = sm
            for key in (
                "smart_money_score",
                "smart_money_bias",
                "smart_money_reason",
                "structure_state",
                "liquidity_state",
                "order_block_state",
                "fvg_state",
                "premium_discount_state",
                "timeframe_alignment",
            ):
                context[key] = sm.get(key)

        # Tier 1 Twitter — read cached scrape output (written by background loop)
        context.update(_get_twitter_context())

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
    pre_risk_tq, candidate, risk_input_decision = _build_candidate_decision(context, claude_out)
    context["pre_risk_trade_quality"] = pre_risk_tq
    closed     = [t for t in trader.get_all_trades() if t["closed"]]
    final      = risk_engine.evaluate(risk_input_decision, context, summary, closed)
    post_risk_tq = trade_quality.score(context, claude_out.get("historical_summary"), final)
    context["post_risk_trade_quality"] = post_risk_tq
    context["trade_quality"] = post_risk_tq
    action     = final["action"]
    reason     = final["reason"]

    result = {
        "market_context":  context,
        "claude_opinion":  claude_out,
        "candidate_decision": candidate,
        "risk_engine":     {k: v for k, v in final.items() if k != "claude_opinion"},
        "final_action":    action,
        "confidence":      candidate.get("confidence"),
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
        candidate=candidate,
        pre_risk_tq=pre_risk_tq,
        post_risk_tq=post_risk_tq,
        strategy_version=STRATEGY_VERSION,
    )
    await _notify_scan_result("webhook", context, risk_input_decision, final, result.get("trade"))

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
    pre_risk_tq, candidate, risk_input_decision = _build_candidate_decision(context, claude_out)
    context["pre_risk_trade_quality"] = pre_risk_tq
    closed     = [t for t in trader.get_all_trades() if t["closed"]]
    final      = risk_engine.evaluate(risk_input_decision, context, summary, closed)
    post_risk_tq = trade_quality.score(context, claude_out.get("historical_summary"), final)
    context["post_risk_trade_quality"] = post_risk_tq
    context["trade_quality"] = post_risk_tq
    action     = final["action"]
    reason     = final["reason"]

    result = {
        "market_context":    context,
        "trailing_stops":    stops,
        "claude_opinion":    claude_out,
        "candidate_decision": candidate,
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
        candidate=candidate,
        pre_risk_tq=pre_risk_tq,
        post_risk_tq=post_risk_tq,
        strategy_version=STRATEGY_VERSION,
    )
    await _notify_scan_result("manual", context, risk_input_decision, final, result.get("trade"))

    return result


@app.get("/portfolio")
async def portfolio():
    price = await get_btc_price()
    return trader.portfolio_summary(price)


@app.get("/market-context")
async def market_context():
    """Live market context for the dashboard. No Claude call, no trade execution."""
    return await get_market_context()


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
    candidate_buys = sum(1 for r in rows if r.get("candidate_action") == "BUY")
    tq_candidate_buys = sum(1 for r in rows if r.get("candidate_source") in {"trade_quality", "both"})
    claude_candidate_buys = sum(1 for r in rows if r.get("candidate_source") in {"claude", "both"})
    risk_blocked_candidates = sum(1 for r in rows if int(r.get("risk_blocked_candidate") or 0) == 1)
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
            "candidate_buy":  candidate_buys,
            "candidate_buy_from_claude": claude_candidate_buys,
            "candidate_buy_from_trade_quality": tq_candidate_buys,
            "risk_blocked_candidates": risk_blocked_candidates,
            "trades_executed": executed,
            "blocked_by_risk_engine": blocked,
            "block_breakdown": block_counts,
            "trigger_breakdown": trigger_counts,
            "execution_rate_pct": round(executed / total * 100, 1) if total else 0,
        },
        "decisions": rows,
    }


@app.get("/ai-audit")
async def ai_audit(limit: int = 25):
    rows = trader.get_decisions(limit=limit)
    out = []
    for r in rows:
        item = dict(r)
        for key in ("invalid_if_json", "historical_summary_json", "trade_quality_json"):
            try:
                item[key.replace("_json", "")] = json.loads(item.get(key) or "null")
            except Exception:
                item[key.replace("_json", "")] = None
        item["note"] = (
            "This is the visible audit trail: model input, model output, final reason, "
            "historical evidence, and risk-engine result. Hidden chain-of-thought is not exposed."
        )
        out.append(item)
    return {"audits": out}


@app.get("/api-usage")
async def api_usage():
    return trader.api_usage_summary()


@app.get("/settings")
async def settings():
    return trader.get_settings()


@app.post("/settings")
async def update_settings(request: Request):
    payload = await request.json()
    return trader.update_settings(payload or {})


@app.get("/price-history")
async def price_history(limit: int = 250):
    def _num(v):
        if v is None or pd.isna(v):
            return None
        return float(v)

    path = LIVE_CANDLES_FILE if LIVE_CANDLES_FILE.exists() else Path("data/raw/btc_15m_raw.csv")
    if not path.exists():
        return {"source": None, "rows": []}
    df = pd.read_csv(path)
    if "timestamp" not in df.columns and "date" in df.columns:
        df = df.rename(columns={"date": "timestamp"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp", "close"]).sort_values("timestamp").tail(limit)
    df = df.where(pd.notna(df), None)
    return {
        "source": str(path),
        "count": len(df),
        "rows": [
            {
                "timestamp": r["timestamp"].isoformat(),
                "open": _num(r.get("open")),
                "high": _num(r.get("high")),
                "low": _num(r.get("low")),
                "close": _num(r.get("close")),
                "volume": _num(r.get("volume")),
            }
            for _, r in df.iterrows()
        ],
    }


@app.get("/twitter-data")
async def twitter_data(limit: int = 120):
    def _clean(value):
        if isinstance(value, dict):
            return {k: _clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_clean(v) for v in value]
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass
        return value

    json_file = Path("data/raw/twitter_playwright.json")
    csv_file = Path("data/raw/twitter_tweets.csv")
    meta = {}
    if json_file.exists():
        try:
            meta = json.loads(json_file.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
    rows = []
    if csv_file.exists():
        df = pd.read_csv(csv_file).tail(limit).astype(object)
        df = df.where(pd.notna(df), None)
        rows = df.to_dict(orient="records")
    elif meta.get("results"):
        for account in meta.get("results", []):
            for rank, tweet in enumerate(account.get("tweets", []), start=1):
                rows.append({"handle": account.get("handle"), "rank": rank, **tweet})
        rows = rows[-limit:]

    for row in rows:
        if row.get("full_text"):
            row["text"] = row["full_text"]
        row["media_urls"] = _json_list(row.get("media_urls"))
        row["media_alt_text"] = _json_list(row.get("media_alt_text"))
        text_for_sentiment = str(row.get("text") or "")
        media_alt = " ".join(str(x) for x in row.get("media_alt_text", []))
        row.update(_tweet_sentiment(" ".join([text_for_sentiment, media_alt])))
        if not row.get("impact_score"):
            row.update(_tweet_engagement(row))
        row["alert_keywords"] = _twitter_keyword_matches(row.get("text", ""))

    avg_sentiment = round(sum(r["sentiment_score"] for r in rows) / len(rows), 2) if rows else 0
    avg_impact = round(sum(float(r.get("impact_score") or 0) for r in rows) / len(rows), 2) if rows else 0
    return {
        "meta": _clean({
            "finished_at": meta.get("finished_at"),
            "accounts_total": meta.get("accounts_total"),
            "accounts_with_tweets": meta.get("accounts_with_tweets"),
            "tweets_total": meta.get("tweets_total", len(rows)),
            "workers": meta.get("workers"),
            "total_s": meta.get("total_s"),
            "avg_per_account_s": meta.get("avg_per_account_s"),
            "errors": meta.get("errors"),
            "avg_sentiment": avg_sentiment,
            "avg_impact_score": avg_impact,
            "bullish_count": sum(1 for r in rows if r["sentiment_score"] > 0),
            "bearish_count": sum(1 for r in rows if r["sentiment_score"] < 0),
            "neutral_count": sum(1 for r in rows if r["sentiment_score"] == 0),
        }),
        "tweets": _clean(rows),
    }


@app.get("/twitter-accounts")
async def twitter_accounts():
    data = await twitter_data(limit=5000)
    tweets = data.get("tweets", [])
    tiers_file = Path("data/raw/account_tiers.json")
    tiers = {}
    if tiers_file.exists():
        try:
            tiers = json.loads(tiers_file.read_text(encoding="utf-8"))
        except Exception:
            tiers = {}

    reasons = {
        "POTUS": "Official US President account; executive policy can move crypto risk sentiment.",
        "WhiteHouse": "Official White House policy announcements; regulation and executive orders.",
        "realDonaldTrump": "US President personal account; crypto policy and market sentiment impact.",
        "federalreserve": "Federal Reserve policy; rates and liquidity drive BTC risk appetite.",
        "SECGov": "SEC enforcement and ETF/regulatory announcements.",
        "USTreasury": "Treasury sanctions, tax, stablecoin, and financial policy.",
        "CFTC": "Derivatives regulator; crypto futures/enforcement relevance.",
        "TheJusticeDept": "DOJ enforcement; exchange/criminal cases can create market shocks.",
        "JPMorgan": "Major bank/institutional sentiment and custody/market commentary.",
        "BlackRock": "Largest asset manager; ETF and institutional Bitcoin flow signal.",
        "iShares": "BlackRock ETF brand; ETF flow and product announcements.",
        "Fidelity": "Major Bitcoin ETF/institutional custody provider.",
        "MicroStrategy": "Largest public corporate BTC treasury buyer.",
        "saylor": "Michael Saylor; MicroStrategy BTC strategy and market-moving commentary.",
        "binance": "Largest crypto exchange; outages, listings, enforcement, reserves.",
        "coinbase": "Major US exchange; regulatory and market structure signal.",
        "Grayscale": "Major crypto fund/ETF issuer.",
        "Tether": "USDT issuer; stablecoin liquidity and depeg/reserve relevance.",
        "paoloardoino": "Tether CEO; direct USDT liquidity/security statements.",
        "zachxbt": "Crypto security investigator; early hacks/scams/exploit alerts.",
        "PeckShieldAlert": "Security alerts for exploits, hacks, suspicious flows.",
        "SlowMist_Team": "Security intelligence and exploit alerts.",
        "CertiKAlert": "Security alerts and phishing/exploit monitoring.",
        "WuBlockchain": "Fast Asia/China crypto news; exchange/regulatory signal.",
    }
    tier_lookup = {}
    for name in tiers.get("tier1_permanent", []):
        tier_lookup[name] = "tier1_permanent"
    for name in tiers.get("tier2_roles", []):
        tier_lookup[name] = "tier2_roles"
    for name in tiers.get("tier3_dynamic", []):
        tier_lookup[name] = "tier3_dynamic"

    by_account = {}
    for t in tweets:
        handle = t.get("handle") or "unknown"
        row = by_account.setdefault(
            handle,
            {
                "handle": handle,
                "tier": tier_lookup.get(handle, "unknown"),
                "why_selected": reasons.get(handle, "Tracked because it is in account_tiers.json and may affect BTC sentiment, policy, security, liquidity, or market structure."),
                "extraction_frequency": f"Every {TWITTER_REFRESH_MINUTES} minutes for Tier 1 live scrape.",
                "data_extracted": ["tweet text", "timestamp", "url", "likes", "retweets/reposts", "comments/replies", "quotes", "views", "bookmarks", "local keyword sentiment", "alert keywords"],
                "paid_api_calls": 0,
                "paid_api_cost_usd": 0,
                "tweets": 0,
                "avg_sentiment": 0,
                "total_likes": 0,
                "total_retweets": 0,
                "total_comments": 0,
                "total_views": 0,
                "latest_tweet_time": None,
                "sentiment_series": [],
            },
        )
        row["tweets"] += 1
        row["total_likes"] += int(t.get("likes") or 0)
        row["total_retweets"] += int(t.get("retweets") or t.get("reposts") or 0)
        row["total_comments"] += int(t.get("comments") or t.get("replies") or 0)
        row["total_views"] += int(t.get("views") or 0)
        row["sentiment_series"].append(
            {
                "timestamp": t.get("timestamp"),
                "sentiment_score": t.get("sentiment_score", 0),
                "likes": t.get("likes") or 0,
                "retweets": t.get("retweets") or t.get("reposts") or 0,
                "comments": t.get("comments") or t.get("replies") or 0,
                "views": t.get("views") or 0,
            }
        )
        if t.get("timestamp") and (row["latest_tweet_time"] is None or str(t["timestamp"]) > str(row["latest_tweet_time"])):
            row["latest_tweet_time"] = t["timestamp"]

    for row in by_account.values():
        scores = [x["sentiment_score"] for x in row["sentiment_series"]]
        row["avg_sentiment"] = round(sum(scores) / len(scores), 2) if scores else 0
        row["api_usage_assessment"] = "normal: this uses Playwright scraping and local sentiment, not paid Twitter API or paid AI per account"

    return {
        "accounts": sorted(by_account.values(), key=lambda x: (x["tier"], x["handle"].lower())),
        "source_accounts": tiers,
        "summary": {
            "accounts_with_data": len(by_account),
            "twitter_paid_api_calls": 0,
            "twitter_paid_api_cost_usd": 0,
            "scrape_frequency_minutes": TWITTER_REFRESH_MINUTES,
            "note": "Twitter/X extraction does not call Claude per account. Only selected alert/recent tweets are included in the trade-decision prompt.",
        },
    }


@app.get("/logs")
async def logs(limit: int = 200):
    return {"logs": list(LOG_BUFFER)[-limit:]}


@app.get("/events")
async def events(limit: int = 200):
    return {"events": trader.get_events(limit=limit)}


def _table_csv_response(table: str, filename: str):
    allowed = {"decisions", "events", "trades"}
    if table not in allowed:
        raise HTTPException(status_code=404, detail="Unknown export")
    con = trader.sqlite3.connect(trader.DB_FILE)
    con.row_factory = trader.sqlite3.Row
    try:
        rows = con.execute(f"SELECT * FROM {table} ORDER BY id DESC").fetchall()
    finally:
        con.close()

    out = io.StringIO()
    if rows:
        writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows([dict(r) for r in rows])
    else:
        out.write("")
    return StreamingResponse(
        iter([out.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/download/paper-trader.db")
async def download_paper_trader_db():
    path = Path(trader.DB_FILE)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Database not found")
    return FileResponse(path, filename="paper_trader.db", media_type="application/octet-stream")


@app.get("/download/decisions.csv")
async def download_decisions_csv():
    return _table_csv_response("decisions", "paper2real_decisions.csv")


@app.get("/download/events.csv")
async def download_events_csv():
    return _table_csv_response("events", "paper2real_events.csv")


@app.get("/download/trades.csv")
async def download_trades_csv():
    return _table_csv_response("trades", "paper2real_trades.csv")


@app.get("/download/logs.json")
async def download_logs_json():
    data = json.dumps({"logs": list(LOG_BUFFER)}, indent=2)
    return StreamingResponse(
        iter([data]),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="paper2real_live_logs.json"'},
    )


@app.get("/download/all.zip")
async def download_all_artifacts():
    """Download safe audit/learning artifacts. Secrets and .env are intentionally excluded."""
    files = [
        "paper_trader.db",
        "data/reports/ai_feedback_summary.json",
        "data/reports/ai_feedback_summary.md",
        "data/reports/decision_evaluations.csv",
        "data/reports/backtest_latest.json",
        "data/reports/backtest_equity.csv",
        "data/reports/backtest_trades.csv",
        "data/reports/trade_quality_sweep.json",
        "data/reports/trade_quality_sweep.csv",
        "data/reports/risk_block_performance.json",
        "data/reports/risk_block_performance.csv",
        "data/reports/daily_validation_report.json",
        "data/reports/daily_validation_report.md",
        "data/reports/full_application_test_report.md",
        "data/reports/market_structure_events.csv",
        "data/reports/market_structure_events.json",
        "data/reports/liquidity_zones.csv",
        "data/reports/liquidity_zones.json",
        "data/reports/order_blocks.csv",
        "data/reports/order_blocks.json",
        "data/reports/fair_value_gaps.csv",
        "data/reports/fair_value_gaps.json",
        "data/reports/premium_discount_zones.csv",
        "data/reports/premium_discount_zones.json",
        "data/reports/smart_money_backtest.csv",
        "data/reports/smart_money_backtest.json",
        "data/reports/smart_money_summary.json",
        "data/raw/live_btc_15m.csv",
        "data/raw/live_btc_1h.csv",
        "data/raw/live_btc_4h.csv",
        "data/raw/live_btc_source_status.json",
        "data/raw/twitter_playwright.json",
        "data/raw/twitter_tweets.csv",
        "data/raw/twitter_timing.csv",
        "data/raw/events.json",
        "data/processed/master_dataset.csv",
        "data/processed/btc_15m_labeled.csv",
        "PAPER2REAL_IMPLEMENTATION_LOG.md",
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "excluded": [".env", "tokens", "API keys", "cookies", "private secrets"],
            "included_files": [],
        }
        for rel in files:
            path = Path(rel)
            if path.exists() and path.is_file():
                zf.write(path, rel)
                manifest["included_files"].append(rel)
        zf.writestr("runtime/live_logs.json", json.dumps({"logs": list(LOG_BUFFER)}, indent=2))
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="paper2real_audit_learning_artifacts.zip"'},
    )


@app.get("/telegram/status")
async def telegram_status():
    return notifier.status()


@app.post("/telegram/test")
async def telegram_test():
    return await notifier.notify(
        "INFO",
        "telegram_test",
        "Safe Paper2Real Telegram test message. No secrets included.",
        source="dashboard",
        status_text="test",
        metadata={"safe": True},
        force=True,
    )


@app.get("/risk-status")
async def risk_status():
    price = await get_btc_price()
    portfolio = trader.portfolio_summary(price)
    closed = [t for t in trader.get_all_trades() if t["closed"] and t["pnl"] is not None]
    last_decisions = trader.get_decisions(limit=50)
    consecutive_losses = 0
    for t in sorted(closed, key=lambda r: r["timestamp"], reverse=True):
        if t.get("pnl", 0) < 0:
            consecutive_losses += 1
        else:
            break
    today_start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    daily_pnl = sum(t.get("pnl", 0) for t in closed if t.get("timestamp", 0) >= today_start)
    recent_blocks = {}
    for d in last_decisions:
        if d.get("blocked_by"):
            recent_blocks[d["blocked_by"]] = recent_blocks.get(d["blocked_by"], 0) + 1
    return {
        "portfolio": portfolio,
        "daily_pnl": round(daily_pnl, 2),
        "daily_loss_pct": round(abs(min(daily_pnl, 0)) / portfolio.get("starting_balance", 10000) * 100, 2),
        "consecutive_losses": consecutive_losses,
        "recent_risk_blocks": recent_blocks,
        "open_trades": trader.get_open_trades(),
    }


@app.get("/system-health")
async def system_health():
    context = await get_market_context()
    issues = _check_data_freshness(context)
    files = {}
    for path in [
        "data/raw/events.json",
        "data/raw/twitter_playwright.json",
        "data/raw/live_btc_15m.csv",
        "data/raw/live_btc_source_status.json",
        "data/processed/master_dataset.csv",
        "data/reports/ai_feedback_summary.json",
    ]:
        p = Path(path)
        files[path] = {
            "exists": p.exists(),
            "age_minutes": round((datetime.now().timestamp() - os.path.getmtime(p)) / 60, 1) if p.exists() else None,
        }
    return {
        "status": "critical" if any(i.startswith("CRITICAL") for i in issues) else "warning" if issues else "ok",
        "issues": issues,
        "files": files,
        "telegram": notifier.status(),
    }


@app.get("/reports")
async def reports():
    def _read_json(path: str):
        p = Path(path)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    return {
        "backtest": _read_json("data/reports/backtest_latest.json"),
        "ai_feedback": _read_json("data/reports/ai_feedback_summary.json"),
        "trade_quality_sweep": _read_json("data/reports/trade_quality_sweep.json"),
        "risk_block_performance": _read_json("data/reports/risk_block_performance.json"),
        "smart_money": _read_json("data/reports/smart_money_summary.json"),
        "smart_money_backtest": _read_json("data/reports/smart_money_backtest.json"),
        "api_usage": trader.api_usage_summary(),
    }


@app.get("/daily-validation-report")
async def daily_validation_report_endpoint():
    path = Path("data/reports/daily_validation_report.json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return await asyncio.to_thread(daily_validation_report.run, False)


@app.get("/smart-money")
async def smart_money_report():
    path = Path("data/reports/smart_money_summary.json")
    if not path.exists() and LIVE_CANDLES_FILE.exists():
        try:
            df = pd.read_csv(LIVE_CANDLES_FILE)
            return smart_money.analyze(df, context={}, save=True)
        except Exception as e:
            return {"smart_money_score": 0, "smart_money_bias": "neutral", "smart_money_reason": f"analysis_failed: {e}"}
    return _read_json_file(path, {"smart_money_score": 0, "smart_money_bias": "neutral", "smart_money_reason": "not_available"})


@app.get("/market-structure")
async def market_structure_report():
    return _read_json_file("data/reports/market_structure_events.json", {"events": [], "count": 0})


@app.get("/liquidity-zones")
async def liquidity_zones_report():
    return _read_json_file("data/reports/liquidity_zones.json", {"zones": [], "count": 0})


@app.get("/order-blocks")
async def order_blocks_report():
    return _read_json_file("data/reports/order_blocks.json", {"order_blocks": [], "count": 0})


@app.get("/fair-value-gaps")
async def fair_value_gaps_report():
    return _read_json_file("data/reports/fair_value_gaps.json", {"fair_value_gaps": [], "count": 0})


@app.get("/premium-discount")
async def premium_discount_report():
    return _read_json_file("data/reports/premium_discount_zones.json", {"zones": [], "count": 0})


@app.get("/smart-money-backtest")
async def smart_money_backtest_report():
    path = Path("data/reports/smart_money_backtest.json")
    if not path.exists():
        import smart_money_backtest
        return await asyncio.to_thread(smart_money_backtest.run)
    return _read_json_file(path, {"summary": {}, "thresholds": []})


@app.get("/risk-block-performance")
async def risk_block_performance():
    path = Path("data/reports/risk_block_performance.json")
    if not path.exists():
        await asyncio.to_thread(decision_evaluator.run)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        await asyncio.to_thread(decision_evaluator.run)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {
            "total_blocked_candidates": 0,
            "minimum_required_before_tuning": 30,
            "ready_to_tune": False,
            "blockers": {},
        }


@app.get("/learning-status")
async def learning_status():
    """Live status of the feedback loop that turns paper scans into better prompts."""
    def _read_json(path: str):
        p = Path(path)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _age_minutes(path: str) -> float | None:
        p = Path(path)
        if not p.exists():
            return None
        return round((datetime.now().timestamp() - os.path.getmtime(p)) / 60, 1)

    decisions = trader.get_decisions(limit=1000)
    trades = trader.get_all_trades()
    events = trader.get_events(limit=1000)
    usage = trader.api_usage_summary()
    feedback = _read_json("data/reports/ai_feedback_summary.json") or {}
    risk_block_report = _read_json("data/reports/risk_block_performance.json") or {}
    eval_path = Path("data/reports/decision_evaluations.csv")

    latest_decision_ts = max((d.get("timestamp") or 0 for d in decisions), default=0)
    latest_decision_time = datetime.fromtimestamp(latest_decision_ts).isoformat() if latest_decision_ts else None
    feedback_decisions = int(feedback.get("decisions_total") or 0)
    evaluator_stale = bool(decisions and feedback_decisions < len(decisions))

    evaluation_rows = 0
    scored_rows = int(feedback.get("rows_scored") or 0)
    pending_rows = int(feedback.get("rows_pending") or 0)
    if eval_path.exists() and eval_path.stat().st_size > 0:
        try:
            evaluation_rows = int(len(pd.read_csv(eval_path)))
        except Exception:
            evaluation_rows = 0

    claude_buy = sum(1 for d in decisions if d.get("claude_action") == "BUY")
    claude_sell = sum(1 for d in decisions if d.get("claude_action") == "SELL")
    claude_hold = sum(1 for d in decisions if d.get("claude_action") == "HOLD")
    candidate_buy = sum(1 for d in decisions if d.get("candidate_action") == "BUY")
    smart_money_candidates = sum(1 for d in decisions if d.get("shadow_smart_money_action"))
    candidate_sources = {}
    for d in decisions:
        src = d.get("candidate_source") or "none"
        candidate_sources[src] = candidate_sources.get(src, 0) + 1
    risk_blocked_candidates = sum(1 for d in decisions if int(d.get("risk_blocked_candidate") or 0) == 1)
    executed = sum(1 for d in decisions if d.get("trade_executed"))
    blocked = sum(1 for d in decisions if d.get("blocked_by"))

    h4 = (feedback.get("horizons") or {}).get("4h") or {}
    risk = h4.get("risk_engine") or {}
    missed_summary = {"missed_upside_holds": 0, "avoided_downside_holds": 0}
    if eval_path.exists() and eval_path.stat().st_size > 0:
        try:
            eval_df = pd.read_csv(eval_path)
            scored_holds = eval_df[
                eval_df["status"].eq("SCORED")
                & eval_df["final_action"].astype(str).str.upper().eq("HOLD")
            ].copy()
            scored_holds["return_pct"] = pd.to_numeric(scored_holds["return_pct"], errors="coerce")
            missed_summary = {
                "scored_holds": int(len(scored_holds)),
                "missed_upside_holds": int((scored_holds["return_pct"] > 1.5).sum()),
                "avoided_downside_holds": int((scored_holds["return_pct"] < -1.5).sum()),
            }
        except Exception:
            pass
    status = "collecting"
    if not decisions:
        status = "waiting_for_decisions"
    elif evaluator_stale:
        status = "feedback_stale"
    elif scored_rows == 0:
        status = "waiting_for_future_price"
    elif scored_rows < 30:
        status = "low_sample_size"
    else:
        status = "learning_active"

    return {
        "status": status,
        "auto_refresh_minutes": EVALUATOR_REFRESH_MINUTES,
        "logs_used": {
            "paper_trader_db": "paper_trader.db",
            "decisions_table": len(decisions),
            "trades_table": len(trades),
            "events_table": len(events),
            "api_usage_source": "decisions.input_tokens/output_tokens/api_cost_usd",
        },
        "data_used": {
            "live_future_prices": "data/raw/live_btc_15m.csv",
            "historical_daily_prices": "data/raw/btc_15m_raw.csv",
            "master_dataset": "data/processed/master_dataset.csv",
            "twitter_context": "data/raw/twitter_playwright.json",
            "critical_events": "data/raw/events.json",
            "feedback_json": "data/reports/ai_feedback_summary.json",
            "feedback_csv": "data/reports/decision_evaluations.csv",
            "smart_money_summary": "data/reports/smart_money_summary.json",
            "smart_money_backtest": "data/reports/smart_money_backtest.json",
        },
        "decision_counts": {
            "total": len(decisions),
            "claude_buy": claude_buy,
            "claude_sell": claude_sell,
            "claude_hold": claude_hold,
            "candidate_buy": candidate_buy,
            "candidate_sources": candidate_sources,
            "risk_blocked_candidates": risk_blocked_candidates,
            "shadow_smart_money_candidates": smart_money_candidates,
            "ready_to_tune_risk_blocks": bool(risk_block_report.get("ready_to_tune")),
            "risk_blocked": blocked,
            "trades_executed": executed,
            "latest_decision_time": latest_decision_time,
        },
        "evaluation": {
            "feedback_decisions_total": feedback_decisions,
            "evaluation_rows": evaluation_rows,
            "rows_scored": scored_rows,
            "rows_pending": pending_rows,
            "evaluator_stale": evaluator_stale,
            "feedback_age_minutes": _age_minutes("data/reports/ai_feedback_summary.json"),
            "recommendation": feedback.get("recommendation"),
            "four_hour": {
                "claude_buy_accuracy_pct": h4.get("claude_buy_accuracy_pct"),
                "missed_upside_holds": h4.get("missed_upside_holds"),
                "risk_engine_saved_losses": risk.get("risk_engine_saved_losses"),
                "risk_engine_blocked_winners": risk.get("risk_engine_blocked_winners"),
            },
            "missed_opportunity": missed_summary,
        },
        "api_cost": {
            "total_calls": usage.get("total_calls"),
            "today_calls": usage.get("today_calls"),
            "today_cost_usd": usage.get("today_cost_usd"),
            "month_cost_usd": usage.get("month_cost_usd"),
        },
        "how_it_improves": [
            "Each scan writes Claude input/output, indicators, action, confidence, risk result, tokens, and cost to SQLite decisions.",
            "decision_evaluator.py compares those decisions against future BTC prices at 1h, 4h, and 24h.",
            "It writes ai_feedback_summary.json and decision_evaluations.csv under data/reports.",
            "brain.py reads ai_feedback_summary.json into the next Claude prompt, so future decisions see what worked or failed.",
            "The dashboard displays decisions, AI audit, reports, API usage, events, and this learning status.",
        ],
    }


@app.get("/missed-opportunities")
async def missed_opportunities(limit: int = 100):
    path = Path("data/reports/decision_evaluations.csv")
    if not path.exists() or path.stat().st_size == 0:
        return {"rows": [], "summary": {"missed_upside_holds": 0, "avoided_downside_holds": 0}}
    df = pd.read_csv(path)
    if df.empty:
        return {"rows": [], "summary": {"missed_upside_holds": 0, "avoided_downside_holds": 0}}
    scored = df[df.get("status").eq("SCORED")].copy()
    holds = scored[scored.get("final_action").astype(str).str.upper().eq("HOLD")].copy()
    holds["return_pct"] = pd.to_numeric(holds["return_pct"], errors="coerce")
    missed = holds[holds["return_pct"] > 1.5].sort_values("return_pct", ascending=False)
    avoided = holds[holds["return_pct"] < -1.5].sort_values("return_pct")
    avg_hold = holds["return_pct"].mean() if len(holds) else None
    avg_hold = None if pd.isna(avg_hold) else round(float(avg_hold), 4)
    return {
        "summary": {
            "scored_holds": int(len(holds)),
            "missed_upside_holds": int(len(missed)),
            "avoided_downside_holds": int(len(avoided)),
            "avg_hold_return_pct": avg_hold,
        },
        "rows": _safe_json_records(missed.head(limit)),
    }


@app.get("/trade-quality-sweep")
async def trade_quality_sweep_report():
    path = Path("data/reports/trade_quality_sweep.json")
    if not path.exists():
        report = await asyncio.to_thread(trade_quality_sweep.run)
        return report
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        report = await asyncio.to_thread(trade_quality_sweep.run)
        return report


@app.get("/shadow-performance")
async def shadow_performance():
    rows = trader.get_decisions(limit=1000)
    shadow = [r for r in rows if r.get("shadow_action")]
    shadow_sm = [r for r in rows if r.get("shadow_smart_money_action")]
    scored_1h = [r for r in shadow if r.get("shadow_future_return_1h") is not None]
    scored_4h = [r for r in shadow if r.get("shadow_future_return_4h") is not None]
    scored_24h = [r for r in shadow if r.get("shadow_future_return_24h") is not None]

    def _stats(items, key):
        vals = [float(r[key]) for r in items if r.get(key) is not None]
        if not vals:
            return {"count": 0, "avg_return_pct": None, "win_rate_pct": None}
        return {
            "count": len(vals),
            "avg_return_pct": round(sum(vals) / len(vals), 4),
            "win_rate_pct": round(sum(1 for v in vals if v > 0) / len(vals) * 100, 2),
        }

    def _smart_stats(horizon_key):
        vals = []
        for r in shadow_sm:
            raw = r.get(horizon_key)
            if raw is None:
                continue
            action = (r.get("shadow_smart_money_action") or "").upper()
            vals.append(float(raw) if action == "BUY" else -float(raw) if action == "SELL" else float(raw))
        if not vals:
            return {"count": 0, "avg_directional_return_pct": None, "win_rate_pct": None}
        return {
            "count": len(vals),
            "avg_directional_return_pct": round(sum(vals) / len(vals), 4),
            "win_rate_pct": round(sum(1 for v in vals if v > 0) / len(vals) * 100, 2),
        }

    return {
        "summary": {
            "shadow_buys": len(shadow),
            "pending": len([r for r in shadow if r.get("shadow_future_return_24h") is None]),
            "one_hour": _stats(scored_1h, "shadow_future_return_1h"),
            "four_hour": _stats(scored_4h, "shadow_future_return_4h"),
            "twenty_four_hour": _stats(scored_24h, "shadow_future_return_24h"),
            "shadow_smart_money": {
                "total": len(shadow_sm),
                "one_hour": _smart_stats("shadow_smart_money_future_return_1h"),
                "four_hour": _smart_stats("shadow_smart_money_future_return_4h"),
                "twenty_four_hour": _smart_stats("shadow_smart_money_future_return_24h"),
            },
        },
        "rows": shadow[:100],
        "smart_money_rows": shadow_sm[:100],
    }


@app.get("/backtest-equity")
async def backtest_equity(limit: int = 800):
    path = Path("data/reports/backtest_equity.csv")
    if not path.exists():
        return {"source": None, "rows": []}
    df = pd.read_csv(path).tail(limit)
    return {"source": str(path), "rows": _safe_json_records(df)}


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
