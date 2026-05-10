from __future__ import annotations

import json
from pathlib import Path

import chart_patterns
import support_resistance
import technical_analysis


REPORT_DIR = Path("data/reports")
FORECAST_JSON = REPORT_DIR / "ta_forecast.json"


def _latest_indicators():
    data = technical_analysis.run(save=True)
    return data.get("latest") or {}


def _nearest_zones(price: float, zones: list[dict]):
    supports = [z for z in zones if "support" in z.get("zone_type", "") or "low" in z.get("zone_type", "")]
    resistances = [z for z in zones if "resistance" in z.get("zone_type", "") or "high" in z.get("zone_type", "")]
    support = max((z for z in supports if z["price_high"] <= price), key=lambda z: z["price_high"], default=None)
    resistance = min((z for z in resistances if z["price_low"] >= price), key=lambda z: z["price_low"], default=None)
    return support, resistance


def run(save: bool = True) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    latest = _latest_indicators()
    zones_payload = support_resistance.run(save=True)
    patterns_payload = chart_patterns.run(save=True)
    zones = zones_payload.get("zones") or []
    patterns = patterns_payload.get("patterns") or []
    current = latest.get("15m") or latest.get("1h") or {}
    price = float(current.get("close") or 0)
    bullish = 0
    bearish = 0
    bull_evidence, bear_evidence, neutral_evidence = [], [], []
    for tf, row in latest.items():
        if not row:
            continue
        weight = 15 if tf in {"1h", "4h"} else 8
        if row.get("trend_state") == "bullish":
            bullish += weight
            bull_evidence.append(f"{tf} trend bullish")
        elif row.get("trend_state") == "bearish":
            bearish += weight
            bear_evidence.append(f"{tf} trend bearish")
        else:
            neutral_evidence.append(f"{tf} trend neutral")
        for ema in ("ema20", "ema50", "ema200"):
            if row.get(ema) and row.get("close"):
                if row["close"] > row[ema]:
                    bullish += 10
                    bull_evidence.append(f"{tf} price above {ema.upper()}")
                else:
                    bearish += 10
                    bear_evidence.append(f"{tf} price below {ema.upper()}")
        mom = row.get("momentum_state")
        if mom in {"bullish", "recovering", "oversold"}:
            bullish += 10
            bull_evidence.append(f"{tf} momentum {mom}")
        elif mom in {"bearish", "weakening", "overbought"}:
            bearish += 10
            bear_evidence.append(f"{tf} momentum {mom}")
        if row.get("volume_quality") == "reliable" and row.get("volume_ratio") and row["volume_ratio"] >= 1.5:
            if row.get("trend_state") == "bullish":
                bullish += 5
                bull_evidence.append(f"{tf} volume confirms")
            elif row.get("trend_state") == "bearish":
                bearish += 5
                bear_evidence.append(f"{tf} volume confirms")
        elif row.get("volume_quality") != "reliable":
            neutral_evidence.append(f"{tf} volume unreliable")
        if row.get("bb_squeeze"):
            neutral_evidence.append(f"{tf} Bollinger squeeze active")
    for p in patterns:
        if p.get("direction") == "bullish":
            bullish += 10
            bull_evidence.append(p.get("pattern_type"))
        elif p.get("direction") == "bearish":
            bearish += 10
            bear_evidence.append(p.get("pattern_type"))
    score = max(bullish, bearish)
    if score < 35 or abs(bullish - bearish) < 12:
        bias = "neutral"
    else:
        bias = "bullish" if bullish > bearish else "bearish"
    disagreements = len({(row or {}).get("trend_state") for row in latest.values() if row})
    confidence = min(100, max(0, score - min(bullish, bearish) * 0.35))
    if disagreements > 1:
        confidence -= 15
        neutral_evidence.append("15m, 1h, and 4h are not fully aligned")
    if any((row or {}).get("bb_squeeze") for row in latest.values()):
        confidence -= 10
    confidence = round(max(0, min(100, confidence)), 2)
    support, resistance = _nearest_zones(price, zones)
    prediction = "sideways" if bias == "neutral" else "up" if bias == "bullish" else "down"
    payload = {
        "ta_score": round(min(100, score), 2),
        "ta_bias": bias,
        "ta_confidence": confidence,
        "prediction_15m": prediction,
        "prediction_1h": prediction if confidence >= 55 else "unknown",
        "prediction_4h": prediction if confidence >= 60 else "unknown",
        "prediction_24h": prediction if confidence >= 65 else "unknown",
        "ta_reason": "; ".join((bull_evidence if bias == "bullish" else bear_evidence if bias == "bearish" else neutral_evidence)[:6]) or "mixed evidence",
        "bullish_evidence": bull_evidence[:20],
        "bearish_evidence": bear_evidence[:20],
        "neutral_evidence": neutral_evidence[:20],
        "invalidation_level": support.get("price_low") if bias == "bullish" and support else resistance.get("price_high") if bias == "bearish" and resistance else None,
        "nearest_support": support,
        "nearest_resistance": resistance,
        "risk_level": "high" if confidence < 50 else "medium" if disagreements > 1 else "low",
        "ta_json": {},
        "shadow_only": True,
        "can_execute_trade": False,
    }
    payload["ta_json"] = {k: v for k, v in payload.items() if k != "ta_json"}
    if save:
        FORECAST_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
