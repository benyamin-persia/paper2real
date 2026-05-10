"""
Evaluate Claude decisions after future BTC price movement.

This is the AI feedback loop. It reads the SQLite decisions table, scores each
Claude/final action at 1h, 4h, and 24h, then writes reports Claude can read.

Run:
  python decision_evaluator.py

Outputs:
  data/reports/decision_evaluations.csv
  data/reports/ai_feedback_summary.json
  data/reports/ai_feedback_summary.md
"""

from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import pandas as pd

from config import DB_FILE


REPORT_DIR = Path("data/reports")
EVAL_CSV = REPORT_DIR / "decision_evaluations.csv"
SUMMARY_JSON = REPORT_DIR / "ai_feedback_summary.json"
SUMMARY_MD = REPORT_DIR / "ai_feedback_summary.md"
RISK_BLOCK_JSON = REPORT_DIR / "risk_block_performance.json"
RISK_BLOCK_CSV = REPORT_DIR / "risk_block_performance.csv"

LIVE_CANDLES = Path("data/raw/live_btc_15m.csv")
DAILY_CANDLES = Path("data/raw/btc_15m_raw.csv")

HORIZONS = {
    "15m": 15 * 60,
    "1h": 3600,
    "4h": 4 * 3600,
    "24h": 24 * 3600,
}

HORIZON_TOLERANCE = {
    "15m": 30 * 60,
    "1h": 90 * 60,
    "4h": 6 * 3600,
    "24h": 36 * 3600,
}

HOLD_MISSED_MOVE_PCT = 1.5


@dataclass(frozen=True)
class PricePoint:
    ts: int
    close: float
    source: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_epoch(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            return int(value)
        ts = pd.to_datetime(value, utc=True, errors="coerce")
        if pd.isna(ts):
            return None
        return int(ts.timestamp())
    except Exception:
        return None


def _read_decisions() -> list[dict]:
    db = Path(DB_FILE)
    if not db.exists():
        return []

    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute("SELECT * FROM decisions ORDER BY timestamp ASC").fetchall()
    except sqlite3.OperationalError:
        rows = []
    finally:
        con.close()
    return [dict(r) for r in rows]


def _update_shadow_future_returns(rows: list[dict]) -> None:
    db = Path(DB_FILE)
    if not db.exists() or not rows:
        return
    con = sqlite3.connect(db)
    try:
        for col in (
            "shadow_future_return_1h REAL",
            "shadow_future_return_4h REAL",
            "shadow_future_return_24h REAL",
        ):
            try:
                con.execute(f"ALTER TABLE decisions ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass
        for row in rows:
            if row["status"] != "SCORED" or not row.get("shadow_action") or row.get("return_pct") == "":
                continue
            col = {
                "1h": "shadow_future_return_1h",
                "4h": "shadow_future_return_4h",
                "24h": "shadow_future_return_24h",
            }.get(row["horizon"])
            if col:
                con.execute(
                    f"UPDATE decisions SET {col}=? WHERE id=?",
                    (float(row["return_pct"]), row["decision_id"]),
                )
        con.commit()
    finally:
        con.close()


def _update_shadow_smart_money_future_returns(rows: list[dict]) -> None:
    db = Path(DB_FILE)
    if not db.exists() or not rows:
        return
    con = sqlite3.connect(db)
    try:
        for col in (
            "shadow_smart_money_future_return_1h REAL",
            "shadow_smart_money_future_return_4h REAL",
            "shadow_smart_money_future_return_24h REAL",
        ):
            try:
                con.execute(f"ALTER TABLE decisions ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass
        for row in rows:
            if row["status"] != "SCORED" or not row.get("shadow_smart_money_action") or row.get("return_pct") == "":
                continue
            col = {
                "1h": "shadow_smart_money_future_return_1h",
                "4h": "shadow_smart_money_future_return_4h",
                "24h": "shadow_smart_money_future_return_24h",
            }.get(row["horizon"])
            if col:
                con.execute(
                    f"UPDATE decisions SET {col}=? WHERE id=?",
                    (float(row["return_pct"]), row["decision_id"]),
                )
        con.commit()
    finally:
        con.close()


def _blocked_outcome(return_pct: float) -> str:
    if return_pct >= 1.5:
        return "WIN"
    if return_pct <= -1.0:
        return "LOSS"
    return "NEUTRAL"


def _update_blocked_candidate_future_returns(rows: list[dict]) -> None:
    db = Path(DB_FILE)
    if not db.exists() or not rows:
        return
    con = sqlite3.connect(db)
    try:
        for col in (
            "blocked_candidate_future_return_1h REAL",
            "blocked_candidate_future_return_4h REAL",
            "blocked_candidate_future_return_24h REAL",
            "blocked_candidate_outcome_1h TEXT",
            "blocked_candidate_outcome_4h TEXT",
            "blocked_candidate_outcome_24h TEXT",
        ):
            try:
                con.execute(f"ALTER TABLE decisions ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass
        for row in rows:
            if (
                row["status"] != "SCORED"
                or int(row.get("risk_blocked_candidate") or 0) != 1
                or row.get("return_pct") == ""
            ):
                continue
            ret = float(row["return_pct"])
            ret_col = {
                "1h": "blocked_candidate_future_return_1h",
                "4h": "blocked_candidate_future_return_4h",
                "24h": "blocked_candidate_future_return_24h",
            }.get(row["horizon"])
            out_col = {
                "1h": "blocked_candidate_outcome_1h",
                "4h": "blocked_candidate_outcome_4h",
                "24h": "blocked_candidate_outcome_24h",
            }.get(row["horizon"])
            if ret_col and out_col:
                con.execute(
                    f"UPDATE decisions SET {ret_col}=?, {out_col}=? WHERE id=?",
                    (ret, _blocked_outcome(ret), row["decision_id"]),
                )
        con.commit()
    finally:
        con.close()


def _update_shadow_layer_future_returns(rows: list[dict], prefix: str) -> None:
    db = Path(DB_FILE)
    if not db.exists() or not rows:
        return
    action_col = f"shadow_{prefix}_action"
    future_cols = {
        "15m": f"shadow_{prefix}_future_return_15m",
        "1h": f"shadow_{prefix}_future_return_1h",
        "4h": f"shadow_{prefix}_future_return_4h",
        "24h": f"shadow_{prefix}_future_return_24h",
    }
    con = sqlite3.connect(db)
    try:
        for col in future_cols.values():
            try:
                con.execute(f"ALTER TABLE decisions ADD COLUMN {col} REAL")
            except sqlite3.OperationalError:
                pass
        for row in rows:
            if row["status"] != "SCORED" or not row.get(action_col) or row.get("return_pct") == "":
                continue
            col = future_cols.get(row["horizon"])
            if not col:
                continue
            ret = float(row["return_pct"])
            action = str(row.get(action_col) or "").upper()
            directional_ret = -ret if action.startswith("SELL") else ret
            con.execute(f"UPDATE decisions SET {col}=? WHERE id=?", (directional_ret, row["decision_id"]))
        con.commit()
    finally:
        con.close()


def _load_csv_prices(path: Path, source: str) -> list[PricePoint]:
    if not path.exists():
        return []
    try:
        df = pd.read_csv(path)
    except Exception:
        return []
    if "timestamp" not in df.columns or "close" not in df.columns:
        return []

    points: list[PricePoint] = []
    for _, row in df.iterrows():
        ts = _to_epoch(row.get("timestamp"))
        try:
            close = float(row.get("close"))
        except Exception:
            continue
        if ts and close > 0:
            points.append(PricePoint(ts=ts, close=close, source=source))
    return points


def _load_decision_prices(decisions: list[dict]) -> list[PricePoint]:
    points: list[PricePoint] = []
    for row in decisions:
        ts = _to_epoch(row.get("timestamp"))
        try:
            close = float(row.get("btc_price"))
        except Exception:
            continue
        if ts and close > 0:
            points.append(PricePoint(ts=ts, close=close, source="decisions"))
    return points


def _load_price_series(decisions: list[dict]) -> list[PricePoint]:
    points = []
    points.extend(_load_csv_prices(DAILY_CANDLES, "daily_csv"))
    points.extend(_load_csv_prices(LIVE_CANDLES, "live_15m_csv"))
    points.extend(_load_decision_prices(decisions))

    by_ts: dict[int, PricePoint] = {}
    source_rank = {"daily_csv": 1, "decisions": 2, "live_15m_csv": 3}
    for p in points:
        old = by_ts.get(p.ts)
        if old is None or source_rank[p.source] >= source_rank[old.source]:
            by_ts[p.ts] = p
    return sorted(by_ts.values(), key=lambda p: p.ts)


def _first_price_at_or_after(prices: list[PricePoint], target_ts: int, max_lag_s: int) -> PricePoint | None:
    for p in prices:
        if p.ts >= target_ts and p.ts - target_ts <= max_lag_s:
            return p
    return None


def _score_action(action: str, return_pct: float) -> tuple[str, bool | None]:
    action = (action or "HOLD").upper()
    if action == "BUY":
        return ("GOOD_BUY" if return_pct > 0 else "BAD_BUY", return_pct > 0)
    if action == "SELL":
        return ("GOOD_SELL" if return_pct < 0 else "BAD_SELL", return_pct < 0)
    if action == "HOLD":
        if return_pct >= HOLD_MISSED_MOVE_PCT:
            return "MISSED_UPSIDE", False
        if return_pct <= -HOLD_MISSED_MOVE_PCT:
            return "AVOIDED_DOWNSIDE", True
        return "OK_HOLD", None
    return "UNKNOWN_ACTION", None


def _bucket_rsi(value) -> str:
    try:
        v = float(value)
    except Exception:
        return "rsi_unknown"
    if v < 35:
        return "rsi_lt_35"
    if v < 45:
        return "rsi_35_45"
    if v < 55:
        return "rsi_45_55"
    if v < 65:
        return "rsi_55_65"
    return "rsi_gte_65"


def _bucket_fear_greed(value) -> str:
    try:
        v = float(value)
    except Exception:
        return "fg_unknown"
    if v < 25:
        return "fg_extreme_fear"
    if v < 45:
        return "fg_fear"
    if v < 60:
        return "fg_neutral"
    if v < 80:
        return "fg_greed"
    return "fg_extreme_greed"


def _funding_state(value) -> str:
    try:
        v = float(value)
    except Exception:
        return "funding_unknown"
    if v > 0.03:
        return "funding_hot_positive"
    if v > 0:
        return "funding_positive"
    if v < -0.01:
        return "funding_negative"
    return "funding_neutral"


def _condition_tags(row: dict) -> list[str]:
    return [
        _bucket_rsi(row.get("rsi_14")),
        _bucket_fear_greed(row.get("fear_greed")),
        _funding_state(row.get("funding_rate")),
        f"trigger_{row.get('trigger') or 'unknown'}",
        f"final_{(row.get('final_action') or 'UNKNOWN').upper()}",
        f"claude_{(row.get('claude_action') or 'UNKNOWN').upper()}",
        f"candidate_{(row.get('candidate_action') or 'UNKNOWN').upper()}",
        f"candidate_source_{row.get('candidate_source') or 'unknown'}",
    ]


def _evaluate_rows(decisions: list[dict], prices: list[PricePoint]) -> list[dict]:
    rows: list[dict] = []
    latest_price_ts = max((p.ts for p in prices), default=0)

    for d in decisions:
        decision_ts = _to_epoch(d.get("timestamp"))
        try:
            entry_price = float(d.get("btc_price"))
        except Exception:
            entry_price = 0
        if not decision_ts or entry_price <= 0:
            continue

        for horizon, seconds in HORIZONS.items():
            target_ts = decision_ts + seconds
            if latest_price_ts < target_ts:
                status = "PENDING"
                future = None
                return_pct = None
                claude_score = "PENDING"
                final_score = "PENDING"
                claude_good = None
                final_good = None
            else:
                future = _first_price_at_or_after(prices, target_ts, HORIZON_TOLERANCE[horizon])
                if future is None:
                    status = "NO_PRICE_AT_HORIZON"
                    return_pct = None
                    claude_score = "NO_PRICE"
                    final_score = "NO_PRICE"
                    claude_good = None
                    final_good = None
                else:
                    status = "SCORED"
                    return_pct = (future.close - entry_price) / entry_price * 100
                    claude_score, claude_good = _score_action(d.get("claude_action"), return_pct)
                    final_score, final_good = _score_action(d.get("final_action"), return_pct)

            rows.append(
                {
                    "decision_id": d.get("id"),
                    "decision_time": datetime.fromtimestamp(decision_ts, timezone.utc).isoformat(),
                    "horizon": horizon,
                    "status": status,
                    "entry_price": round(entry_price, 2),
                    "future_time": (
                        datetime.fromtimestamp(future.ts, timezone.utc).isoformat()
                        if future else ""
                    ),
                    "future_price": round(future.close, 2) if future else "",
                    "future_price_source": future.source if future else "",
                    "return_pct": round(return_pct, 4) if return_pct is not None else "",
                    "trigger": d.get("trigger"),
                    "rsi_14": d.get("rsi_14"),
                    "fear_greed": d.get("fear_greed"),
                    "funding_rate": d.get("funding_rate"),
                    "claude_action": d.get("claude_action"),
                    "claude_conf": d.get("claude_conf"),
                    "claude_score": claude_score,
                    "claude_good": claude_good,
                    "strategy_version": d.get("strategy_version"),
                    "candidate_action": d.get("candidate_action"),
                    "candidate_source": d.get("candidate_source"),
                    "candidate_confidence": d.get("candidate_confidence"),
                    "candidate_reason": d.get("candidate_reason"),
                    "pre_risk_tq_score": d.get("pre_risk_tq_score"),
                    "post_risk_tq_score": d.get("post_risk_tq_score"),
                    "final_action": d.get("final_action"),
                    "blocked_by": d.get("blocked_by"),
                    "block_reason": d.get("block_reason"),
                    "risk_blocked_candidate": d.get("risk_blocked_candidate") or 0,
                    "risk_blocker": d.get("risk_blocker") or d.get("blocked_by"),
                    "blocked_candidate_entry_price": d.get("blocked_candidate_entry_price"),
                    "blocked_candidate_tq_score": d.get("blocked_candidate_tq_score"),
                    "final_score": final_score,
                    "final_good": final_good,
                    "trade_executed": d.get("trade_executed"),
                    "tq_score": d.get("tq_score"),
                    "tq_primary_reason": d.get("tq_primary_reason"),
                    "shadow_action": d.get("shadow_action"),
                    "shadow_score": d.get("shadow_score"),
                    "shadow_reason": d.get("shadow_reason"),
                    "shadow_stop_price": d.get("shadow_stop_price"),
                    "shadow_take_profit_price": d.get("shadow_take_profit_price"),
                    "smart_money_score": d.get("smart_money_score"),
                    "smart_money_bias": d.get("smart_money_bias"),
                    "smart_money_reason": d.get("smart_money_reason"),
                    "structure_state": d.get("structure_state"),
                    "liquidity_state": d.get("liquidity_state"),
                    "order_block_state": d.get("order_block_state"),
                    "fvg_state": d.get("fvg_state"),
                    "premium_discount_state": d.get("premium_discount_state"),
                    "timeframe_alignment": d.get("timeframe_alignment"),
                    "shadow_smart_money_action": d.get("shadow_smart_money_action"),
                    "shadow_smart_money_score": d.get("shadow_smart_money_score"),
                    "shadow_smart_money_bias": d.get("shadow_smart_money_bias"),
                    "shadow_smart_money_reason": d.get("shadow_smart_money_reason"),
                    "shadow_ta_action": d.get("shadow_ta_action"),
                    "shadow_ta_score": d.get("shadow_ta_score"),
                    "shadow_ta_bias": d.get("shadow_ta_bias"),
                    "shadow_ta_reason": d.get("shadow_ta_reason"),
                    "shadow_ai_ta_action": d.get("shadow_ai_ta_action"),
                    "shadow_ai_ta_score": d.get("shadow_ai_ta_score"),
                    "shadow_ai_ta_bias": d.get("shadow_ai_ta_bias"),
                    "shadow_ai_ta_reason": d.get("shadow_ai_ta_reason"),
                    "condition_tags": "|".join(_condition_tags(d)),
                    "claude_reason": d.get("claude_reason"),
                }
            )
    return rows


def _pct(part: int, total: int) -> float | None:
    if total <= 0:
        return None
    return round(part / total * 100, 2)


def _action_accuracy(rows: list[dict], action_field: str, good_field: str, horizon: str) -> dict:
    scoped = [
        r for r in rows
        if r["horizon"] == horizon and r["status"] == "SCORED" and r[good_field] is not None
    ]
    by_action: dict[str, dict] = {}
    for r in scoped:
        action = (r.get(action_field) or "UNKNOWN").upper()
        item = by_action.setdefault(action, {"count": 0, "good": 0, "avg_return_pct": []})
        item["count"] += 1
        item["good"] += int(bool(r[good_field]))
        if r["return_pct"] != "":
            item["avg_return_pct"].append(float(r["return_pct"]))
    for item in by_action.values():
        item["accuracy_pct"] = _pct(item["good"], item["count"])
        vals = item.pop("avg_return_pct")
        item["avg_return_pct"] = round(mean(vals), 4) if vals else None
    return by_action


def _risk_engine_summary(rows: list[dict], horizon: str) -> dict:
    scoped = [
        r for r in rows
        if r["horizon"] == horizon
        and r["status"] == "SCORED"
        and (r.get("candidate_action") or "").upper() == "BUY"
        and (r.get("final_action") or "").upper() == "HOLD"
    ]
    saved_losses = [r for r in scoped if r["return_pct"] != "" and float(r["return_pct"]) < 0]
    blocked_winners = [r for r in scoped if r["return_pct"] != "" and float(r["return_pct"]) > 0]
    block_counts: dict[str, int] = {}
    for r in scoped:
        key = r.get("blocked_by") or "unknown"
        block_counts[key] = block_counts.get(key, 0) + 1
    return {
        "candidate_buy_blocked": len(scoped),
        "claude_buy_blocked": len([r for r in scoped if (r.get("candidate_source") or "") in {"claude", "both"}]),
        "trade_quality_buy_blocked": len([r for r in scoped if (r.get("candidate_source") or "") in {"trade_quality", "both"}]),
        "risk_engine_saved_losses": len(saved_losses),
        "risk_engine_blocked_winners": len(blocked_winners),
        "block_breakdown": dict(sorted(block_counts.items(), key=lambda x: x[1], reverse=True)),
    }


def build_risk_block_performance(rows: list[dict]) -> dict:
    blocked_ids = {
        r["decision_id"]
        for r in rows
        if int(r.get("risk_blocked_candidate") or 0) == 1
        and (r.get("candidate_action") or "").upper() == "BUY"
        and (r.get("final_action") or "").upper() == "HOLD"
    }
    by_blocker: dict[str, dict] = {}
    for r in rows:
        if r["decision_id"] not in blocked_ids:
            continue
        blocker = r.get("risk_blocker") or r.get("blocked_by") or "unknown"
        item = by_blocker.setdefault(
            blocker,
            {
                "decision_ids": set(),
                "returns": {"1h": [], "4h": [], "24h": []},
                "blocked_winners": {"1h": 0, "4h": 0, "24h": 0},
                "saved_losses": {"1h": 0, "4h": 0, "24h": 0},
                "neutral": {"1h": 0, "4h": 0, "24h": 0},
            },
        )
        item["decision_ids"].add(r["decision_id"])
        if r.get("status") != "SCORED" or r.get("return_pct") == "":
            continue
        horizon = r.get("horizon")
        if horizon not in item["returns"]:
            continue
        ret = float(r["return_pct"])
        item["returns"][horizon].append(ret)
        outcome = _blocked_outcome(ret)
        if outcome == "WIN":
            item["blocked_winners"][horizon] += 1
        elif outcome == "LOSS":
            item["saved_losses"][horizon] += 1
        else:
            item["neutral"][horizon] += 1

    blockers: dict[str, dict] = {}
    for blocker, item in by_blocker.items():
        count = len(item["decision_ids"])
        saved_4h = item["saved_losses"]["4h"]
        winners_4h = item["blocked_winners"]["4h"]
        if count < 30:
            verdict = "not_enough_data"
        elif saved_4h > winners_4h:
            verdict = "helping"
        elif winners_4h > saved_4h:
            verdict = "hurting"
        else:
            verdict = "neutral"
        blockers[blocker] = {
            "count": count,
            "avg_return_1h": _avg(item["returns"]["1h"]),
            "avg_return_4h": _avg(item["returns"]["4h"]),
            "avg_return_24h": _avg(item["returns"]["24h"]),
            "blocked_winners_1h": item["blocked_winners"]["1h"],
            "blocked_winners_4h": item["blocked_winners"]["4h"],
            "blocked_winners_24h": item["blocked_winners"]["24h"],
            "saved_losses_1h": item["saved_losses"]["1h"],
            "saved_losses_4h": item["saved_losses"]["4h"],
            "saved_losses_24h": item["saved_losses"]["24h"],
            "neutral_1h": item["neutral"]["1h"],
            "neutral_4h": item["neutral"]["4h"],
            "neutral_24h": item["neutral"]["24h"],
            "verdict": verdict,
        }

    total = len(blocked_ids)
    return {
        "generated_at": _utc_now(),
        "total_blocked_candidates": total,
        "minimum_required_before_tuning": 30,
        "ready_to_tune": total >= 30,
        "blockers": dict(sorted(blockers.items(), key=lambda x: x[1]["count"], reverse=True)),
    }


def _avg(vals: list[float]) -> float | None:
    return round(mean(vals), 4) if vals else None


def _condition_summary(rows: list[dict], horizon: str) -> dict:
    scored = [
        r for r in rows
        if r["horizon"] == horizon and r["status"] == "SCORED" and r["return_pct"] != ""
    ]
    tag_stats: dict[str, dict] = {}
    for r in scored:
        ret = float(r["return_pct"])
        for tag in str(r.get("condition_tags") or "").split("|"):
            if not tag:
                continue
            item = tag_stats.setdefault(tag, {"count": 0, "returns": []})
            item["count"] += 1
            item["returns"].append(ret)

    summarized = []
    for tag, item in tag_stats.items():
        if item["count"] < 2:
            continue
        summarized.append(
            {
                "condition": tag,
                "count": item["count"],
                "avg_return_pct": round(mean(item["returns"]), 4),
            }
        )

    best = sorted(summarized, key=lambda x: x["avg_return_pct"], reverse=True)[:8]
    worst = sorted(summarized, key=lambda x: x["avg_return_pct"])[:8]
    return {"best_conditions": best, "worst_conditions": worst}


def _build_summary(decisions: list[dict], prices: list[PricePoint], rows: list[dict]) -> dict:
    scored = [r for r in rows if r["status"] == "SCORED"]
    pending = [r for r in rows if r["status"] == "PENDING"]
    no_price = [r for r in rows if r["status"] == "NO_PRICE_AT_HORIZON"]
    shadow_rows = [r for r in rows if r.get("shadow_action")]
    shadow_scored = [r for r in shadow_rows if r["status"] == "SCORED" and r.get("return_pct") != ""]
    shadow_sm_rows = [r for r in rows if r.get("shadow_smart_money_action")]
    shadow_sm_scored = [r for r in shadow_sm_rows if r["status"] == "SCORED" and r.get("return_pct") != ""]
    candidate_buy_ids = {
        r["decision_id"] for r in rows if (r.get("candidate_action") or "").upper() == "BUY"
    }
    blocked_candidate_ids = {
        r["decision_id"] for r in rows if int(r.get("risk_blocked_candidate") or 0) == 1
    }
    latest_price_ts = max((p.ts for p in prices), default=None)

    summary = {
        "generated_at": _utc_now(),
        "db_file": DB_FILE,
        "decisions_total": len(decisions),
        "price_points_total": len(prices),
        "latest_price_time": (
            datetime.fromtimestamp(latest_price_ts, timezone.utc).isoformat()
            if latest_price_ts else None
        ),
        "rows_total": len(rows),
        "rows_scored": len(scored),
        "rows_pending": len(pending),
        "rows_no_price_at_horizon": len(no_price),
        "shadow_buys_total": len({r["decision_id"] for r in shadow_rows}),
        "shadow_rows_scored": len(shadow_scored),
        "shadow_smart_money_total": len({r["decision_id"] for r in shadow_sm_rows}),
        "shadow_smart_money_rows_scored": len(shadow_sm_scored),
        "candidate_buys_total": len(candidate_buy_ids),
        "risk_blocked_candidates_total": len(blocked_candidate_ids),
        "horizons": {},
        "recommendation": None,
    }

    for horizon in HORIZONS:
        hrows = [r for r in rows if r["horizon"] == horizon]
        hscored = [r for r in hrows if r["status"] == "SCORED"]
        buy_rows = [
            r for r in hscored
            if (r.get("claude_action") or "").upper() == "BUY" and r["claude_good"] is not None
        ]
        hold_rows = [
            r for r in hscored
            if (r.get("claude_action") or "").upper() == "HOLD" and r["claude_score"] == "MISSED_UPSIDE"
        ]
        summary["horizons"][horizon] = {
            "total": len(hrows),
            "scored": len(hscored),
            "pending": sum(1 for r in hrows if r["status"] == "PENDING"),
            "no_price_at_horizon": sum(1 for r in hrows if r["status"] == "NO_PRICE_AT_HORIZON"),
            "claude_accuracy": _action_accuracy(hrows, "claude_action", "claude_good", horizon),
            "final_accuracy": _action_accuracy(hrows, "final_action", "final_good", horizon),
            "claude_buy_accuracy_pct": _pct(sum(1 for r in buy_rows if r["claude_good"]), len(buy_rows)),
            "missed_upside_holds": len(hold_rows),
            "risk_engine": _risk_engine_summary(hrows, horizon),
            "conditions": _condition_summary(hrows, horizon),
            "shadow_buy": _shadow_summary(hrows),
            "shadow_smart_money": _shadow_smart_money_summary(hrows),
        }

    if not decisions:
        summary["recommendation"] = "No decisions logged yet. Run paper trading scans first."
    elif not scored:
        summary["recommendation"] = (
            "Decisions exist, but not enough future price data exists yet. "
            "Keep paper trading and rerun this evaluator after 4-24 hours."
        )
    else:
        buy_4h = summary["horizons"]["4h"]["claude_buy_accuracy_pct"]
        if buy_4h is not None and buy_4h < 50:
            summary["recommendation"] = "Claude BUY calls are weak at 4h. Tighten BUY prompt/risk filters before increasing trade frequency."
        else:
            summary["recommendation"] = "Keep collecting decisions. Do not change strategy until sample size is larger."
    return summary


def _shadow_summary(rows: list[dict]) -> dict:
    scoped = [
        r for r in rows
        if r.get("shadow_action") == "BUY" and r["status"] == "SCORED" and r.get("return_pct") != ""
    ]
    vals = [float(r["return_pct"]) for r in scoped]
    if not vals:
        return {"count": 0, "avg_return_pct": None, "win_rate_pct": None}
    return {
        "count": len(vals),
        "avg_return_pct": round(mean(vals), 4),
        "win_rate_pct": _pct(sum(1 for v in vals if v > 0), len(vals)),
        "missed_big_upside": sum(1 for v in vals if v > HOLD_MISSED_MOVE_PCT),
        "would_have_lost": sum(1 for v in vals if v < 0),
    }


def _shadow_smart_money_summary(rows: list[dict]) -> dict:
    scoped = [
        r for r in rows
        if r.get("shadow_smart_money_action") and r["status"] == "SCORED" and r.get("return_pct") != ""
    ]
    vals = []
    for r in scoped:
        raw = float(r["return_pct"])
        action = (r.get("shadow_smart_money_action") or "").upper()
        vals.append(raw if action == "BUY" else -raw if action == "SELL" else raw)
    if not vals:
        return {"count": 0, "avg_directional_return_pct": None, "win_rate_pct": None}
    return {
        "count": len(vals),
        "avg_directional_return_pct": round(mean(vals), 4),
        "win_rate_pct": _pct(sum(1 for v in vals if v > 0), len(vals)),
        "missed_big_directional_move": sum(1 for v in vals if v > HOLD_MISSED_MOVE_PCT),
        "would_have_lost": sum(1 for v in vals if v < 0),
    }


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_risk_block_csv(report: dict) -> None:
    rows = []
    for blocker, stats in (report.get("blockers") or {}).items():
        row = {"blocker": blocker}
        row.update(stats)
        rows.append(row)
    _write_csv(RISK_BLOCK_CSV, rows)


def _write_markdown(summary: dict) -> None:
    lines = [
        "# AI Feedback Summary",
        "",
        f"Generated: {summary['generated_at']}",
        f"Decisions: {summary['decisions_total']}",
        f"Scored rows: {summary['rows_scored']}",
        f"Pending rows: {summary['rows_pending']}",
        f"Shadow BUYs: {summary.get('shadow_buys_total', 0)}",
        f"Shadow rows scored: {summary.get('shadow_rows_scored', 0)}",
        f"Shadow Smart Money candidates: {summary.get('shadow_smart_money_total', 0)}",
        f"Shadow Smart Money rows scored: {summary.get('shadow_smart_money_rows_scored', 0)}",
        f"Recommendation: {summary['recommendation']}",
        "",
        "## Horizons",
    ]
    for horizon, data in summary["horizons"].items():
        lines.extend(
            [
                "",
                f"### {horizon}",
                f"- Scored: {data['scored']} / {data['total']}",
                f"- Claude BUY accuracy: {data['claude_buy_accuracy_pct']}",
                f"- Missed upside HOLDs: {data['missed_upside_holds']}",
                f"- Risk engine saved losses: {data['risk_engine']['risk_engine_saved_losses']}",
                f"- Risk engine blocked winners: {data['risk_engine']['risk_engine_blocked_winners']}",
                f"- Shadow BUY count: {data['shadow_buy']['count']}",
                f"- Shadow BUY avg return: {data['shadow_buy']['avg_return_pct']}",
                f"- Shadow BUY win rate: {data['shadow_buy']['win_rate_pct']}",
                f"- Shadow Smart Money count: {data['shadow_smart_money']['count']}",
                f"- Shadow Smart Money directional avg return: {data['shadow_smart_money']['avg_directional_return_pct']}",
                f"- Shadow Smart Money directional win rate: {data['shadow_smart_money']['win_rate_pct']}",
            ]
        )
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> dict:
    decisions = _read_decisions()
    prices = _load_price_series(decisions)
    rows = _evaluate_rows(decisions, prices)
    _update_shadow_future_returns(rows)
    _update_shadow_smart_money_future_returns(rows)
    _update_blocked_candidate_future_returns(rows)
    _update_shadow_layer_future_returns(rows, "ta")
    _update_shadow_layer_future_returns(rows, "ai_ta")
    summary = _build_summary(decisions, prices, rows)
    risk_block_report = build_risk_block_performance(rows)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(EVAL_CSV, rows)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    RISK_BLOCK_JSON.write_text(json.dumps(risk_block_report, indent=2), encoding="utf-8")
    _write_risk_block_csv(risk_block_report)
    _write_markdown(summary)

    print("Decision evaluation complete")
    print(f"  Decisions:    {summary['decisions_total']}")
    print(f"  Price points: {summary['price_points_total']}")
    print(f"  Scored rows:  {summary['rows_scored']}")
    print(f"  Pending rows: {summary['rows_pending']}")
    print(f"  Report JSON:  {SUMMARY_JSON}")
    print(f"  Report CSV:   {EVAL_CSV}")
    print(f"  Risk blocks:  {RISK_BLOCK_JSON}")
    print(f"  Summary MD:   {SUMMARY_MD}")
    print(f"  Next:         {summary['recommendation']}")
    return summary


if __name__ == "__main__":
    run()
