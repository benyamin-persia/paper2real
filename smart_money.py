"""Smart Money Structure Layer for Paper2Real.

This is evidence/scoring only. It does not execute trades and does not bypass
risk_engine.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from config import SMART_MONEY_SWING_LENGTH

import fair_value_gaps
import liquidity
import market_structure
import order_blocks
import premium_discount


SUMMARY_JSON = Path("data/reports/smart_money_summary.json")
LIVE_1H = Path("data/raw/live_btc_1h.csv")
LIVE_4H = Path("data/raw/live_btc_4h.csv")


def prepare_timeframes(df_15m: pd.DataFrame, closed_only: bool = True, save: bool = True) -> dict[str, pd.DataFrame]:
    base = market_structure.clean_candles(df_15m)
    if closed_only and len(base) > 2:
        base = base.iloc[:-1].copy()
    frames = {"15m": base}
    indexed = base.set_index("timestamp")
    for tf, rule in (("1h", "1h"), ("4h", "4h")):
        resampled = indexed.resample(rule, label="right", closed="right").agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        resampled = resampled.dropna(subset=["open", "high", "low", "close"]).reset_index()
        if closed_only and len(resampled) > 2:
            resampled = resampled.iloc[:-1].copy()
        frames[tf] = resampled

    if save:
        LIVE_1H.parent.mkdir(parents=True, exist_ok=True)
        frames["1h"].to_csv(LIVE_1H, index=False)
        frames["4h"].to_csv(LIVE_4H, index=False)
    return frames


def analyze(df_15m: pd.DataFrame, context: dict | None = None, save: bool = True) -> dict:
    context = context or {}
    frames = prepare_timeframes(df_15m, closed_only=True, save=save)
    structure = market_structure.run(frames, swing_length=SMART_MONEY_SWING_LENGTH, save=save)
    liq = liquidity.run(frames, swing_length=SMART_MONEY_SWING_LENGTH, save=save)
    obs = order_blocks.run(frames, structure, save=save)
    fvgs = fair_value_gaps.run(frames, structure, obs, save=save)
    zones = premium_discount.run(frames, structure, save=save)
    score = score_smart_money(structure, liq, obs, fvgs, zones, context)

    result = {
        **score,
        "market_structure": _compact_structure(structure),
        "liquidity": _compact_liquidity(liq),
        "order_blocks": _compact_order_blocks(obs),
        "fair_value_gaps": _compact_fvgs(fvgs),
        "premium_discount": zones,
    }
    if save:
        SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def score_smart_money(
    structure: dict[str, dict],
    liq: dict[str, dict],
    obs: dict[str, dict],
    fvgs: dict[str, dict],
    zones: dict[str, dict],
    context: dict,
) -> dict:
    trends = {tf: (structure.get(tf) or {}).get("trend", "neutral") for tf in ("15m", "1h", "4h")}
    bullish_align = sum(1 for v in trends.values() if v == "bullish")
    bearish_align = sum(1 for v in trends.values() if v == "bearish")

    latest_events = [((structure.get(tf) or {}).get("latest_event") or {}) for tf in ("15m", "1h", "4h")]
    latest_sweeps = [((liq.get(tf) or {}).get("latest_sweep") or {}) for tf in ("15m", "1h", "4h")]
    active_obs = [x for tf in obs.values() for x in (tf.get("active_order_blocks") or [])]
    active_fvgs = [x for tf in fvgs.values() for x in (tf.get("active_fvgs") or [])]
    zone_15m = (zones.get("15m") or {}).get("current_zone")
    zone_1h = (zones.get("1h") or {}).get("current_zone")

    bull = 0
    bear = 0
    reasons: list[str] = []

    if bullish_align >= 2:
        bull += 15
        reasons.append("higher_timeframe_bullish")
    if bearish_align >= 2:
        bear += 15
        reasons.append("higher_timeframe_bearish")

    if any(str(e.get("event_type", "")).startswith("bullish") for e in latest_events[-2:]):
        bull += 15
        reasons.append("bullish_bos_or_choch")
    if any(str(e.get("event_type", "")).startswith("bearish") for e in latest_events[-2:]):
        bear += 15
        reasons.append("bearish_bos_or_choch")

    if any(s.get("sweep_type") == "bullish_sweep" for s in latest_sweeps):
        bull += 15
        reasons.append("bullish_liquidity_sweep")
    if any(s.get("sweep_type") == "bearish_sweep" for s in latest_sweeps):
        bear += 15
        reasons.append("bearish_liquidity_sweep")

    if zone_15m == "discount" or zone_1h == "discount":
        bull += 15
        reasons.append("price_in_discount")
    if zone_15m == "premium" or zone_1h == "premium":
        bear += 15
        reasons.append("price_in_premium")

    if any(ob.get("type") == "bullish" for ob in active_obs):
        bull += 15
        reasons.append("active_bullish_order_block")
    if any(ob.get("type") == "bearish" for ob in active_obs):
        bear += 15
        reasons.append("active_bearish_order_block")

    if any(f.get("type") == "bullish" for f in active_fvgs):
        bull += 15
        reasons.append("active_bullish_fvg")
    if any(f.get("type") == "bearish" for f in active_fvgs):
        bear += 15
        reasons.append("active_bearish_fvg")

    if context.get("macd_bullish") and float(context.get("rsi_14") or 50) >= 45:
        bull += 10
        reasons.append("momentum_confirms_bullish")
    if not context.get("macd_bullish") and float(context.get("rsi_14") or 50) <= 55:
        bear += 10
        reasons.append("momentum_confirms_bearish")

    bull = min(100, bull)
    bear = min(100, bear)
    if bull > bear and bull >= 45:
        bias = "bullish"
        score = bull
    elif bear > bull and bear >= 45:
        bias = "bearish"
        score = bear
    else:
        bias = "neutral"
        score = max(bull, bear)

    alignment = "bullish" if bullish_align >= 2 else "bearish" if bearish_align >= 2 else "mixed"
    return {
        "smart_money_score": int(score),
        "smart_money_bullish_score": int(bull),
        "smart_money_bearish_score": int(bear),
        "smart_money_bias": bias,
        "smart_money_reason": ", ".join(reasons[:8]) if reasons else "no_clear_structure_edge",
        "structure_state": (structure.get("15m") or {}).get("structure_state", "unknown"),
        "liquidity_state": (liq.get("15m") or {}).get("liquidity_state", "unknown"),
        "order_block_state": (obs.get("15m") or {}).get("order_block_state", "unknown"),
        "fvg_state": (fvgs.get("15m") or {}).get("fvg_state", "unknown"),
        "premium_discount_state": (zones.get("15m") or {}).get("current_zone", "unknown"),
        "timeframe_alignment": alignment,
    }


def _compact_structure(results: dict[str, dict]) -> dict:
    return {
        tf: {
            "trend": r.get("trend"),
            "structure_state": r.get("structure_state"),
            "latest_event": r.get("latest_event"),
            "events_count": len(r.get("events") or []),
            "swings_count": len(r.get("swings") or []),
        }
        for tf, r in results.items()
    }


def _compact_liquidity(results: dict[str, dict]) -> dict:
    return {
        tf: {
            "liquidity_state": r.get("liquidity_state"),
            "latest_sweep": r.get("latest_sweep"),
            "active_count": len(r.get("active_zones") or []),
        }
        for tf, r in results.items()
    }


def _compact_order_blocks(results: dict[str, dict]) -> dict:
    return {
        tf: {
            "order_block_state": r.get("order_block_state"),
            "active_count": len(r.get("active_order_blocks") or []),
            "latest_order_block": r.get("latest_order_block"),
        }
        for tf, r in results.items()
    }


def _compact_fvgs(results: dict[str, dict]) -> dict:
    return {
        tf: {
            "fvg_state": r.get("fvg_state"),
            "active_count": len(r.get("active_fvgs") or []),
            "latest_fvg": r.get("latest_fvg"),
        }
        for tf, r in results.items()
    }


if __name__ == "__main__":
    path = Path("data/raw/live_btc_15m.csv")
    df = pd.read_csv(path)
    print(json.dumps(analyze(df), indent=2))
