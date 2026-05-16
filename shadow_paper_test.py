"""Shadow BUY small controlled paper test.

This module is intentionally separate from normal portfolio/trade execution.
It never places exchange orders, never mutates trader.trades, and always writes
paper_only=1 in its own shadow_paper_trades table.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import daily_validation_report
import risk_engine
import config as cfg

DB_FILE = cfg.DB_FILE
SHADOW_BUY_PAPER_TEST_ENABLED = getattr(cfg, "SHADOW_BUY_PAPER_TEST_ENABLED", False)
SHADOW_BUY_PAPER_TEST_MAX_POSITION_USD = getattr(cfg, "SHADOW_BUY_PAPER_TEST_MAX_POSITION_USD", 300.0)
SHADOW_BUY_PAPER_TEST_MAX_OPEN_TRADES = getattr(cfg, "SHADOW_BUY_PAPER_TEST_MAX_OPEN_TRADES", 1)
SHADOW_BUY_PAPER_TEST_MIN_TQ_SCORE = getattr(cfg, "SHADOW_BUY_PAPER_TEST_MIN_TQ_SCORE", 70.0)
SHADOW_BUY_PAPER_TEST_MIN_SHADOW_REVIEW_COUNT = getattr(cfg, "SHADOW_BUY_PAPER_TEST_MIN_SHADOW_REVIEW_COUNT", 100)
SHADOW_BUY_PAPER_TEST_STOP_AFTER_TRADES = getattr(cfg, "SHADOW_BUY_PAPER_TEST_STOP_AFTER_TRADES", 10)
SHADOW_BUY_PAPER_TEST_MAX_DAILY_LOSS_USD = getattr(cfg, "SHADOW_BUY_PAPER_TEST_MAX_DAILY_LOSS_USD", 25.0)
SHADOW_BUY_PAPER_TEST_MAX_TOTAL_LOSS_USD = getattr(cfg, "SHADOW_BUY_PAPER_TEST_MAX_TOTAL_LOSS_USD", 50.0)
SHADOW_BUY_PAPER_TEST_COOLDOWN_MINUTES = getattr(cfg, "SHADOW_BUY_PAPER_TEST_COOLDOWN_MINUTES", 60)
SHADOW_BUY_PAPER_TEST_HORIZON_HOURS = getattr(cfg, "SHADOW_BUY_PAPER_TEST_HORIZON_HOURS", 4)
SHADOW_BUY_PAPER_TEST_MODE = getattr(cfg, "SHADOW_BUY_PAPER_TEST_MODE", "paper_only")
SHADOW_BUY_PAPER_TEST_REQUIRE_SMART_MONEY_NOT_BEARISH = getattr(cfg, "SHADOW_BUY_PAPER_TEST_REQUIRE_SMART_MONEY_NOT_BEARISH", True)
SHADOW_BUY_PAPER_TEST_REQUIRE_TA_NOT_BEARISH = getattr(cfg, "SHADOW_BUY_PAPER_TEST_REQUIRE_TA_NOT_BEARISH", True)
SHADOW_BUY_PAPER_TEST_REQUIRE_AI_TA_NOT_BEARISH = getattr(cfg, "SHADOW_BUY_PAPER_TEST_REQUIRE_AI_TA_NOT_BEARISH", True)
SHADOW_BUY_PAPER_TEST_REQUIRE_AT_LEAST_ONE_BULLISH_CONFIRMATION = getattr(cfg, "SHADOW_BUY_PAPER_TEST_REQUIRE_AT_LEAST_ONE_BULLISH_CONFIRMATION", True)
SHADOW_BUY_PAPER_TEST_ALLOW_BB_SQUEEZE_OVERRIDE = getattr(cfg, "SHADOW_BUY_PAPER_TEST_ALLOW_BB_SQUEEZE_OVERRIDE", False)
SHADOW_BUY_PAPER_TEST_REQUIRE_BEARISH_SWEEP_CONFIRMATION = getattr(cfg, "SHADOW_BUY_PAPER_TEST_REQUIRE_BEARISH_SWEEP_CONFIRMATION", False)
SHADOW_BUY_PAPER_TEST_STRICT_RULES_STAGED = getattr(cfg, "SHADOW_BUY_PAPER_TEST_STRICT_RULES_STAGED", True)

REPORT_DIR = Path("data/reports")
JSON_PATH = REPORT_DIR / "shadow_paper_test_report.json"
MD_PATH = REPORT_DIR / "shadow_paper_test_report.md"
RESUME_PLAN_JSON_PATH = REPORT_DIR / "shadow_paper_resume_plan.json"
RESUME_PLAN_MD_PATH = REPORT_DIR / "shadow_paper_resume_plan.md"
SHADOW_REVIEW_PATH = REPORT_DIR / "shadow_buy_review.json"
DAILY_VALIDATION_PATH = REPORT_DIR / "daily_validation_report.json"
DIAGNOSIS_PATH = REPORT_DIR / "shadow_buy_failure_diagnosis.json"
TAKE_PROFIT_PCT = 0.50
STOP_LOSS_PCT = -0.35
WAITING_NOTIFICATION_COOLDOWN_SECONDS = 12 * 60 * 60
BLOCKED_NOTIFICATION_COOLDOWN_SECONDS = 4 * 60 * 60
READY_RECOMMENDATION = "SHADOW_BUY_READY_FOR_SMALL_TEST"
PAUSED_RECOMMENDATION = "SHADOW_BUY_STAYS_SHADOW"
PAUSE_REASON = "Shadow BUY review downgraded to SHADOW_BUY_STAYS_SHADOW"


def _now() -> int:
    return int(time.time())


def _iso(ts: int | float | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(float(ts), timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    con = _connect()
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS shadow_paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opened_at INTEGER NOT NULL,
            closed_at INTEGER,
            symbol TEXT DEFAULT 'BTC/USD',
            side TEXT DEFAULT 'BUY',
            entry_price REAL NOT NULL,
            exit_price REAL,
            position_usd REAL NOT NULL,
            quantity REAL NOT NULL,
            status TEXT DEFAULT 'OPEN',
            entry_reason TEXT,
            exit_reason TEXT,
            candidate_action TEXT,
            final_action TEXT,
            risk_blocker TEXT,
            risk_reason TEXT,
            trade_quality_score REAL,
            shadow_buy_review_count INTEGER,
            shadow_buy_review_recommendation TEXT,
            smart_money_score REAL,
            smart_money_bias TEXT,
            ta_score REAL,
            ta_bias TEXT,
            ai_ta_score REAL,
            ai_ta_bias TEXT,
            pnl_usd REAL,
            pnl_pct REAL,
            duration_minutes REAL,
            paper_only INTEGER DEFAULT 1,
            created_by TEXT
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS shadow_paper_test_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    con.commit()
    con.close()


def _read_json(path: Path, fallback: dict | None = None) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return fallback or {}


def _state_get(key: str) -> str | None:
    init_db()
    con = _connect()
    row = con.execute("SELECT value FROM shadow_paper_test_state WHERE key=?", (key,)).fetchone()
    con.close()
    return row["value"] if row else None


def _state_set(key: str, value: Any) -> None:
    init_db()
    con = _connect()
    con.execute(
        "INSERT OR REPLACE INTO shadow_paper_test_state (key, value) VALUES (?, ?)",
        (key, str(value)),
    )
    con.commit()
    con.close()


def _state_int(key: str) -> int | None:
    value = _state_get(key)
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _rows() -> list[dict]:
    init_db()
    con = _connect()
    rows = [dict(r) for r in con.execute("SELECT * FROM shadow_paper_trades ORDER BY opened_at DESC, id DESC")]
    con.close()
    return rows


def get_trades(limit: int = 200) -> dict:
    rows = _rows()[: max(0, int(limit))]
    return {
        "count": len(rows),
        "rows": rows,
        "paper_only": True,
        "mode": SHADOW_BUY_PAPER_TEST_MODE,
    }


def _open_rows(con: sqlite3.Connection) -> list[dict]:
    return [
        dict(r)
        for r in con.execute(
            "SELECT * FROM shadow_paper_trades WHERE status='OPEN' ORDER BY opened_at ASC"
        )
    ]


def _close_trade(con: sqlite3.Connection, row: dict, price: float, exit_reason: str, now: int) -> dict:
    entry = float(row["entry_price"])
    qty = float(row["quantity"])
    pnl_usd = round((price - entry) * qty, 4)
    pnl_pct = round(((price / entry) - 1) * 100, 4) if entry > 0 else 0.0
    duration = round((now - int(row["opened_at"])) / 60, 2)
    con.execute(
        """
        UPDATE shadow_paper_trades
           SET closed_at=?, exit_price=?, status='CLOSED', exit_reason=?,
               pnl_usd=?, pnl_pct=?, duration_minutes=?, paper_only=1
         WHERE id=?
        """,
        (now, price, exit_reason, pnl_usd, pnl_pct, duration, row["id"]),
    )
    return {
        "type": "close",
        "exit_reason": exit_reason,
        "metadata": {
            "trade_id": row["id"],
            "entry_price": entry,
            "exit_price": price,
            "exit_reason": exit_reason,
            "pnl_usd": pnl_usd,
            "pnl_pct": pnl_pct,
            "duration_minutes": duration,
        },
    }


def update_open_trades(price: float, issues: list[str] | None = None, created_by: str = "scan") -> list[dict]:
    init_db()
    now = _now()
    events: list[dict] = []
    emergency = _emergency_reason(issues or [])
    con = _connect()
    try:
        for row in _open_rows(con):
            entry = float(row["entry_price"])
            pnl_pct = ((float(price) / entry) - 1) * 100 if entry > 0 else 0.0
            age_hours = (now - int(row["opened_at"])) / 3600
            exit_reason = None
            if emergency:
                exit_reason = "EMERGENCY_EXIT"
            elif pnl_pct >= TAKE_PROFIT_PCT:
                exit_reason = "TAKE_PROFIT"
            elif pnl_pct <= STOP_LOSS_PCT:
                exit_reason = "STOP_LOSS"
            elif age_hours >= SHADOW_BUY_PAPER_TEST_HORIZON_HOURS:
                exit_reason = "TIME_EXIT"
            if exit_reason:
                events.append(_close_trade(con, row, float(price), exit_reason, now))
        con.commit()
    finally:
        con.close()
    if events:
        report = run_report(save=True)
        for index, event in enumerate(events):
            metadata = event.get("metadata") or {}
            metadata["closed_test_trades"] = report.get("closed_test_trades")
            metadata["recommendation"] = report.get("recommendation")
            events[index] = _notification(
                kind="close",
                severity="WARNING",
                event_type="shadow_paper_test_trade_closed",
                message="\n".join(
                    [
                        "SHADOW PAPER TRADE CLOSED",
                        f"Exit reason: {metadata.get('exit_reason')}",
                        f"Entry: {metadata.get('entry_price')}",
                        f"Exit: {metadata.get('exit_price')}",
                        f"PnL: {metadata.get('pnl_pct')}% / ${metadata.get('pnl_usd')}",
                        f"Duration: {metadata.get('duration_minutes')} minutes",
                        f"Closed trades: {report.get('closed_test_trades')}",
                        f"Recommendation: {report.get('recommendation')}",
                        "Mode: paper only",
                    ]
                ),
                metadata=metadata,
                now=now,
            ) | {"exit_reason": event.get("exit_reason")}
    return events


def _emergency_reason(issues: list[str]) -> str | None:
    for issue in issues:
        text = str(issue)
        if text.startswith("CRITICAL") or text.startswith("BUY_BLOCK") or "Training dataset" in text:
            return text
    return None


def _review_status() -> dict:
    try:
        import shadow_buy_review

        return shadow_buy_review.run(save=True)
    except Exception:
        return _read_json(SHADOW_REVIEW_PATH, {})


def _review_recommendation(review: dict) -> str:
    return str(review.get("final_shadow_buy_recommendation") or "")


def _review_ready_for_small_test(review: dict) -> bool:
    return (
        _review_recommendation(review) == READY_RECOMMENDATION
        and int(review.get("shadow_buy_count") or 0) >= SHADOW_BUY_PAPER_TEST_MIN_SHADOW_REVIEW_COUNT
    )


def _paper_test_entries_enabled(review: dict) -> bool:
    if risk_engine.supervision_hard_block().get("active"):
        return False
    return (
        SHADOW_BUY_PAPER_TEST_ENABLED
        and SHADOW_BUY_PAPER_TEST_MODE == "paper_only"
        and _review_ready_for_small_test(review)  # review gate keeps paper entries off until evidence supports them
    )


def _strict_resume_conditions() -> dict:
    return {
        "smart_money_not_bearish": SHADOW_BUY_PAPER_TEST_REQUIRE_SMART_MONEY_NOT_BEARISH,  # proposed resume filter from failure diagnosis
        "ta_not_bearish": SHADOW_BUY_PAPER_TEST_REQUIRE_TA_NOT_BEARISH,  # proposed resume filter; TA bearish entries lost in paper test
        "ai_ta_not_bearish": SHADOW_BUY_PAPER_TEST_REQUIRE_AI_TA_NOT_BEARISH,  # proposed resume filter; AI TA bearish should not confirm a BUY
        "at_least_one_bullish_confirmation": SHADOW_BUY_PAPER_TEST_REQUIRE_AT_LEAST_ONE_BULLISH_CONFIRMATION,  # proposed resume filter; TQ alone is insufficient
        "bb_squeeze_override_disabled": not SHADOW_BUY_PAPER_TEST_ALLOW_BB_SQUEEZE_OVERRIDE,  # staged response to all 4 paper trades starting as bb_squeeze overrides
        "bearish_sweep_confirmation_optional": True,  # evidence is tracked, but sample size is still too small to require it
        "bearish_sweep_confirmation_active": SHADOW_BUY_PAPER_TEST_REQUIRE_BEARISH_SWEEP_CONFIRMATION,  # optional staged filter, off by default
    }


def _paper_test_pause_reason(review: dict) -> str | None:
    supervision = risk_engine.supervision_hard_block()
    if supervision.get("active"):
        return f"Supervision forbids trading: {supervision.get('supervision_verdict')}"
    if not SHADOW_BUY_PAPER_TEST_ENABLED:
        return "Shadow Paper Test disabled by staged config"
    return _pause_reason(review)


def _pause_reason(review: dict) -> str | None:
    return PAUSE_REASON if _review_recommendation(review) == PAUSED_RECOMMENDATION else None


def _daily_health_clean(issues: list[str]) -> tuple[bool, str]:
    if _emergency_reason(issues):
        return False, "data_freshness_or_buy_block_issue"
    daily = _read_json(DAILY_VALIDATION_PATH, {})
    if not daily:
        return False, "daily_validation_report_missing"
    if (daily.get("system_health_status") or "").lower() == "error":
        return False, "system_health_error"
    if daily.get("stale_dataset_warning"):
        return False, "stale_dataset_warning"
    if daily.get("download_zip_safe") is False or daily.get("secrets_excluded") is False:
        return False, "download_or_secret_safety_failed"
    return True, "ok"


def _loss_stats(rows: list[dict], now: int) -> dict:
    closed = [r for r in rows if r.get("status") == "CLOSED"]
    total_pnl = round(sum(float(r.get("pnl_usd") or 0) for r in closed), 4)
    day_start = int(datetime.fromtimestamp(now, timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    daily_pnl = round(sum(float(r.get("pnl_usd") or 0) for r in closed if int(r.get("closed_at") or 0) >= day_start), 4)
    return {"closed_count": len(closed), "total_pnl_usd": total_pnl, "daily_pnl_usd": daily_pnl}


def _event_logged(event_type: str) -> bool:
    con = _connect()
    try:
        row = con.execute("SELECT 1 FROM events WHERE event_type=? LIMIT 1", (event_type,)).fetchone()
        return bool(row)  # notifier writes events here, so this prevents milestone spam every scan
    except sqlite3.OperationalError:
        return False
    finally:
        con.close()


def _mark_lifecycle_event(event_name: str, now: int) -> None:
    _state_set("last_event", event_name)
    _state_set("last_event_time", now)


def _notification(
    *,
    kind: str,
    severity: str,
    event_type: str,
    message: str,
    metadata: dict | None = None,
    now: int | None = None,
) -> dict:
    ts = now or _now()
    _mark_lifecycle_event(message.splitlines()[0], ts)
    _state_set(f"telegram_last_{kind}_sent_at", ts)
    return {
        "type": kind,
        "severity": severity,
        "event_type": event_type,
        "message": message,
        "metadata": {"mode": "paper_only", "paper_only": True, **(metadata or {})},
    }


def _cooldown_elapsed(key: str, cooldown_seconds: int, now: int) -> bool:
    last = _state_int(key)
    return last is None or now - last >= cooldown_seconds


def _core_setup_qualified(
    context: dict,
    candidate: dict,
    final: dict,
    pre_risk_tq: dict,
    review: dict,
    normal_trade_executed: bool,
) -> bool:
    final_action = (final.get("action") or "").upper()
    return all(
        [
            SHADOW_BUY_PAPER_TEST_ENABLED,
            SHADOW_BUY_PAPER_TEST_MODE == "paper_only",
            _review_ready_for_small_test(review),
            (candidate.get("action") or "").upper() == "BUY",
            float(pre_risk_tq.get("score") or 0) >= SHADOW_BUY_PAPER_TEST_MIN_TQ_SCORE,
            not normal_trade_executed,
            float(context.get("price") or 0) > 0,
            final_action == "BUY" or (final_action == "HOLD" and bool(final.get("blocked_by"))),
        ]
    )


def _waiting_notification(
    context: dict,
    candidate: dict,
    final: dict,
    block_reason: str | None,
    rows: list[dict],
    now: int,
) -> dict | None:
    has_opened = any(int(r.get("opened_at") or 0) > 0 for r in rows)
    open_count = sum(1 for r in rows if r.get("status") == "OPEN")
    if has_opened or open_count or not _cooldown_elapsed("telegram_last_waiting_sent_at", WAITING_NOTIFICATION_COOLDOWN_SECONDS, now):
        return None
    _state_set("waiting_reason", block_reason or "waiting_for_qualified_setup")
    last_signal = f"candidate={candidate.get('action') or 'none'}, final={final.get('action') or 'none'}"
    current_blocker = final.get("blocked_by") or block_reason or "none"
    message = "\n".join(
        [
            "SHADOW PAPER TEST WAITING",
            "Mode: paper only",
            "Open paper trades: 0",
            f"Closed paper trades: {sum(1 for r in rows if r.get('status') == 'CLOSED')}",
            f"Last signal: {last_signal}",
            f"Current blocker if any: {current_blocker}",
            f"Next requirement: {block_reason or 'qualified BUY setup'}",
        ]
    )
    return _notification(
        kind="waiting",
        severity="INFO",
        event_type="shadow_paper_test_waiting",
        message=message,
        metadata={
            "btc_price": context.get("price"),
            "candidate_action": candidate.get("action"),
            "final_action": final.get("action"),
            "waiting_reason": block_reason,
        },
        now=now,
    )


def _blocked_notification(
    context: dict,
    candidate: dict,
    final: dict,
    pre_risk_tq: dict,
    block_reason: str,
    now: int,
) -> dict | None:
    blocker = final.get("blocked_by") or block_reason
    state_key = f"telegram_last_blocked_sent_at:{blocker}"
    if not _cooldown_elapsed(state_key, BLOCKED_NOTIFICATION_COOLDOWN_SECONDS, now):
        return None
    _state_set(state_key, now)
    _state_set("telegram_last_blocked_sent_at", now)
    _state_set("last_blocker", blocker)
    _state_set("last_blocked_reason", block_reason)
    message = "\n".join(
        [
            "SHADOW PAPER TEST BLOCKED",
            f"Reason: {block_reason}",
            f"BTC: {context.get('price')}",
            f"Trade Quality: {pre_risk_tq.get('score')}",
            f"Candidate: {candidate.get('action')}",
            f"Final: {final.get('action')}",
            "Mode: paper only",
        ]
    )
    return _notification(
        kind="blocked",
        severity="WARNING",
        event_type="shadow_paper_test_blocked",
        message=message,
        metadata={
            "blocker": blocker,
            "btc_price": context.get("price"),
            "trade_quality_score": pre_risk_tq.get("score"),
            "candidate_action": candidate.get("action"),
            "final_action": final.get("action"),
            "reason": final.get("reason"),
            "timestamp": now,
        },
        now=now,
    )


def _paused_notification(review: dict, now: int) -> dict | None:
    reason = _pause_reason(review)
    if (
        not reason
        or _state_int("telegram_last_paused_sent_at") is not None
        or _event_logged("shadow_paper_test_paused")
    ):
        return None
    return _notification(
        kind="paused",
        severity="WARNING",
        event_type="shadow_paper_test_paused",
        message="\n".join(
            [
                "SHADOW PAPER TEST PAUSED",
                "Reason: Shadow BUY review no longer supports small test.",
                f"Review recommendation: {_review_recommendation(review)}",
                "Mode: paper only",
                "No real trades placed.",
            ]
        ),
        metadata={
            "pause_reason": reason,
            "shadow_buy_review_recommendation": _review_recommendation(review),
            "positive_expectancy": review.get("positive_expectancy"),
        },
        now=now,
    )


def _cooldown_ok(rows: list[dict], now: int) -> tuple[bool, str]:
    if SHADOW_BUY_PAPER_TEST_COOLDOWN_MINUTES <= 0:
        return True, "ok"
    last_open = max((int(r.get("opened_at") or 0) for r in rows), default=0)
    if not last_open:
        return True, "ok"
    elapsed = (now - last_open) / 60
    if elapsed < SHADOW_BUY_PAPER_TEST_COOLDOWN_MINUTES:
        return False, f"cooldown_active_{elapsed:.1f}m_lt_{SHADOW_BUY_PAPER_TEST_COOLDOWN_MINUTES}m"
    return True, "ok"


def _entry_block_reason(
    context: dict,
    candidate: dict,
    final: dict,
    pre_risk_tq: dict,
    issues: list[str],
    review: dict,
    rows: list[dict],
    normal_trade_executed: bool = False,
) -> str | None:
    now = _now()
    hard_block = risk_engine.runtime_hard_block_active(context)
    if hard_block.get("active"):
        return "runtime_hard_block_active"
    if not SHADOW_BUY_PAPER_TEST_ENABLED:
        return "disabled"
    if SHADOW_BUY_PAPER_TEST_MODE != "paper_only":
        return "mode_not_paper_only"
    if _review_recommendation(review) != READY_RECOMMENDATION:
        return "shadow_buy_review_not_ready_for_small_test"
    if int(review.get("shadow_buy_count") or 0) < SHADOW_BUY_PAPER_TEST_MIN_SHADOW_REVIEW_COUNT:
        return "shadow_buy_count_below_minimum"
    if (candidate.get("action") or "").upper() != "BUY":
        return "candidate_not_buy"
    score = float(pre_risk_tq.get("score") or 0)
    if score < SHADOW_BUY_PAPER_TEST_MIN_TQ_SCORE:
        return "trade_quality_score_below_paper_test_min"
    final_action = (final.get("action") or "").upper()
    blocked_by = final.get("blocked_by")
    decision_only_buy = final_action == "BUY" and not normal_trade_executed
    risk_blocked_hold = final_action == "HOLD" and bool(blocked_by)
    if normal_trade_executed:
        return "normal_trade_already_executed"
    if not (decision_only_buy or risk_blocked_hold):
        return "not_decision_only_buy_or_risk_blocked_hold"
    if final.get("blocked_by") == "exchange_alert":
        return "exchange_alert_active"
    if final.get("blocked_by") == "events_unavailable":
        return "events_unavailable"
    if (context.get("live_btc_source_status") or {}).get("buy_block"):
        return "live_btc_source_buy_block"
    health_ok, health_reason = _daily_health_clean(issues)
    if not health_ok:
        return health_reason
    open_count = sum(1 for r in rows if r.get("status") == "OPEN")
    if open_count >= SHADOW_BUY_PAPER_TEST_MAX_OPEN_TRADES:
        return "shadow_paper_open_trade_exists"
    loss = _loss_stats(rows, now)
    if loss["closed_count"] >= SHADOW_BUY_PAPER_TEST_STOP_AFTER_TRADES:
        return "paper_test_trade_cap_reached"
    if loss["daily_pnl_usd"] <= -abs(SHADOW_BUY_PAPER_TEST_MAX_DAILY_LOSS_USD):
        return "paper_test_daily_loss_limit_hit"
    if loss["total_pnl_usd"] <= -abs(SHADOW_BUY_PAPER_TEST_MAX_TOTAL_LOSS_USD):
        return "paper_test_total_loss_limit_hit"
    cooldown_ok, cooldown_reason = _cooldown_ok(rows, now)
    if not cooldown_ok:
        return cooldown_reason
    price = float(context.get("price") or 0)
    if price <= 0:
        return "invalid_btc_price"
    return None


def maybe_open_trade(
    context: dict,
    candidate: dict,
    final: dict,
    pre_risk_tq: dict,
    issues: list[str] | None = None,
    created_by: str = "scan",
    normal_trade_executed: bool = False,
) -> dict:
    init_db()
    review = _review_status()
    rows = _rows()
    block_reason = _entry_block_reason(
        context,
        candidate,
        final,
        pre_risk_tq,
        issues or [],
        review,
        rows,
        normal_trade_executed=normal_trade_executed,
    )
    if block_reason:
        hard_block = risk_engine.runtime_hard_block_active(context)
        notifications = []
        if hard_block.get("active") and (candidate.get("action") or "").upper() == "BUY":
            incident = daily_validation_report.log_trade_execution_incident(
                trade_type="shadow-paper",
                hard_block=hard_block,
                context={**context, "open_shadow_paper_trades": sum(1 for r in rows if r.get("status") == "OPEN")},
                final=final,
                portfolio={
                    "btc_held": 0,
                    "open_trades": 0,
                    "open_shadow_paper_trades": sum(1 for r in rows if r.get("status") == "OPEN"),
                },
                real_order_sent=False,
                recommendation="DO_NOT_RESUME",
            )
            notifications.extend(
                [
                    _notification(
                        kind="runtime_freeze",
                        severity="CRITICAL",
                        event_type="EXECUTION_FREEZE_ACTIVE",
                        message="\n".join(
                            [
                                "EXECUTION FREEZE ACTIVE",
                                "Shadow Paper Test entry rejected.",
                                f"Reason: {hard_block.get('reason')}",
                                f"Report: {incident.get('json_path')}",
                            ]
                        ),
                        metadata={
                            "blocker": hard_block.get("blocker"),
                            "blockers": hard_block.get("blockers"),
                            "incident_report": incident.get("json_path"),
                            "supervision_verdict": hard_block.get("supervision_verdict"),
                        },
                    ),
                    _notification(
                        kind="incident",
                        severity="CRITICAL",
                        event_type="TRADE_EXECUTION_INCIDENT",
                        message="\n".join(
                            [
                                "TRADE EXECUTION INCIDENT",
                                "Trade type: shadow-paper",
                                f"Reason: {hard_block.get('reason')}",
                                f"Report: {incident.get('json_path')}",
                            ]
                        ),
                        metadata={"incident_report": incident.get("json_path"), "trade_type": "shadow-paper"},
                    ),
                    _notification(
                        kind="paused",
                        severity="CRITICAL",
                        event_type="SHADOW_PAPER_TEST_PAUSED",
                        message="\n".join(
                            [
                                "SHADOW PAPER TEST PAUSED",
                                f"Reason: {hard_block.get('reason')}",
                                "No shadow-paper trade opened.",
                            ]
                        ),
                        metadata={"blocker": hard_block.get("blocker"), "supervision_verdict": hard_block.get("supervision_verdict")},
                    ),
                ]
            )
        run_report(save=True)
        return {"status": "not_opened", "reason": block_reason, "notifications": notifications}

    now = _now()
    price = float(context.get("price") or 0)
    position = float(SHADOW_BUY_PAPER_TEST_MAX_POSITION_USD)
    quantity = position / price
    smart = context.get("smart_money") or {}
    ta = context.get("ta_forecast") or {}
    ai_ta = context.get("ai_ta") or {}
    if (final.get("action") or "").upper() == "BUY":
        entry_reason = "PAPER TEST: decision-only BUY signal was not executed by the normal portfolio layer."
    else:
        entry_reason = (
            "PAPER TEST OVERRIDE: normal risk engine blocked candidate "
            f"with {final.get('blocked_by')}; shadow BUY review is ready."
        )
    con = _connect()
    try:
        con.execute(
            """
            INSERT INTO shadow_paper_trades
                (opened_at, symbol, side, entry_price, position_usd, quantity, status,
                 entry_reason, candidate_action, final_action, risk_blocker, risk_reason,
                 trade_quality_score, shadow_buy_review_count, shadow_buy_review_recommendation,
                 smart_money_score, smart_money_bias, ta_score, ta_bias, ai_ta_score, ai_ta_bias,
                 paper_only, created_by)
            VALUES (?, 'BTC/USD', 'BUY', ?, ?, ?, 'OPEN',
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                now,
                price,
                position,
                quantity,
                entry_reason,
                candidate.get("action"),
                final.get("action"),
                final.get("blocked_by"),
                (final.get("reason") or "")[:700],
                float(pre_risk_tq.get("score") or 0),
                int(review.get("shadow_buy_count") or 0),
                review.get("final_shadow_buy_recommendation"),
                smart.get("smart_money_score") or context.get("smart_money_score"),
                smart.get("smart_money_bias") or context.get("smart_money_bias"),
                ta.get("ta_score") or context.get("ta_score"),
                ta.get("ta_bias") or context.get("ta_bias"),
                ai_ta.get("ai_ta_score"),
                ai_ta.get("ai_ta_bias"),
                created_by,
            ),
        )
        trade_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        con.commit()
    finally:
        con.close()
    report = run_report(save=True)
    notifications = [
        _notification(
            kind="open",
            severity="WARNING",
            event_type="shadow_paper_test_trade_opened",
            message="\n".join(
                [
                    "SHADOW PAPER BUY OPENED",
                    f"Entry: {price}",
                    f"Position: ${position} / {quantity} BTC",
                    f"Trade Quality: {float(pre_risk_tq.get('score') or 0)}",
                    f"Risk blocker: {final.get('blocked_by') or 'none'}",
                    f"Smart Money: {smart.get('smart_money_bias') or context.get('smart_money_bias') or 'unknown'}",
                    f"TA: {ta.get('ta_bias') or context.get('ta_bias') or 'unknown'}",
                    f"AI TA: {ai_ta.get('ai_ta_bias') or 'unknown'}",
                    "Mode: paper only",
                ]
            ),
            metadata={
                "trade_id": trade_id,
                "entry_price": price,
                "position_usd": position,
                "quantity": quantity,
                "trade_quality_score": float(pre_risk_tq.get("score") or 0),
                "risk_blocker": final.get("blocked_by"),
                "smart_money_bias": smart.get("smart_money_bias") or context.get("smart_money_bias"),
                "ta_bias": ta.get("ta_bias") or context.get("ta_bias"),
                "ai_ta_bias": ai_ta.get("ai_ta_bias"),
                "reason": entry_reason,
            },
            now=now,
        )
    ]
    return {"status": "opened", "trade_id": trade_id, "notifications": notifications}


def process_scan(
    context: dict,
    candidate: dict,
    final: dict,
    pre_risk_tq: dict,
    issues: list[str] | None = None,
    created_by: str = "scan",
    normal_trade_executed: bool = False,
) -> dict:
    price = float(context.get("price") or 0)
    notifications = []
    if price > 0:
        notifications.extend(update_open_trades(price, issues=issues or [], created_by=created_by))
    opened = maybe_open_trade(
        context,
        candidate,
        final,
        pre_risk_tq,
        issues=issues or [],
        created_by=created_by,
        normal_trade_executed=normal_trade_executed,
    )
    notifications.extend(opened.get("notifications") or [])
    report = run_report(save=True)
    if opened.get("status") == "not_opened":
        reason = opened.get("reason")
        review = _review_status()
        now = _now()
        if _pause_reason(review):
            paused = _paused_notification(review, now)
            if paused:
                notifications.append(paused)
        elif _core_setup_qualified(context, candidate, final, pre_risk_tq, review, normal_trade_executed):
            blocked = _blocked_notification(context, candidate, final, pre_risk_tq, reason, now)
            if blocked:
                notifications.append(blocked)
        else:
            waiting = _waiting_notification(context, candidate, final, reason, _rows(), now)
            if waiting:
                notifications.append(waiting)
    if report.get("recommendation") == "PAPER_TEST_STOP_LOSING" and _state_int("telegram_last_loss_sent_at") is None:
        notifications.append(
            _notification(
                kind="loss",
                severity="CRITICAL",
                event_type="shadow_paper_test_loss_limit_hit",
                message="\n".join(
                    [
                        "SHADOW PAPER TEST STOPPED",
                        "Reason: loss limit hit",
                        f"Daily PnL: {report.get('daily_pnl_usd')}",
                        f"Total PnL: {report.get('total_pnl_usd')}",
                        f"Open trades: {report.get('open_test_trades')}",
                        "Mode: paper only",
                    ]
                ),
                metadata={
                    "daily_pnl_usd": report.get("daily_pnl_usd"),
                    "total_pnl_usd": report.get("total_pnl_usd"),
                    "stop_reason": report.get("stop_reason"),
                },
            )
        )
    if report.get("recommendation") == "PAPER_TEST_READY_FOR_REVIEW" and _state_int("telegram_last_ready_sent_at") is None:
        notifications.append(
            _notification(
                kind="ready",
                severity="WARNING",
                event_type="shadow_paper_test_ready_for_review",
                message="\n".join(
                    [
                        "SHADOW PAPER TEST READY FOR REVIEW",
                        f"Closed trades: {report.get('closed_test_trades')}",
                        f"Win rate: {report.get('win_rate')}",
                        f"Avg PnL: {report.get('avg_pnl_pct')}% / ${report.get('avg_pnl_usd')}",
                        f"Total PnL: {report.get('total_pnl_usd')}",
                        f"Recommendation: {report.get('recommendation')}",
                    ]
                ),
                metadata={
                    "closed_test_trades": report.get("closed_test_trades"),
                    "win_rate": report.get("win_rate"),
                    "avg_pnl_pct": report.get("avg_pnl_pct"),
                    "avg_pnl_usd": report.get("avg_pnl_usd"),
                    "total_pnl_usd": report.get("total_pnl_usd"),
                },
            )
        )
    return {"update": opened, "notifications": notifications, "report": report}


def _max_drawdown(closed: list[dict]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for row in sorted(closed, key=lambda r: int(r.get("closed_at") or 0)):
        equity += float(row.get("pnl_usd") or 0)
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return round(max_dd, 4)


def _recommendation(closed_count: int, win_rate: float, avg_pnl_pct: float, total_pnl: float, open_count: int) -> str:
    if total_pnl <= -abs(SHADOW_BUY_PAPER_TEST_MAX_TOTAL_LOSS_USD):
        return "PAPER_TEST_STOP_LOSING"
    if closed_count < SHADOW_BUY_PAPER_TEST_STOP_AFTER_TRADES:
        return "PAPER_TEST_RUNNING" if open_count else "PAPER_TEST_COLLECT_MORE"
    if win_rate >= 55 and avg_pnl_pct > 0 and total_pnl > 0:
        return "PAPER_TEST_READY_FOR_REVIEW"
    return "PAPER_TEST_STOP_LOSING"


def run_report(save: bool = True) -> dict:
    init_db()
    rows = _rows()
    review = _review_status()
    review_pause_reason = _pause_reason(review)
    pause_reason = _paper_test_pause_reason(review)
    entries_enabled = _paper_test_entries_enabled(review)
    open_rows = [r for r in rows if r.get("status") == "OPEN"]
    closed = [r for r in rows if r.get("status") == "CLOSED"]
    wins = [r for r in closed if float(r.get("pnl_usd") or 0) > 0]
    losses = [r for r in closed if float(r.get("pnl_usd") or 0) < 0]
    pnl_usd = [float(r.get("pnl_usd") or 0) for r in closed]
    pnl_pct = [float(r.get("pnl_pct") or 0) for r in closed]
    total_pnl = round(sum(pnl_usd), 4)
    win_rate = round(len(wins) / len(closed) * 100, 2) if closed else 0.0
    avg_pct = round(mean(pnl_pct), 4) if pnl_pct else 0.0
    avg_usd = round(mean(pnl_usd), 4) if pnl_usd else 0.0
    exit_counts = {r: sum(1 for row in closed if row.get("exit_reason") == r) for r in ("TAKE_PROFIT", "STOP_LOSS", "TIME_EXIT", "EMERGENCY_EXIT")}
    stop_reason = None
    now = _now()
    loss = _loss_stats(rows, now)
    if loss["daily_pnl_usd"] <= -abs(SHADOW_BUY_PAPER_TEST_MAX_DAILY_LOSS_USD):
        stop_reason = "daily_loss_limit_hit"
    elif loss["total_pnl_usd"] <= -abs(SHADOW_BUY_PAPER_TEST_MAX_TOTAL_LOSS_USD):
        stop_reason = "total_loss_limit_hit"
    elif len(closed) >= SHADOW_BUY_PAPER_TEST_STOP_AFTER_TRADES:
        stop_reason = "trade_cap_reached"
    recommendation = _recommendation(len(closed), win_rate, avg_pct, total_pnl, len(open_rows))
    last_open_ts = max((int(r.get("opened_at") or 0) for r in rows), default=0)
    next_trade_ts = None
    cooldown_remaining = 0.0
    if last_open_ts and SHADOW_BUY_PAPER_TEST_COOLDOWN_MINUTES > 0:
        next_trade_ts = last_open_ts + int(SHADOW_BUY_PAPER_TEST_COOLDOWN_MINUTES * 60)
        cooldown_remaining = max(0.0, round((next_trade_ts - now) / 60, 2))
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "enabled": SHADOW_BUY_PAPER_TEST_ENABLED,
        "paper_test_entries_enabled": entries_enabled,
        "config_enabled": SHADOW_BUY_PAPER_TEST_ENABLED,
        "mode": SHADOW_BUY_PAPER_TEST_MODE,
        "paper_only": True,
        "pause_reason": pause_reason,
        "review_pause_reason": review_pause_reason,
        "shadow_buy_review_recommendation": _review_recommendation(review),
        "shadow_buy_positive_expectancy": review.get("positive_expectancy"),
        "shadow_buy_review_count": int(review.get("shadow_buy_count") or 0),
        "strict_rules_staged": SHADOW_BUY_PAPER_TEST_STRICT_RULES_STAGED,
        "strict_resume_conditions": _strict_resume_conditions(),
        "config": {
            "max_position_usd": SHADOW_BUY_PAPER_TEST_MAX_POSITION_USD,
            "max_open_trades": SHADOW_BUY_PAPER_TEST_MAX_OPEN_TRADES,
            "min_tq_score": SHADOW_BUY_PAPER_TEST_MIN_TQ_SCORE,
            "min_shadow_review_count": SHADOW_BUY_PAPER_TEST_MIN_SHADOW_REVIEW_COUNT,
            "stop_after_trades": SHADOW_BUY_PAPER_TEST_STOP_AFTER_TRADES,
            "max_daily_loss_usd": SHADOW_BUY_PAPER_TEST_MAX_DAILY_LOSS_USD,
            "max_total_loss_usd": SHADOW_BUY_PAPER_TEST_MAX_TOTAL_LOSS_USD,
            "cooldown_minutes": SHADOW_BUY_PAPER_TEST_COOLDOWN_MINUTES,
            "horizon_hours": SHADOW_BUY_PAPER_TEST_HORIZON_HOURS,
            "take_profit_pct": TAKE_PROFIT_PCT,
            "stop_loss_pct": STOP_LOSS_PCT,
            "strict_rules_staged": SHADOW_BUY_PAPER_TEST_STRICT_RULES_STAGED,
            "require_smart_money_not_bearish": SHADOW_BUY_PAPER_TEST_REQUIRE_SMART_MONEY_NOT_BEARISH,
            "require_ta_not_bearish": SHADOW_BUY_PAPER_TEST_REQUIRE_TA_NOT_BEARISH,
            "require_ai_ta_not_bearish": SHADOW_BUY_PAPER_TEST_REQUIRE_AI_TA_NOT_BEARISH,
            "require_at_least_one_bullish_confirmation": SHADOW_BUY_PAPER_TEST_REQUIRE_AT_LEAST_ONE_BULLISH_CONFIRMATION,
            "allow_bb_squeeze_override": SHADOW_BUY_PAPER_TEST_ALLOW_BB_SQUEEZE_OVERRIDE,
            "require_bearish_sweep_confirmation": SHADOW_BUY_PAPER_TEST_REQUIRE_BEARISH_SWEEP_CONFIRMATION,
        },
        "total_test_trades": len(rows),
        "open_test_trades": len(open_rows),
        "closed_test_trades": len(closed),
        "open_trade_count": len(open_rows),
        "closed_trade_count": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "avg_pnl_pct": avg_pct,
        "avg_pnl_usd": avg_usd,
        "total_pnl_usd": total_pnl,
        "daily_pnl_usd": loss["daily_pnl_usd"],
        "max_drawdown_usd": _max_drawdown(closed),
        "take_profit_count": exit_counts["TAKE_PROFIT"],
        "stop_loss_count": exit_counts["STOP_LOSS"],
        "time_exit_count": exit_counts["TIME_EXIT"],
        "emergency_exit_count": exit_counts["EMERGENCY_EXIT"],
        "current_status": "Paper Test Paused" if pause_reason else ("OPEN" if open_rows else "WAITING"),
        "stop_reason": stop_reason,
        "recommendation": recommendation,
        "last_trade": rows[0] if rows else None,
        "last_event": _state_get("last_event"),
        "last_event_time": _iso(_state_int("last_event_time")),
        "last_blocker": _state_get("last_blocker"),
        "last_blocked_reason": _state_get("last_blocked_reason"),
        "waiting_reason": _state_get("waiting_reason") or ("waiting_for_qualified_setup" if not open_rows else None),
        "next_possible_trade_time": _iso(next_trade_ts),
        "cooldown_remaining_minutes": cooldown_remaining,
        "telegram_last_waiting_sent_at": _iso(_state_int("telegram_last_waiting_sent_at")),
        "telegram_last_blocked_sent_at": _iso(_state_int("telegram_last_blocked_sent_at")),
        "telegram_last_open_sent_at": _iso(_state_int("telegram_last_open_sent_at")),
        "telegram_last_close_sent_at": _iso(_state_int("telegram_last_close_sent_at")),
        "telegram_last_pause_sent_at": _iso(_state_int("telegram_last_paused_sent_at")),
        "guardrails": [
            "Paper test only; no real exchange order.",
            "Normal risk_engine.py is unchanged.",
            "Normal portfolio trades table is unchanged.",
            "Smart Money, TA, and AI TA remain shadow-only.",
        ],
    }
    if save:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        JSON_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        _write_markdown(report)
        run_resume_plan_report(save=True, current_report=report)
    return report


def _diagnosis_summary() -> dict:
    diagnosis = _read_json(DIAGNOSIS_PATH, {})
    paper = diagnosis.get("paper_trade_summary") or {}
    failure = diagnosis.get("failure_reasons") or {}
    best = (diagnosis.get("winning_conditions") or diagnosis.get("best_filters") or [{}])[0] or {}
    worst = (diagnosis.get("losing_conditions") or diagnosis.get("worst_filters") or [{}])[0] or {}
    return {
        "source_report": DIAGNOSIS_PATH.as_posix(),
        "recommended_next_action": diagnosis.get("recommended_next_action") or [],
        "paper_trade_count": int(paper.get("total_trades") or 0),
        "closed_paper_trades": int(paper.get("closed_trades") or 0),
        "paper_test_win_rate": paper.get("win_rate"),
        "paper_test_total_pnl_usd": paper.get("total_pnl_usd"),
        "bb_squeeze_override_trades": paper.get("bb_squeeze_override_trades"),
        "entries_against_ta": paper.get("entries_against_ta"),
        "entries_against_ai_ta": paper.get("entries_against_ai_ta"),
        "failure_reasons": failure,
        "best_condition": {
            "section": best.get("section"),
            "filter": best.get("filter"),
            "avg_return_4h": best.get("avg_return_4h"),
            "win_rate_4h": best.get("win_rate_4h"),
            "count": best.get("count"),
        },
        "worst_condition": {
            "section": worst.get("section"),
            "filter": worst.get("filter"),
            "avg_return_4h": worst.get("avg_return_4h"),
            "win_rate_4h": worst.get("win_rate_4h"),
            "count": worst.get("count"),
        },
    }


def run_resume_plan_report(save: bool = True, current_report: dict | None = None) -> dict:
    current_report = current_report or run_report(save=False)
    diagnosis = _diagnosis_summary()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current_status": current_report.get("current_status") or "Paper Test Paused",
        "why_paused": current_report.get("pause_reason") or "Shadow Paper Test remains disabled while stricter resume rules are staged.",
        "diagnosis_summary": diagnosis,
        "proposed_filters": _strict_resume_conditions(),
        "expected_effect": [
            "Reject staged resume candidates when Smart Money, TA, or AI TA are bearish.",
            "Require at least one bullish confirmation so high Trade Quality alone is not enough.",
            "Keep bb_squeeze overrides disabled because the first four paper trades all came from that path and total PnL is negative.",
            "Track bearish_sweep confirmation as optional evidence only until more shadow-only samples exist.",
        ],
        "risks": [
            "Sample size is still small, especially for bearish_sweep and high Trade Quality buckets.",
            "Making filters too strict could remove future valid recovery setups.",
            "Stop/take-profit behavior still needs review because paper losses hit before the 4h horizon could mature.",
            "This plan does not resume paper entries or change execution behavior automatically.",
        ],
        "recommendation": ["KEEP_PAUSED_AND_COLLECT_SHADOW", "DO_NOT_RESUME_YET"],
    }
    if save:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        RESUME_PLAN_JSON_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        _write_resume_plan_markdown(report)
    return report


def _write_resume_plan_markdown(report: dict) -> None:
    lines = [
        "# Shadow Paper Resume Plan",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Current status: `{report['current_status']}`",
        f"- Why paused: `{report['why_paused']}`",
        f"- Recommendation: `{', '.join(report['recommendation'])}`",
        "",
        "## Diagnosis Summary",
        "",
        "```json",
        json.dumps(report["diagnosis_summary"], indent=2),
        "```",
        "",
        "## Proposed Filters",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in report["proposed_filters"].items())
    lines.extend(["", "## Expected Effect", ""])
    lines.extend(f"- {item}" for item in report["expected_effect"])
    lines.extend(["", "## Risks", ""])
    lines.extend(f"- {item}" for item in report["risks"])
    lines.extend(["", "Staged only. This report does not resume paper entries, enable bonuses, place real trades, or change risk_engine.py.", ""])
    RESUME_PLAN_MD_PATH.write_text("\n".join(lines), encoding="utf-8")


def _write_markdown(report: dict) -> None:
    lines = [
        "# Shadow Paper Test Report",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Enabled: `{report['enabled']}`",
        f"- Paper test entries enabled: `{report['paper_test_entries_enabled']}`",
        f"- Current status: `{report['current_status']}`",
        f"- Pause reason: `{report['pause_reason']}`",
        f"- Strict rules staged: `{report['strict_rules_staged']}`",
        f"- Shadow BUY review recommendation: `{report['shadow_buy_review_recommendation']}`",
        f"- Mode: `{report['mode']}`",
        f"- Paper only: `{report['paper_only']}`",
        f"- Recommendation: `{report['recommendation']}`",
        f"- Total trades: `{report['total_test_trades']}`",
        f"- Open trades: `{report['open_test_trades']}`",
        f"- Closed trades: `{report['closed_test_trades']}`",
        f"- Wins / losses: `{report['wins']} / {report['losses']}`",
        f"- Win rate: `{report['win_rate']}%`",
        f"- Average PnL: `{report['avg_pnl_pct']}%`, `${report['avg_pnl_usd']}`",
        f"- Total PnL: `${report['total_pnl_usd']}`",
        f"- Max drawdown: `${report['max_drawdown_usd']}`",
        f"- Take profit / stop loss / time / emergency exits: `{report['take_profit_count']} / {report['stop_loss_count']} / {report['time_exit_count']} / {report['emergency_exit_count']}`",
        "",
        "## Guardrails",
        "",
    ]
    lines.extend(f"- {item}" for item in report["guardrails"])
    lines.extend(
        [
            "",
            "## Proposed Resume Rules",
            "",
            "```json",
            json.dumps(report["strict_resume_conditions"], indent=2),
            "```",
            "",
            "## Config",
            "",
            "```json",
            json.dumps(report["config"], indent=2),
            "```",
        ]
    )
    MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps(run_report(save=True), indent=2))
