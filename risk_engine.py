"""
risk_engine.py — deterministic veto layer between Claude and execution.

Claude gives an opinion. This module decides whether that opinion is safe to act on.
Final action is always: HOLD unless every check passes.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from config import (
    STARTING_BALANCE,
    MAX_DRAWDOWN_PCT,
    MAX_CONSECUTIVE_LOSS,
    DAILY_LOSS_LIMIT_PCT,
    MONTHLY_LOSS_LIMIT_PCT,
    MAX_OPEN_TRADES,
    ATR_INITIAL_STOP_MULT,
    ATR_TRAIL_STOP_MULT,
)

MIN_CONFIDENCE         = 60    # Claude must be at least 60% confident
MAX_RISK_PER_TRADE_PCT = 1.0   # never risk more than 1% of account per trade
ATR_STOP_MULTIPLIER    = ATR_INITIAL_STOP_MULT
ATR_TRAIL_MULTIPLIER   = ATR_TRAIL_STOP_MULT
MAX_BB_WIDTH_SQUEEZE    = 0.02   # skip trades when bands are extremely tight (no trend)
MAX_STALE_PRICE_MINUTES = 5
MAX_STALE_DAILY_HOURS   = 30
MAX_STALE_SENTIMENT_HRS = 24
MASTER_DATASET_PATH = Path("data/processed/master_dataset.csv")
EVENTS_JSON_PATH = Path("data/raw/events.json")
SUPERVISION_REPORT_PATH = Path("data/reports/chatgpt_supervision_report.json")
MASTER_DATASET_MAX_AGE_HOURS = float(os.getenv("MASTER_DATASET_MAX_AGE_HOURS", "36"))
DO_NOT_RESUME_SUPERVISION_VERDICTS = {
    "DO_NOT_RESUME",
    "DO_NOT_RESUME_TRADING",
    "DO_NOT_RESUME_TRADING_OR_PAPER_TEST",
    "EXPORT_NOT_AUDIT_CLEAN",
}
CRITICAL_ALERT_CATEGORIES = {"BTC_DIRECT", "REGULATORY_CRYPTO", "EXCHANGE_RISK"}

# Calendar of high-volatility events — dates when we default to HOLD unless confidence ≥ 80
# Format: "MM-DD" (repeating annual) or "YYYY-MM-DD" (one-off)
# FOMC 2025/2026 dates — update annually
FOMC_DATES = {
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
}

# CPI release dates 2025/2026 (BLS, 8:30 ET) — update annually
CPI_DATES = {
    "2025-01-15", "2025-02-12", "2025-03-12", "2025-04-10",
    "2025-05-13", "2025-06-11", "2025-07-15", "2025-08-12",
    "2025-09-10", "2025-10-15", "2025-11-12", "2025-12-10",
    "2026-01-14", "2026-02-11", "2026-03-11", "2026-04-09",
    "2026-05-13", "2026-06-10", "2026-07-15", "2026-08-12",
    "2026-09-09", "2026-10-14", "2026-11-12", "2026-12-09",
}


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _is_event_day() -> tuple[bool, str]:
    today = _today_utc()
    if today in FOMC_DATES:
        return True, f"FOMC meeting day ({today}) — elevated macro risk"
    if today in CPI_DATES:
        return True, f"CPI release day ({today}) — elevated volatility risk"
    return False, ""


def master_dataset_age_hours(path: str | Path = MASTER_DATASET_PATH) -> float | None:
    dataset = Path(path)
    if not dataset.exists():
        return None
    return (datetime.now(timezone.utc).timestamp() - dataset.stat().st_mtime) / 3600


def stale_dataset_hard_block(
    max_age_hours: float = MASTER_DATASET_MAX_AGE_HOURS,
    path: str | Path = MASTER_DATASET_PATH,
) -> dict:
    age = master_dataset_age_hours(path)
    if age is None:
        return {
            "active": True,
            "blocker": "stale_dataset",
            "reason": "master_dataset.csv missing",
            "master_dataset_age_hours": None,
            "max_age_hours": max_age_hours,
        }
    if age > max_age_hours:
        return {
            "active": True,
            "blocker": "stale_dataset",
            "reason": f"master_dataset.csv is {age:.2f}h old; max allowed is {max_age_hours:.2f}h",
            "master_dataset_age_hours": round(age, 4),
            "max_age_hours": max_age_hours,
        }
    return {
        "active": False,
        "blocker": None,
        "reason": "master_dataset_fresh",
        "master_dataset_age_hours": round(age, 4),
        "max_age_hours": max_age_hours,
    }


def _read_json(path: str | Path) -> dict:
    try:
        p = Path(path)
        if p.exists():
            value = json.loads(p.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
    except Exception:
        pass
    return {}


def active_critical_alerts(path: str | Path = EVENTS_JSON_PATH) -> list[dict]:
    data = _read_json(path)
    alerts: list[dict] = []

    if data.get("exchange_hack_alert"):
        alerts.append({"category": "EXCHANGE_RISK", "message": str(data.get("exchange_hack_alert"))})
    if data.get("stablecoin_depeg"):
        alerts.append({"category": "REGULATORY_CRYPTO", "message": str(data.get("stablecoin_depeg"))})

    raw_alerts = data.get("critical_alerts") or data.get("alerts") or data.get("events") or []
    if isinstance(raw_alerts, dict):
        raw_alerts = [raw_alerts]
    for raw in raw_alerts if isinstance(raw_alerts, list) else []:
        if not isinstance(raw, dict):
            continue
        category = str(raw.get("category") or raw.get("alert_type") or raw.get("source") or raw.get("type") or "").upper()
        severity = str(raw.get("severity") or raw.get("level") or "").upper()
        status = str(raw.get("status") or "active").lower()
        text = " ".join(
            str(raw.get(key) or "")
            for key in ("message", "title", "summary", "reason", "text")
        )
        text_upper = text.upper()
        category_hit = category in CRITICAL_ALERT_CATEGORIES or any(cat in text_upper for cat in CRITICAL_ALERT_CATEGORIES)
        severity_hit = severity in {"CRITICAL", "HIGH"} or bool(data.get("has_critical"))
        if status not in {"resolved", "inactive", "closed"} and (category_hit or severity_hit):
            alerts.append(
                {
                    "category": category or ("CRITICAL" if severity_hit else "UNKNOWN"),
                    "severity": severity or raw.get("severity"),
                    "status": status,
                    "message": text.strip() or str(raw)[:500],
                }
            )
    if data.get("has_critical") and not alerts:
        alerts.append({"category": "CRITICAL", "message": "events.json has_critical=true"})
    return alerts


def critical_alerts_hard_block(path: str | Path = EVENTS_JSON_PATH) -> dict:
    alerts = active_critical_alerts(path)
    return {
        "active": bool(alerts),
        "blocker": "critical_market_alert" if alerts else None,
        "reason": "critical market alerts active" if alerts else "no_critical_alerts",
        "critical_alerts_active": alerts,
    }


def supervision_verdict(path: str | Path = SUPERVISION_REPORT_PATH) -> str | None:
    return _read_json(path).get("supervision_verdict")


def supervision_hard_block(path: str | Path = SUPERVISION_REPORT_PATH) -> dict:
    verdict = supervision_verdict(path)
    active = bool(verdict and (verdict in DO_NOT_RESUME_SUPERVISION_VERDICTS or str(verdict).startswith("DO_NOT_RESUME")))
    return {
        "active": active,
        "blocker": "supervision_do_not_resume" if active else None,
        "reason": f"supervision_verdict={verdict}" if active else "supervision_allows_runtime",
        "supervision_verdict": verdict,
    }


def runtime_hard_block_active(
    market: dict | None = None,
    *,
    max_dataset_age_hours: float = MASTER_DATASET_MAX_AGE_HOURS,
    master_dataset_path: str | Path = MASTER_DATASET_PATH,
    events_path: str | Path = EVENTS_JSON_PATH,
    supervision_path: str | Path = SUPERVISION_REPORT_PATH,
) -> dict:
    dataset = stale_dataset_hard_block(max_dataset_age_hours, master_dataset_path)
    alerts = critical_alerts_hard_block(events_path)
    supervision = supervision_hard_block(supervision_path)
    checks = [dataset, alerts, supervision]
    active_checks = [check for check in checks if check.get("active")]
    blockers = [str(check.get("blocker")) for check in active_checks if check.get("blocker")]
    reasons = [str(check.get("reason")) for check in active_checks if check.get("reason")]
    result = {
        "active": bool(active_checks),
        "blocked": bool(active_checks),
        "blocker": blockers[0] if blockers else None,
        "blockers": blockers,
        "reason": "; ".join(reasons) if reasons else "runtime_hard_block_clear",
        "checks": {
            "stale_dataset": dataset,
            "critical_alerts": alerts,
            "supervision": supervision,
        },
        "master_dataset_age_hours": dataset.get("master_dataset_age_hours"),
        "critical_alerts_active": alerts.get("critical_alerts_active", []),
        "supervision_verdict": supervision.get("supervision_verdict"),
    }
    if market:
        market["runtime_hard_block"] = result
        market["runtime_hard_block_active"] = result["active"]
    return result


def apply_runtime_hard_block(decision: dict, hard_block: dict) -> dict:
    blocked = dict(decision)
    blocked["action"] = "HOLD"
    blocked["blocked_by"] = hard_block.get("blocker") or "runtime_hard_block"
    blocked["reason"] = f"Runtime hard block active: {hard_block.get('reason')}"
    blocked["position_usd"] = None
    blocked["stop_price"] = None
    return blocked


def compute_position_size(
    account_balance: float,
    entry_price: float,
    atr: float,
    risk_pct: float = MAX_RISK_PER_TRADE_PCT,
    max_position_pct: float = 30.0,
) -> tuple[float, float]:
    """
    Returns (usd_position_size, stop_price).
    Risk-based sizing: risk_amount / stop_distance.
    """
    stop_distance_usd = ATR_STOP_MULTIPLIER * atr
    stop_price        = entry_price - stop_distance_usd
    risk_amount       = account_balance * (risk_pct / 100)
    stop_pct          = stop_distance_usd / entry_price
    if stop_pct <= 0:
        return 0.0, stop_price
    position_usd = risk_amount / stop_pct
    position_usd = min(position_usd, account_balance * (max_position_pct / 100))
    return round(position_usd, 2), round(stop_price, 2)


def evaluate(
    claude_decision: dict,
    market: dict,
    portfolio: dict,
    closed_trades: list[dict],
) -> dict:
    """
    Takes Claude's raw opinion and returns the final safe decision.

    Parameters
    ----------
    claude_decision : dict from brain.decide() — {action, confidence, reason, ...}
    market          : dict from get_market_context() — price, rsi_14, atr_14, etc.
    portfolio       : dict from trader.portfolio_summary()
    closed_trades   : list of closed trade dicts (for streak/daily checks)

    Returns
    -------
    {
        "action":         "BUY" | "SELL" | "HOLD",
        "reason":         str,
        "blocked_by":     str | None,       # which rule blocked, if any
        "position_usd":   float | None,     # only on BUY
        "stop_price":     float | None,     # only on BUY
        "claude_opinion": dict,             # original Claude output preserved
    }
    """
    action     = claude_decision.get("action", "HOLD").upper()
    confidence = int(claude_decision.get("confidence", 0))
    price      = float(market.get("price", 0))
    atr        = float(market.get("atr_14", 0))
    balance    = float(portfolio.get("cash_balance_usd", 0))
    total      = float(portfolio.get("total_portfolio_usd", 0))
    open_cnt   = int(portfolio.get("open_trades", 0))
    settings   = portfolio.get("settings") or {}
    risk_pct   = float(settings.get("risk_per_trade_pct", MAX_RISK_PER_TRADE_PCT))
    max_pos_pct = float(settings.get("max_position_pct", 30.0))

    def _hold(reason: str, blocked_by: str) -> dict:
        return {
            "action":         "HOLD",
            "reason":         reason,
            "blocked_by":     blocked_by,
            "position_usd":   None,
            "stop_price":     None,
            "claude_opinion": claude_decision,
        }

    # ── Layer A: Critical safety overrides ───────────────────────────────────

    # 1. Max portfolio drawdown
    drawdown_pct = (STARTING_BALANCE - total) / STARTING_BALANCE * 100
    if drawdown_pct >= MAX_DRAWDOWN_PCT:
        return _hold(
            f"Portfolio down {drawdown_pct:.1f}% — max drawdown {MAX_DRAWDOWN_PCT}% hit. Trading paused.",
            "max_drawdown",
        )

    # 2. Consecutive losses streak
    sorted_closed = sorted(closed_trades, key=lambda t: t["timestamp"], reverse=True)
    streak = 0
    for t in sorted_closed:
        if t.get("pnl", 0) < 0:
            streak += 1
        else:
            break
    if streak >= MAX_CONSECUTIVE_LOSS:
        return _hold(
            f"{streak} consecutive losses — max {MAX_CONSECUTIVE_LOSS} hit. Strategy review needed.",
            "consecutive_losses",
        )

    # 3. Daily loss limit
    today_start = int(datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).timestamp())
    today_pnl = sum(
        t.get("pnl", 0) for t in closed_trades
        if t.get("timestamp", 0) >= today_start and t.get("pnl") is not None
    )
    daily_loss_pct = abs(today_pnl) / STARTING_BALANCE * 100
    if today_pnl < 0 and daily_loss_pct >= DAILY_LOSS_LIMIT_PCT:
        return _hold(
            f"Daily loss limit hit: ${abs(today_pnl):.2f} ({daily_loss_pct:.1f}%). Resuming tomorrow.",
            "daily_loss_limit",
        )

    # 4. Monthly loss limit - pause new BUYs, but still allow SELL/HOLD
    month_start = int(datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    ).timestamp())
    monthly_pnl = sum(
        t.get("pnl", 0) for t in closed_trades
        if t.get("timestamp", 0) >= month_start and t.get("pnl") is not None
    )
    monthly_loss_pct = abs(monthly_pnl) / STARTING_BALANCE * 100
    if action == "BUY" and monthly_pnl < 0 and monthly_loss_pct >= MONTHLY_LOSS_LIMIT_PCT:
        return _hold(
            f"Monthly loss limit hit: ${abs(monthly_pnl):.2f} ({monthly_loss_pct:.1f}% of balance, "
            f"limit: {MONTHLY_LOSS_LIMIT_PCT}%). Blocking new BUYs until next month.",
            "monthly_loss_limit",
        )

    # 5. Stablecoin depeg (if scraper provides it)
    depeg = market.get("stablecoin_depeg")
    if depeg:
        return _hold(
            f"Stablecoin depeg detected: {depeg}. Market structure unsafe.",
            "stablecoin_depeg",
        )

    # 6. Exchange hack/collapse flag (if scraper provides it)
    exchange_alert = market.get("exchange_hack_alert")
    if exchange_alert:
        return _hold(
            f"Exchange alert: {exchange_alert}. Holding until market stabilises.",
            "exchange_alert",
        )

    # ── Layer B: Pre-trade checks (only block BUY/SELL, not HOLD) ────────────

    if action == "HOLD":
        return {
            "action":         "HOLD",
            "reason":         claude_decision.get("reason", "Claude advised HOLD"),
            "blocked_by":     None,
            "position_usd":   None,
            "stop_price":     None,
            "claude_opinion": claude_decision,
        }

    # 6. Events data unavailable — cannot verify no critical event, block new BUY only
    if action == "BUY" and market.get("events_unavailable"):
        return _hold(
            "Events data stale or missing — cannot confirm no critical market event. "
            "Blocking new BUY until events refresh.",
            "events_unavailable",
        )

    # 7. Confidence threshold
    if confidence < MIN_CONFIDENCE:
        return _hold(
            f"Claude confidence {confidence}% is below minimum {MIN_CONFIDENCE}%. Not enough conviction.",
            "low_confidence",
        )

    # 8. Max open trades
    if action == "BUY" and open_cnt >= MAX_OPEN_TRADES:
        return _hold(
            f"Already {open_cnt} open trades (max {MAX_OPEN_TRADES}). No new BUY.",
            "max_open_trades",
        )

    # 9. ATR must be available for position sizing on BUY
    if action == "BUY" and atr <= 0:
        return _hold(
            "ATR is zero or missing — cannot calculate stop distance. Skipping trade.",
            "missing_atr",
        )

    # 10. Bollinger Band squeeze — no trend, skip trade
    bb_width = float(market.get("bb_width", 1.0))
    if action == "BUY" and bb_width < MAX_BB_WIDTH_SQUEEZE:
        return _hold(
            f"Bollinger Band squeeze (width={bb_width:.4f}). No directional trend — skipping.",
            "bb_squeeze",
        )

    # 11. FOMC / CPI calendar — reduce risk on event days
    is_event, event_msg = _is_event_day()
    if is_event and confidence < 80:
        return _hold(
            f"{event_msg}. Need confidence ≥ 80% to trade, got {confidence}%.",
            "macro_event_day",
        )

    # 12. Insufficient cash balance for BUY
    if action == "BUY" and balance < 100:
        return _hold(
            f"Cash balance ${balance:.2f} too low to open a meaningful position.",
            "insufficient_balance",
        )

    # ── Compute risk-based position size for BUY ─────────────────────────────

    position_usd, stop_price = (None, None)
    if action == "BUY":
        position_usd, stop_price = compute_position_size(balance, price, atr, risk_pct, max_pos_pct)
        if position_usd < 10:
            return _hold(
                f"Calculated position size ${position_usd:.2f} too small (ATR stop too wide).",
                "position_too_small",
            )

    return {
        "action":         action,
        "reason":         claude_decision.get("reason", ""),
        "blocked_by":     None,
        "position_usd":   position_usd,
        "stop_price":     stop_price,
        "claude_opinion": claude_decision,
    }
