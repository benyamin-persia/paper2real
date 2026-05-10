from __future__ import annotations

import json
from pathlib import Path

from config import (
    AI_TA_MODEL,
    AI_TA_SHADOW_ONLY,
    AI_TA_MIN_TQ_TO_CALL,
    AI_TA_MIN_SMART_MONEY_TO_CALL,
)


REPORT_DIR = Path("data/reports")
CURRENT_JSON = REPORT_DIR / "ai_technical_analyst.json"


def build_context(market: dict, candidate: dict | None = None, final: dict | None = None) -> dict:
    ta = market.get("ta_forecast") or {}
    return {
        "scan_time": market.get("candle_timestamp"),
        "btc_price": market.get("price"),
        "scan_mode": market.get("scan_mode"),
        "technical_indicators": market.get("technical_indicators", {}).get("latest", {}),
        "support_zones": (market.get("support_resistance") or {}).get("zones", [])[:20],
        "resistance_zones": (market.get("support_resistance") or {}).get("zones", [])[:20],
        "chart_patterns": (market.get("chart_patterns") or {}).get("patterns", [])[:20],
        "TA_forecast": ta,
        "Smart_Money_score": market.get("smart_money_score"),
        "Smart_Money_bias": market.get("smart_money_bias"),
        "Smart_Money_structure_state": market.get("structure_state"),
        "latest_BOS_CHoCH": market.get("structure_state"),
        "liquidity_state": market.get("liquidity_state"),
        "order_blocks": market.get("order_block_state"),
        "FVG_state": market.get("fvg_state"),
        "premium_discount": market.get("premium_discount_state"),
        "Trade_Quality_score": (market.get("pre_risk_trade_quality") or market.get("trade_quality") or {}).get("score"),
        "candidate_action": (candidate or {}).get("action"),
        "risk_engine_final_action": (final or {}).get("action"),
        "risk_engine_blocked_by": (final or {}).get("blocked_by"),
        "risk_engine_reason": (final or {}).get("reason"),
    }


def should_call(market: dict, candidate: dict | None = None, final: dict | None = None) -> tuple[bool, str]:
    tq = float((market.get("pre_risk_trade_quality") or market.get("trade_quality") or {}).get("score") or 0)
    sm = float(market.get("smart_money_score") or 0)
    ta_score = float((market.get("ta_forecast") or {}).get("ta_score") or 0)
    candidate_action = ((candidate or {}).get("action") or "").upper()
    blocked_buy = candidate_action == "BUY" and (final or {}).get("blocked_by")
    patterns = (market.get("chart_patterns") or {}).get("patterns") or []
    if tq >= AI_TA_MIN_TQ_TO_CALL:
        return True, "trade_quality_threshold"
    if sm >= AI_TA_MIN_SMART_MONEY_TO_CALL:
        return True, "smart_money_threshold"
    if ta_score >= 60:
        return True, "ta_score_threshold"
    if candidate_action in {"BUY", "SELL"}:
        return True, "candidate_action"
    if blocked_buy:
        return True, "risk_blocked_buy_candidate"
    if patterns:
        return True, "chart_pattern_detected"
    if market.get("scan_mode") in {"scheduled", "manual", "webhook"}:
        return True, "live_paper_scan"
    if market.get("scan_mode") == "learning_only" and market.get("meaningful_change_reason"):
        return True, "meaningful_learning_scan"
    return False, "boring_duplicate_scan"


def _validated(payload: dict) -> dict:
    payload["should_trade"] = False
    payload["risk_engine_respected"] = True
    payload["ai_ta_score"] = max(0, min(100, float(payload.get("ai_ta_score") or 0)))
    payload["ai_ta_confidence"] = max(0, min(100, float(payload.get("ai_ta_confidence") or 0)))
    if payload["ai_ta_bias"] not in {"bullish", "bearish", "neutral"}:
        payload["ai_ta_bias"] = "neutral"
    for key in ("prediction_15m", "prediction_1h", "prediction_4h", "prediction_24h"):
        if payload.get(key) not in {"up", "down", "sideways", "unknown"}:
            payload[key] = "unknown"
    if payload.get("risk_level") not in {"low", "medium", "high"}:
        payload["risk_level"] = "medium"
    return payload


def analyze(market: dict, candidate: dict | None = None, final: dict | None = None, force: bool = False) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    called, reason = should_call(market, candidate, final)
    if not called and not force:
        return {
            "ai_ta_called": 0,
            "ai_ta_model": AI_TA_MODEL,
            "ai_ta_bias": "neutral",
            "ai_ta_score": 0,
            "ai_ta_confidence": 0,
            "ai_ta_reason": reason,
            "should_trade": False,
            "risk_engine_respected": True,
        }
    ta = market.get("ta_forecast") or {}
    score = float(ta.get("ta_score") or 0)
    confidence = float(ta.get("ta_confidence") or 0)
    bias = ta.get("ta_bias") or "neutral"
    if confidence < 65:
        bias = "neutral"
    payload = _validated(
        {
            "ai_ta_called": 1,
            "ai_ta_model": AI_TA_MODEL,
            "ai_ta_bias": bias,
            "ai_ta_score": score if bias != "neutral" else min(score, 55),
            "ai_ta_confidence": confidence if bias != "neutral" else min(confidence, 60),
            "prediction_15m": ta.get("prediction_15m", "unknown"),
            "prediction_1h": ta.get("prediction_1h", "unknown"),
            "prediction_4h": ta.get("prediction_4h", "unknown"),
            "prediction_24h": ta.get("prediction_24h", "unknown"),
            "best_horizon": "4h" if confidence >= 60 else "none",
            "bullish_evidence": ta.get("bullish_evidence", []),
            "bearish_evidence": ta.get("bearish_evidence", []),
            "neutral_evidence": ta.get("neutral_evidence", []),
            "main_reason": ta.get("ta_reason", "structured TA evidence reviewed"),
            "ai_ta_reason": ta.get("ta_reason", "structured TA evidence reviewed"),
            "invalidation_level": ta.get("invalidation_level"),
            "nearest_support": ta.get("nearest_support"),
            "nearest_resistance": ta.get("nearest_resistance"),
            "risk_level": ta.get("risk_level", "medium"),
            "should_trade": False,
            "risk_engine_respected": True,
            "notes": "Shadow-only deterministic analyst layer; no execution and no risk override.",
            "call_reason": reason,
            "shadow_only": AI_TA_SHADOW_ONLY,
            "input_context": build_context(market, candidate, final),
        }
    )
    CURRENT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(analyze({}, force=True), indent=2))
