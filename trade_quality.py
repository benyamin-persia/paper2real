"""Deterministic trade quality scoring for dashboard and audit logs.

This is not an LLM decision. It is an explainable score that shows why the
system is or is not close to a trade.
"""

from __future__ import annotations


def _num(value, default=0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def score(market: dict, historical: dict | None = None, risk: dict | None = None) -> dict:
    historical = historical or {}
    risk = risk or {}

    price = _num(market.get("price"))
    ema50 = _num(market.get("ema_50"))
    ema200 = _num(market.get("ema_200"))
    rsi = _num(market.get("rsi_14"), 50)
    stoch = _num(market.get("stoch_k"), 50)
    funding = _num(market.get("funding_rate"))
    vix = _num(market.get("vix"), 20)
    dxy = _num(market.get("dxy"), 100)
    bb_width = _num(market.get("bb_width"))
    win_rate = _num(historical.get("historical_win_rate_pct"), 50)
    avg_4h = _num(historical.get("avg_return_4h"))
    avg_24h = _num(historical.get("avg_return_24h"))

    trend = 0
    trend += 8 if market.get("above_ema200") else 0
    trend += 5 if market.get("above_ema50") else 0
    trend += 4 if market.get("ema_bullish") else 0
    trend += 3 if price and ema200 and price > ema200 * 1.02 else 0
    trend = _clamp(trend, 0, 20)

    momentum = 0
    if 35 <= rsi <= 55:
        momentum += 9
    elif 55 < rsi <= 65:
        momentum += 5
    elif rsi < 35:
        momentum += 6
    if stoch < 30:
        momentum += 7
    elif stoch < 70:
        momentum += 4
    if market.get("macd_bullish"):
        momentum += 4
    momentum = _clamp(momentum, 0, 20)

    volatility = 8
    if 0 < bb_width < 0.025:
        volatility += 4
    if _num(market.get("atr_14")) > 0:
        volatility += 3
    volatility = _clamp(volatility, 0, 15)

    derivatives = 6
    if funding < -0.01:
        derivatives -= 3
    elif 0 <= funding <= 0.03:
        derivatives += 3
    if _num(market.get("long_short_ratio"), 1) > 1.5:
        derivatives -= 2
    if _num(market.get("etf_flow_usd")) > 0:
        derivatives += 3
    elif _num(market.get("etf_flow_usd")) < 0:
        derivatives -= 2
    derivatives = _clamp(derivatives, 0, 15)

    macro = 5
    if vix < 25:
        macro += 2
    if dxy < 105:
        macro += 2
    if _num(market.get("sp500")) > 0:
        macro += 1
    macro = _clamp(macro, 0, 10)

    hist = 4
    hist += (win_rate - 50) / 10
    hist += 1 if avg_4h > 0 else -1 if avg_4h < 0 else 0
    hist += 1 if avg_24h > 0 else -1 if avg_24h < 0 else 0
    hist = _clamp(hist, 0, 10)

    data_quality = 10
    penalties = []
    if market.get("volume_quality") != "reliable":
        data_quality -= 3
        penalties.append("volume_unreliable")
    if market.get("events_unavailable"):
        data_quality -= 3
        penalties.append("events_unavailable")
    if market.get("twitter_unavailable"):
        data_quality -= 1
        penalties.append("twitter_unavailable")
    if market.get("fear_greed_index") is None:
        data_quality -= 1
        penalties.append("fear_greed_missing")
    data_quality = _clamp(data_quality, 0, 10)

    risk_safety = 10
    if risk.get("blocked_by"):
        risk_safety = 0
    elif market.get("stablecoin_depeg") or market.get("exchange_hack_alert"):
        risk_safety = 0
    elif market.get("events_unavailable"):
        risk_safety = 4

    components = {
        "trend": round(trend, 1),
        "momentum": round(momentum, 1),
        "volatility": round(volatility, 1),
        "derivatives": round(derivatives, 1),
        "macro": round(macro, 1),
        "historical_match": round(hist, 1),
        "data_quality": round(data_quality, 1),
        "risk_safety": round(risk_safety, 1),
    }
    total = round(sum(components.values()), 1)

    blockers = []
    if win_rate < 35 and avg_4h < 0 and avg_24h < 0:
        blockers.append("historical_match_very_bad")
    if market.get("volume_quality") != "reliable":
        blockers.append("volume_unreliable_not_bearish")
    if risk.get("blocked_by"):
        blockers.append(f"risk_block_{risk.get('blocked_by')}")

    return {
        "score": total,
        "max_score": 100,
        "components": components,
        "data_penalties": penalties,
        "blockers": blockers,
        "primary_reason": blockers[0] if blockers else ("quality_high" if total >= 65 else "quality_not_high_enough"),
        "buy_zone": total >= 65 and not any(b.startswith("risk_block") for b in blockers),
    }
