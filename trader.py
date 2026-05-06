import sqlite3
import time
import json
from datetime import datetime, timezone
from config import (
    DB_FILE, STARTING_BALANCE, TRADE_SIZE_PCT, MAX_OPEN_TRADES,
    MAX_DRAWDOWN_PCT, MAX_CONSECUTIVE_LOSS, DAILY_LOSS_LIMIT_PCT,
    ATR_INITIAL_STOP_MULT, ATR_TRAIL_STOP_MULT,
    AI_INPUT_USD_PER_MILLION_TOKENS, AI_OUTPUT_USD_PER_MILLION_TOKENS,
    SHADOW_BUY_SCORE_THRESHOLD, STRATEGY_VERSION,
    SMART_MONEY_MIN_SCORE_FOR_BUY_BONUS,
)


DEFAULT_SETTINGS = {
    "trade_size_pct": TRADE_SIZE_PCT,
    "risk_per_trade_pct": 1.0,
    "max_position_pct": 30.0,
}


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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       INTEGER NOT NULL,
            severity        TEXT NOT NULL,
            event_type      TEXT NOT NULL,
            actor           TEXT DEFAULT 'system',
            source          TEXT,
            symbol          TEXT,
            status          TEXT,
            message         TEXT NOT NULL,
            metadata_json   TEXT,
            telegram_sent   INTEGER DEFAULT 0,
            telegram_error  TEXT
        )
    """)
    for key, value in DEFAULT_SETTINGS.items():
        cur.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
    try:
        cur.execute("ALTER TABLE decisions ADD COLUMN trigger TEXT DEFAULT 'unknown'")
    except Exception:
        pass
    for col in (
        "risk_summary TEXT",
        "invalid_if_json TEXT",
        "historical_summary_json TEXT",
        "trade_quality_json TEXT",
        "strategy_version TEXT",
        "candidate_action TEXT",
        "candidate_source TEXT",
        "candidate_confidence INTEGER",
        "candidate_reason TEXT",
        "pre_risk_tq_json TEXT",
        "pre_risk_tq_score REAL",
        "pre_risk_tq_trend REAL",
        "pre_risk_tq_momentum REAL",
        "pre_risk_tq_volatility REAL",
        "pre_risk_tq_derivatives REAL",
        "pre_risk_tq_macro REAL",
        "pre_risk_tq_historical_match REAL",
        "pre_risk_tq_data_quality REAL",
        "pre_risk_tq_risk_safety REAL",
        "pre_risk_tq_primary_reason TEXT",
        "post_risk_tq_json TEXT",
        "post_risk_tq_score REAL",
        "risk_blocked_candidate INTEGER DEFAULT 0",
        "risk_blocker TEXT",
        "blocked_candidate_entry_price REAL",
        "blocked_candidate_tq_score REAL",
        "blocked_candidate_future_return_1h REAL",
        "blocked_candidate_future_return_4h REAL",
        "blocked_candidate_future_return_24h REAL",
        "blocked_candidate_outcome_1h TEXT",
        "blocked_candidate_outcome_4h TEXT",
        "blocked_candidate_outcome_24h TEXT",
        "smart_money_score REAL",
        "smart_money_bias TEXT",
        "smart_money_reason TEXT",
        "smart_money_json TEXT",
        "structure_state TEXT",
        "liquidity_state TEXT",
        "order_block_state TEXT",
        "fvg_state TEXT",
        "premium_discount_state TEXT",
        "timeframe_alignment TEXT",
        "shadow_smart_money_action TEXT",
        "shadow_smart_money_score REAL",
        "shadow_smart_money_bias TEXT",
        "shadow_smart_money_reason TEXT",
        "shadow_smart_money_future_return_1h REAL",
        "shadow_smart_money_future_return_4h REAL",
        "shadow_smart_money_future_return_24h REAL",
        "tq_score REAL",
        "tq_trend REAL",
        "tq_momentum REAL",
        "tq_volatility REAL",
        "tq_derivatives REAL",
        "tq_macro REAL",
        "tq_historical_match REAL",
        "tq_data_quality REAL",
        "tq_risk_safety REAL",
        "tq_primary_reason TEXT",
        "shadow_action TEXT",
        "shadow_entry_price REAL",
        "shadow_score REAL",
        "shadow_reason TEXT",
        "shadow_stop_price REAL",
        "shadow_take_profit_price REAL",
        "shadow_future_return_1h REAL",
        "shadow_future_return_4h REAL",
        "shadow_future_return_24h REAL",
        "ai_model TEXT",
        "ai_prompt TEXT",
        "ai_response TEXT",
        "input_tokens INTEGER",
        "output_tokens INTEGER",
        "api_cost_usd REAL",
    ):
        try:
            cur.execute(f"ALTER TABLE decisions ADD COLUMN {col}")
        except Exception:
            pass
    cur.execute("INSERT OR IGNORE INTO portfolio (id, balance) VALUES (1, ?)", (STARTING_BALANCE,))
    _backfill_trade_quality_columns(cur)
    con.commit()
    con.close()


def _backfill_trade_quality_columns(cur) -> None:
    """Populate new queryable Trade Quality columns from existing JSON rows."""
    try:
        rows = cur.execute(
            """SELECT id, final_action, blocked_by, btc_price, claude_action, claude_conf,
                      claude_reason, trade_quality_json, tq_score, shadow_action,
                      candidate_action, pre_risk_tq_score, post_risk_tq_score
               FROM decisions
               WHERE trade_quality_json IS NOT NULL AND trade_quality_json != ''"""
        ).fetchall()
    except Exception:
        return

    for row in rows:
        (
            decision_id, final_action, blocked_by, btc_price, claude_action, claude_conf,
            claude_reason, quality_json, tq_score, shadow_action, candidate_action,
            pre_risk_tq_score, post_risk_tq_score,
        ) = row
        try:
            quality = json.loads(quality_json or "{}")
        except Exception:
            continue
        components = quality.get("components") or {}
        score = quality.get("score")
        if score is None:
            continue
        shadow = shadow_action
        shadow_entry = shadow_score = shadow_tp = None
        shadow_reason = None
        if not shadow and str(final_action).upper() == "HOLD" and float(score) >= SHADOW_BUY_SCORE_THRESHOLD:
            price = float(btc_price or 0)
            if price > 0:
                shadow = "BUY"
                shadow_entry = price
                shadow_score = float(score)
                shadow_tp = round(price * 1.03, 2)
                shadow_reason = quality.get("primary_reason") or "quality_score_above_shadow_threshold"
        inferred_candidate_action = candidate_action
        inferred_source = None
        if not inferred_candidate_action:
            reason_text = str(claude_reason or "")
            if str(claude_action).upper() == "BUY":
                inferred_candidate_action = "BUY"
                inferred_source = "trade_quality" if reason_text.startswith("Trade Quality Score") else "claude"
            else:
                inferred_candidate_action = str(claude_action or "HOLD").upper()
                inferred_source = "none"
        risk_blocked_candidate = int(
            str(inferred_candidate_action).upper() == "BUY"
            and str(final_action).upper() == "HOLD"
            and bool(blocked_by)
        )
        cur.execute(
            """UPDATE decisions SET
               tq_score=?, tq_trend=?, tq_momentum=?, tq_volatility=?, tq_derivatives=?,
               tq_macro=?, tq_historical_match=?, tq_data_quality=?, tq_risk_safety=?,
               tq_primary_reason=?,
               strategy_version=COALESCE(strategy_version, ?),
               candidate_action=COALESCE(candidate_action, ?),
               candidate_source=COALESCE(candidate_source, ?),
               candidate_confidence=COALESCE(candidate_confidence, ?),
               candidate_reason=COALESCE(candidate_reason, ?),
               pre_risk_tq_json=COALESCE(pre_risk_tq_json, ?),
               pre_risk_tq_score=COALESCE(pre_risk_tq_score, ?),
               pre_risk_tq_trend=COALESCE(pre_risk_tq_trend, ?),
               pre_risk_tq_momentum=COALESCE(pre_risk_tq_momentum, ?),
               pre_risk_tq_volatility=COALESCE(pre_risk_tq_volatility, ?),
               pre_risk_tq_derivatives=COALESCE(pre_risk_tq_derivatives, ?),
               pre_risk_tq_macro=COALESCE(pre_risk_tq_macro, ?),
               pre_risk_tq_historical_match=COALESCE(pre_risk_tq_historical_match, ?),
               pre_risk_tq_data_quality=COALESCE(pre_risk_tq_data_quality, ?),
               pre_risk_tq_risk_safety=COALESCE(pre_risk_tq_risk_safety, ?),
               pre_risk_tq_primary_reason=COALESCE(pre_risk_tq_primary_reason, ?),
               post_risk_tq_json=COALESCE(post_risk_tq_json, ?),
               post_risk_tq_score=COALESCE(post_risk_tq_score, ?),
               risk_blocked_candidate=CASE
                   WHEN COALESCE(risk_blocked_candidate, 0)=0 THEN ?
                   ELSE risk_blocked_candidate
               END,
               risk_blocker=COALESCE(risk_blocker, ?),
               blocked_candidate_entry_price=COALESCE(blocked_candidate_entry_price, ?),
               blocked_candidate_tq_score=COALESCE(blocked_candidate_tq_score, ?),
               shadow_action=COALESCE(shadow_action, ?),
               shadow_entry_price=COALESCE(shadow_entry_price, ?),
               shadow_score=COALESCE(shadow_score, ?),
               shadow_reason=COALESCE(shadow_reason, ?),
               shadow_take_profit_price=COALESCE(shadow_take_profit_price, ?)
               WHERE id=?""",
            (
                score,
                components.get("trend"),
                components.get("momentum"),
                components.get("volatility"),
                components.get("derivatives"),
                components.get("macro"),
                components.get("historical_match"),
                components.get("data_quality"),
                components.get("risk_safety"),
                quality.get("primary_reason"),
                STRATEGY_VERSION,
                inferred_candidate_action,
                inferred_source,
                claude_conf,
                claude_reason,
                quality_json,
                score,
                components.get("trend"),
                components.get("momentum"),
                components.get("volatility"),
                components.get("derivatives"),
                components.get("macro"),
                components.get("historical_match"),
                components.get("data_quality"),
                components.get("risk_safety"),
                quality.get("primary_reason"),
                quality_json,
                score,
                risk_blocked_candidate,
                blocked_by,
                btc_price if risk_blocked_candidate else None,
                score if risk_blocked_candidate else None,
                shadow,
                shadow_entry,
                shadow_score,
                shadow_reason,
                shadow_tp,
                decision_id,
            ),
        )


def log_event(
    severity: str,
    event_type: str,
    message: str,
    *,
    actor: str = "system",
    source: str | None = None,
    symbol: str | None = "BTC/USD",
    status: str | None = None,
    metadata: dict | None = None,
    telegram_sent: bool = False,
    telegram_error: str | None = None,
) -> int:
    def _safe_meta(value):
        if isinstance(value, dict):
            out = {}
            for k, v in value.items():
                if str(k).lower() in {"token", "api_key", "password", "cookie", "authorization", "secret", "webhook_secret"}:
                    out[k] = "[REDACTED]"
                else:
                    out[k] = _safe_meta(v)
            return out
        if isinstance(value, list):
            return [_safe_meta(v) for v in value]
        text = str(value)
        lowered = text.lower()
        if any(x in lowered for x in ("anthropic_api_key=", "telegram_bot_token=", "webhook_secret=", "authorization:", "cookie:")):
            return "[REDACTED]"
        return value

    con = sqlite3.connect(DB_FILE)
    cur = con.execute(
        """INSERT INTO events
           (timestamp, severity, event_type, actor, source, symbol, status, message,
            metadata_json, telegram_sent, telegram_error)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            int(time.time()),
            severity.upper(),
            event_type,
            actor,
            source,
            symbol,
            status,
            message[:2000],
            json_dumps_safe(_safe_meta(metadata or {})),
            int(telegram_sent),
            (telegram_error or "")[:500],
        ),
    )
    con.commit()
    event_id = int(cur.lastrowid)
    con.close()
    return event_id


def update_event_telegram(event_id: int, sent: bool, error: str | None = None) -> None:
    con = sqlite3.connect(DB_FILE)
    con.execute(
        "UPDATE events SET telegram_sent=?, telegram_error=? WHERE id=?",
        (int(sent), (error or "")[:500], event_id),
    )
    con.commit()
    con.close()


def get_events(limit: int = 200) -> list[dict]:
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    con.close()
    out = []
    for row in rows:
        item = dict(row)
        try:
            item["metadata"] = json.loads(item.get("metadata_json") or "{}")
        except Exception:
            item["metadata"] = {}
        out.append(item)
    return out


def get_settings() -> dict:
    con = sqlite3.connect(DB_FILE)
    rows = con.execute("SELECT key, value FROM settings").fetchall()
    con.close()
    settings = DEFAULT_SETTINGS.copy()
    for key, value in rows:
        try:
            settings[key] = float(value)
        except (TypeError, ValueError):
            settings[key] = value
    return settings


def update_settings(new_values: dict) -> dict:
    allowed = {
        "trade_size_pct": (0.01, 0.50),
        "risk_per_trade_pct": (0.1, 5.0),
        "max_position_pct": (1.0, 50.0),
    }
    con = sqlite3.connect(DB_FILE)
    for key, value in new_values.items():
        if key not in allowed:
            continue
        low, high = allowed[key]
        num = float(value)
        if num > 1 and key == "trade_size_pct":
            num = num / 100
        num = max(low, min(high, num))
        con.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(num)),
        )
    con.commit()
    con.close()
    return get_settings()


def log_decision(
    market: dict,
    claude_out: dict,
    final: dict,
    trade_executed: bool,
    trigger: str = "unknown",
    candidate: dict | None = None,
    pre_risk_tq: dict | None = None,
    post_risk_tq: dict | None = None,
    strategy_version: str | None = None,
) -> None:
    """Record every scan decision to the decisions table for review."""
    audit = claude_out.get("_audit") or {}
    usage = claude_out.get("_api_usage") or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    cost = (
        input_tokens / 1_000_000 * AI_INPUT_USD_PER_MILLION_TOKENS
        + output_tokens / 1_000_000 * AI_OUTPUT_USD_PER_MILLION_TOKENS
    )
    candidate = candidate or {}
    pre_risk_tq = pre_risk_tq or market.get("pre_risk_trade_quality") or market.get("trade_quality") or {}
    post_risk_tq = post_risk_tq or market.get("post_risk_trade_quality") or market.get("trade_quality") or pre_risk_tq
    quality = post_risk_tq
    components = quality.get("components") or {}
    pre_components = pre_risk_tq.get("components") or {}
    post_components = post_risk_tq.get("components") or {}
    tq_score = quality.get("score")
    pre_tq_score = pre_risk_tq.get("score")
    candidate_action = (candidate.get("action") or candidate.get("candidate_action") or "HOLD").upper()
    candidate_source = candidate.get("source") or candidate.get("candidate_source") or "none"
    candidate_confidence = candidate.get("confidence")
    candidate_reason = candidate.get("reason") or candidate.get("candidate_reason") or ""
    risk_blocked_candidate = int(
        candidate_action == "BUY"
        and (final.get("action") or "").upper() == "HOLD"
        and bool(final.get("blocked_by"))
    )
    risk_blocker = final.get("blocked_by") if risk_blocked_candidate else None
    blocked_entry_price = float(market.get("price") or 0) if risk_blocked_candidate else None
    blocked_tq_score = float(pre_tq_score) if risk_blocked_candidate and pre_tq_score is not None else None
    smart_money = market.get("smart_money") or {}
    smart_money_score = smart_money.get("smart_money_score") or market.get("smart_money_score")
    smart_money_bias = smart_money.get("smart_money_bias") or market.get("smart_money_bias")
    smart_money_reason = smart_money.get("smart_money_reason") or market.get("smart_money_reason")
    shadow_action = None
    shadow_entry = shadow_score = shadow_stop = shadow_tp = None
    shadow_reason = None
    if final.get("action") == "HOLD" and pre_tq_score is not None and float(pre_tq_score) >= SHADOW_BUY_SCORE_THRESHOLD:
        price = float(market.get("price") or 0)
        atr = float(market.get("atr_14") or 0)
        if price > 0:
            shadow_action = "BUY"
            shadow_entry = price
            shadow_score = float(pre_tq_score)
            shadow_stop = round(price - ATR_INITIAL_STOP_MULT * atr, 2) if atr > 0 else None
            shadow_tp = round(price * 1.03, 2)
            shadow_reason = pre_risk_tq.get("primary_reason") or "quality_score_above_shadow_threshold"
    shadow_sm_action = None
    shadow_sm_score = None
    shadow_sm_bias = None
    shadow_sm_reason = None
    if final.get("action") == "HOLD" and smart_money_score is not None:
        try:
            sm_score_float = float(smart_money_score)
        except Exception:
            sm_score_float = 0.0
        if sm_score_float >= SMART_MONEY_MIN_SCORE_FOR_BUY_BONUS and smart_money_bias in {"bullish", "bearish"}:
            shadow_sm_action = "BUY" if smart_money_bias == "bullish" else "SELL"
            shadow_sm_score = sm_score_float
            shadow_sm_bias = smart_money_bias
            shadow_sm_reason = smart_money_reason or "smart_money_score_above_shadow_threshold"
    con = sqlite3.connect(DB_FILE)
    con.execute(
        f"""INSERT INTO decisions
           (timestamp, trigger, btc_price, rsi_14, fear_greed, funding_rate,
            claude_action, claude_conf, claude_reason,
            final_action, blocked_by, block_reason,
            position_usd, stop_price, trade_executed,
            risk_summary, invalid_if_json, historical_summary_json,
            trade_quality_json,
            strategy_version,
            candidate_action, candidate_source, candidate_confidence, candidate_reason,
            pre_risk_tq_json, pre_risk_tq_score, pre_risk_tq_trend, pre_risk_tq_momentum,
            pre_risk_tq_volatility, pre_risk_tq_derivatives, pre_risk_tq_macro,
            pre_risk_tq_historical_match, pre_risk_tq_data_quality, pre_risk_tq_risk_safety,
            pre_risk_tq_primary_reason,
            post_risk_tq_json, post_risk_tq_score,
            risk_blocked_candidate, risk_blocker, blocked_candidate_entry_price,
            blocked_candidate_tq_score,
            smart_money_score, smart_money_bias, smart_money_reason, smart_money_json,
            structure_state, liquidity_state, order_block_state, fvg_state,
            premium_discount_state, timeframe_alignment,
            shadow_smart_money_action, shadow_smart_money_score, shadow_smart_money_bias,
            shadow_smart_money_reason,
            tq_score, tq_trend, tq_momentum, tq_volatility, tq_derivatives, tq_macro,
            tq_historical_match, tq_data_quality, tq_risk_safety, tq_primary_reason,
            shadow_action, shadow_entry_price, shadow_score, shadow_reason,
            shadow_stop_price, shadow_take_profit_price,
            ai_model, ai_prompt, ai_response, input_tokens, output_tokens, api_cost_usd)
           VALUES ({','.join(['?'] * 77)})""",
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
            claude_out.get("risk_summary"),
            json_dumps_safe(claude_out.get("invalid_if", [])),
            json_dumps_safe(claude_out.get("historical_summary", {})),
            json_dumps_safe(quality),
            strategy_version or STRATEGY_VERSION,
            candidate_action,
            candidate_source,
            candidate_confidence,
            candidate_reason[:700],
            json_dumps_safe(pre_risk_tq),
            pre_tq_score,
            pre_components.get("trend"),
            pre_components.get("momentum"),
            pre_components.get("volatility"),
            pre_components.get("derivatives"),
            pre_components.get("macro"),
            pre_components.get("historical_match"),
            pre_components.get("data_quality"),
            pre_components.get("risk_safety"),
            pre_risk_tq.get("primary_reason"),
            json_dumps_safe(post_risk_tq),
            post_risk_tq.get("score"),
            risk_blocked_candidate,
            risk_blocker,
            blocked_entry_price,
            blocked_tq_score,
            smart_money_score,
            smart_money_bias,
            smart_money_reason,
            json_dumps_safe(smart_money),
            smart_money.get("structure_state"),
            smart_money.get("liquidity_state"),
            smart_money.get("order_block_state"),
            smart_money.get("fvg_state"),
            smart_money.get("premium_discount_state"),
            smart_money.get("timeframe_alignment"),
            shadow_sm_action,
            shadow_sm_score,
            shadow_sm_bias,
            shadow_sm_reason,
            tq_score,
            components.get("trend"),
            components.get("momentum"),
            components.get("volatility"),
            components.get("derivatives"),
            components.get("macro"),
            components.get("historical_match"),
            components.get("data_quality"),
            components.get("risk_safety"),
            quality.get("primary_reason"),
            shadow_action,
            shadow_entry,
            shadow_score,
            shadow_reason,
            shadow_stop,
            shadow_tp,
            audit.get("model"),
            audit.get("prompt"),
            audit.get("response"),
            input_tokens,
            output_tokens,
            round(cost, 8),
        ),
    )
    con.commit()
    con.close()


def json_dumps_safe(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return "{}"


def get_decisions(limit: int = 100) -> list[dict]:
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM decisions ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def api_usage_summary() -> dict:
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT timestamp, ai_model, input_tokens, output_tokens, api_cost_usd "
        "FROM decisions ORDER BY timestamp DESC LIMIT 1000"
    ).fetchall()
    con.close()
    items = [dict(r) for r in rows]
    total_calls = sum(1 for r in items if (r.get("input_tokens") or 0) or (r.get("output_tokens") or 0))
    total_input = sum(int(r.get("input_tokens") or 0) for r in items)
    total_output = sum(int(r.get("output_tokens") or 0) for r in items)
    total_cost = sum(float(r.get("api_cost_usd") or 0) for r in items)
    today_start = int(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    month_start = int(datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp())
    return {
        "total_calls": total_calls,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cost_usd": round(total_cost, 6),
        "today_calls": sum(1 for r in items if r["timestamp"] >= today_start and ((r.get("input_tokens") or 0) or (r.get("output_tokens") or 0))),
        "today_cost_usd": round(sum(float(r.get("api_cost_usd") or 0) for r in items if r["timestamp"] >= today_start), 6),
        "month_calls": sum(1 for r in items if r["timestamp"] >= month_start and ((r.get("input_tokens") or 0) or (r.get("output_tokens") or 0))),
        "month_cost_usd": round(sum(float(r.get("api_cost_usd") or 0) for r in items if r["timestamp"] >= month_start), 6),
        "pricing": {
            "input_usd_per_million_tokens": AI_INPUT_USD_PER_MILLION_TOKENS,
            "output_usd_per_million_tokens": AI_OUTPUT_USD_PER_MILLION_TOKENS,
        },
        "recent": items[:100],
    }


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
        usd_to_spend = round(balance * float(get_settings().get("trade_size_pct", TRADE_SIZE_PCT)), 2)

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
        "btc_price_usd":      round(current_btc_price, 2),
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
        "settings":           get_settings(),
    }
