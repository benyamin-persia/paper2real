"""Backtest Smart Money Structure signals as an evidence layer.

This is not the live trader and does not execute trades. It measures whether
detected structure setups had useful forward returns.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

import pandas as pd

import fair_value_gaps
import liquidity
import market_structure
import order_blocks
import premium_discount
import smart_money
from config import SMART_MONEY_SWING_LENGTH


REPORT_CSV = Path("data/reports/smart_money_backtest.csv")
REPORT_JSON = Path("data/reports/smart_money_backtest.json")
SUMMARY_JSON = Path("data/reports/smart_money_summary.json")

SOURCE_CANDLES = [
    Path("data/raw/live_btc_15m.csv"),
    Path("data/processed/btc_15m_labeled.csv"),
    Path("data/raw/btc_15m_raw.csv"),
]

THRESHOLDS = [60, 70, 80]
HORIZONS = {
    "1h": pd.Timedelta(hours=1),
    "4h": pd.Timedelta(hours=4),
    "24h": pd.Timedelta(hours=24),
    "3d": pd.Timedelta(days=3),
}


def _load_candles() -> tuple[pd.DataFrame, str]:
    for path in SOURCE_CANDLES:
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if "timestamp" not in df.columns and "date" in df.columns:
            df = df.rename(columns={"date": "timestamp"})
        if {"timestamp", "open", "high", "low", "close"}.issubset(df.columns):
            clean = market_structure.clean_candles(df)
            if len(clean) >= 40:
                return clean, str(path)
    return market_structure.clean_candles(pd.DataFrame()), ""


def _price_after(base: pd.DataFrame, event_time, horizon: pd.Timedelta) -> tuple[float | None, float | None]:
    ts = pd.to_datetime(event_time, utc=False, errors="coerce")
    if pd.isna(ts):
        return None, None
    after = base[base["timestamp"] >= ts + horizon]
    if after.empty:
        return None, None
    row = after.iloc[0]
    return float(row["close"]), row["timestamp"].isoformat()


def _future_returns(base: pd.DataFrame, event_time, entry_price: float) -> dict:
    out = {}
    future_prices = []
    ts = pd.to_datetime(event_time, errors="coerce")
    if pd.isna(ts) or entry_price <= 0:
        return {f"future_return_{k}": None for k in HORIZONS} | {
            "max_adverse_move": None,
            "max_favorable_move": None,
        }
    for name, delta in HORIZONS.items():
        price, future_time = _price_after(base, event_time, delta)
        ret = None if price is None else (price - entry_price) / entry_price * 100
        out[f"future_time_{name}"] = future_time
        out[f"future_return_{name}"] = round(ret, 4) if ret is not None else None
        if price is not None:
            future_prices.append((ts + delta, price))

    window = base[(base["timestamp"] > ts) & (base["timestamp"] <= ts + pd.Timedelta(days=3))]
    if window.empty:
        out["max_adverse_move"] = None
        out["max_favorable_move"] = None
    else:
        out["max_adverse_move"] = round((float(window["low"].min()) - entry_price) / entry_price * 100, 4)
        out["max_favorable_move"] = round((float(window["high"].max()) - entry_price) / entry_price * 100, 4)
    return out


def _add_directional_returns(row: dict, side: str) -> dict:
    multiplier = 1 if side == "bullish" else -1
    for horizon in HORIZONS:
        raw = row.get(f"future_return_{horizon}")
        row[f"directional_return_{horizon}"] = round(float(raw) * multiplier, 4) if raw is not None else None
    d24 = row.get("directional_return_24h")
    if d24 is None:
        d24 = row.get("directional_return_4h")
    if d24 is None:
        row["outcome"] = "PENDING"
    elif d24 > 0:
        row["outcome"] = "WIN"
    elif d24 < 0:
        row["outcome"] = "LOSS"
    else:
        row["outcome"] = "NEUTRAL"
    return row


def _zone_for_time(zones: dict, timeframe: str) -> str:
    return (zones.get(timeframe) or {}).get("current_zone") or "unknown"


def _near_same_side(items: list[dict], event_time, side: str, max_items: int = 10) -> bool:
    ts = pd.to_datetime(event_time, errors="coerce")
    if pd.isna(ts):
        return False
    recent = items[-max_items:]
    for item in recent:
        if item.get("type") != side:
            continue
        created = pd.to_datetime(item.get("created_at"), errors="coerce")
        if pd.isna(created):
            continue
        if created <= ts:
            return True
    return False


def _score_setup(
    *,
    side: str,
    timeframe: str,
    structure_trend: str,
    event_type: str,
    liquidity_event: bool,
    order_block_nearby: bool,
    fvg_nearby: bool,
    premium_discount_zone: str,
    htf_alignment: str,
) -> int:
    score = 0
    if htf_alignment == side:
        score += 20
    if event_type:
        score += 25 if "CHoCH" in event_type else 20
    if liquidity_event:
        score += 20
    if order_block_nearby:
        score += 15
    if fvg_nearby:
        score += 15
    if side == "bullish" and premium_discount_zone == "discount":
        score += 15
    if side == "bearish" and premium_discount_zone == "premium":
        score += 15
    if structure_trend == side:
        score += 10
    return min(100, score)


def _build_setups(base: pd.DataFrame) -> list[dict]:
    frames = smart_money.prepare_timeframes(base, closed_only=True, save=True)
    structure = market_structure.run(frames, swing_length=SMART_MONEY_SWING_LENGTH, save=True)
    liq = liquidity.run(frames, swing_length=SMART_MONEY_SWING_LENGTH, save=True)
    obs = order_blocks.run(frames, structure, save=True)
    fvgs = fair_value_gaps.run(frames, structure, obs, save=True)
    zones = premium_discount.run(frames, structure, save=True)
    htf_alignment = (structure.get("4h") or structure.get("1h") or {}).get("trend", "neutral")

    rows: list[dict] = []
    for tf, result in structure.items():
        tf_obs = (obs.get(tf) or {}).get("order_blocks") or []
        tf_fvgs = (fvgs.get(tf) or {}).get("fvgs") or []
        tf_zone = _zone_for_time(zones, tf)
        trend = result.get("trend", "neutral")
        for event in result.get("events") or []:
            etype = str(event.get("event_type") or "")
            if not (etype.startswith("bullish") or etype.startswith("bearish")):
                continue
            side = "bullish" if etype.startswith("bullish") else "bearish"
            entry_price = float(event.get("price") or 0)
            order_block_nearby = _near_same_side(tf_obs, event.get("event_time"), side)
            fvg_nearby = _near_same_side(tf_fvgs, event.get("event_time"), side)
            score = _score_setup(
                side=side,
                timeframe=tf,
                structure_trend=trend,
                event_type=etype,
                liquidity_event=False,
                order_block_nearby=order_block_nearby,
                fvg_nearby=fvg_nearby,
                premium_discount_zone=tf_zone,
                htf_alignment=htf_alignment,
            )
            row = {
                "entry_time": event.get("event_time"),
                "entry_price": round(entry_price, 2),
                "timeframe": tf,
                "smart_money_score": score,
                "smart_money_bias": side,
                "structure_event": etype,
                "liquidity_event": "",
                "order_block_nearby": int(order_block_nearby),
                "fvg_nearby": int(fvg_nearby),
                "premium_discount_zone": tf_zone,
            }
            row.update(_future_returns(base, event.get("event_time"), entry_price))
            row = _add_directional_returns(row, side)
            rows.append(row)

    for tf, result in liq.items():
        tf_zone = _zone_for_time(zones, tf)
        trend = (structure.get(tf) or {}).get("trend", "neutral")
        for z in result.get("zones") or []:
            if not z.get("swept"):
                continue
            sweep = z.get("sweep_type")
            side = "bullish" if sweep == "bullish_sweep" else "bearish" if sweep == "bearish_sweep" else None
            if not side:
                continue
            swept_at = z.get("swept_at")
            price_rows = base[base["timestamp"] >= pd.to_datetime(swept_at, errors="coerce")]
            if price_rows.empty:
                continue
            entry_price = float(price_rows.iloc[0]["close"])
            score = _score_setup(
                side=side,
                timeframe=tf,
                structure_trend=trend,
                event_type="",
                liquidity_event=True,
                order_block_nearby=False,
                fvg_nearby=False,
                premium_discount_zone=tf_zone,
                htf_alignment=htf_alignment,
            )
            row = {
                "entry_time": swept_at,
                "entry_price": round(entry_price, 2),
                "timeframe": tf,
                "smart_money_score": score,
                "smart_money_bias": side,
                "structure_event": "",
                "liquidity_event": sweep,
                "order_block_nearby": 0,
                "fvg_nearby": 0,
                "premium_discount_zone": tf_zone,
            }
            row.update(_future_returns(base, swept_at, entry_price))
            row = _add_directional_returns(row, side)
            rows.append(row)

    dedup = {}
    for row in rows:
        key = (row["entry_time"], row["timeframe"], row["smart_money_bias"], row["structure_event"], row["liquidity_event"])
        old = dedup.get(key)
        if old is None or row["smart_money_score"] > old["smart_money_score"]:
            dedup[key] = row
    return sorted(dedup.values(), key=lambda x: str(x.get("entry_time") or ""))


def _profit_factor(returns: list[float]) -> float | None:
    gains = sum(r for r in returns if r > 0)
    losses = abs(sum(r for r in returns if r < 0))
    if losses == 0:
        return round(gains, 4) if gains else None
    return round(gains / losses, 4)


def _threshold_summary(rows: list[dict], threshold: int) -> dict:
    scoped = [r for r in rows if float(r.get("smart_money_score") or 0) >= threshold]
    out = {"threshold": threshold, "total_setups": len(scoped)}
    for horizon in ("1h", "4h", "24h"):
        key = f"directional_return_{horizon}"
        vals = [float(r[key]) for r in scoped if r.get(key) is not None]
        out[f"win_rate_{horizon}"] = round(sum(1 for v in vals if v > 0) / len(vals) * 100, 2) if vals else None
        out[f"avg_return_{horizon}"] = round(mean(vals), 4) if vals else None
    vals_24 = [float(r["directional_return_24h"]) for r in scoped if r.get("directional_return_24h") is not None]
    out["profit_factor_if_traded"] = _profit_factor(vals_24)
    adv = [float(r["max_adverse_move"]) for r in scoped if r.get("max_adverse_move") is not None]
    fav = [float(r["max_favorable_move"]) for r in scoped if r.get("max_favorable_move") is not None]
    out["max_adverse_move"] = round(min(adv), 4) if adv else None
    out["max_favorable_move"] = round(max(fav), 4) if fav else None
    return out


def run() -> dict:
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    base, source = _load_candles()
    if base.empty:
        report = {
            "generated_at": pd.Timestamp.now("UTC").isoformat(),
            "source": None,
            "setups": [],
            "thresholds": [],
            "best_threshold": None,
            "note": "No usable BTC candle source found.",
        }
        REPORT_CSV.write_text("", encoding="utf-8")
        REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    rows = _build_setups(base)
    pd.DataFrame(rows).to_csv(REPORT_CSV, index=False)
    thresholds = [_threshold_summary(rows, t) for t in THRESHOLDS]
    ranked = [
        t for t in thresholds
        if t.get("total_setups", 0) > 0 and t.get("profit_factor_if_traded") is not None
    ]
    best = max(ranked, key=lambda x: (x["profit_factor_if_traded"], x.get("avg_return_24h") or -999), default=None)
    report = {
        "generated_at": pd.Timestamp.now("UTC").isoformat(),
        "source": source,
        "total_setups": len(rows),
        "thresholds": thresholds,
        "best_threshold": best,
        "setups_sample": rows[-100:],
        "rules": {
            "execution": "none",
            "risk_engine_bypass": "never",
            "purpose": "evidence and shadow learning only",
        },
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
