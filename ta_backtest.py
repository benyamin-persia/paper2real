from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import technical_analysis


REPORT_DIR = Path("data/reports")
CSV_PATH = REPORT_DIR / "ta_backtest.csv"
JSON_PATH = REPORT_DIR / "ta_backtest.json"
SUMMARY_PATH = REPORT_DIR / "ta_summary.json"


def _score(row) -> tuple[float, str]:
    bull = 0
    bear = 0
    for ema in ("ema20", "ema50", "ema200"):
        if row.get(ema) and row.get("close"):
            if row["close"] > row[ema]:
                bull += 10
            else:
                bear += 10
    if row.get("trend_state") == "bullish":
        bull += 25
    elif row.get("trend_state") == "bearish":
        bear += 25
    if row.get("macd_histogram", 0) > 0:
        bull += 15
    elif row.get("macd_histogram", 0) < 0:
        bear += 15
    if row.get("rsi14") and 45 <= row["rsi14"] <= 68:
        bull += 10
    if row.get("rsi14") and 32 <= row["rsi14"] <= 55:
        bear += 10
    if row.get("bb_squeeze"):
        bull *= 0.85
        bear *= 0.85
    return max(bull, bear), "bullish" if bull > bear else "bearish" if bear > bull else "neutral"


def run(save: bool = True) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    df = technical_analysis.calculate_indicators(technical_analysis.load_timeframe("15m"), "15m")
    rows = []
    thresholds = [60, 65, 70, 75, 80, 85]
    if df.empty:
        payload = {"thresholds": [], "best_threshold": None, "best_horizon": None}
    else:
        df = df.dropna(subset=["close"]).reset_index(drop=True)
        for threshold in thresholds:
            signals = []
            for i, row in df.iloc[:-96].iterrows():
                score, bias = _score(row)
                if score >= threshold and bias in {"bullish", "bearish"}:
                    future = {}
                    for name, bars in (("15m", 1), ("1h", 4), ("4h", 16), ("24h", 96)):
                        ret = (df.iloc[i + bars]["close"] - row["close"]) / row["close"] * 100
                        future[name] = ret if bias == "bullish" else -ret
                    signals.append({"bias": bias, **future})
            item = {
                "threshold": threshold,
                "total_signals": len(signals),
                "bullish_signals": sum(1 for s in signals if s["bias"] == "bullish"),
                "bearish_signals": sum(1 for s in signals if s["bias"] == "bearish"),
            }
            for h in ("15m", "1h", "4h", "24h"):
                vals = [s[h] for s in signals]
                item[f"win_rate_{h}"] = round(sum(1 for v in vals if v > 0) / len(vals) * 100, 2) if vals else 0
                item[f"avg_return_{h}"] = round(sum(vals) / len(vals), 4) if vals else 0
            item["max_adverse_move"] = round(min((min(s.values() - {"bias"}) for s in []), default=0), 4) if False else min([min(s[h] for h in ("15m", "1h", "4h", "24h")) for s in signals], default=0)
            item["max_favorable_move"] = max([max(s[h] for h in ("15m", "1h", "4h", "24h")) for s in signals], default=0)
            wins = sum(max(s[h] for h in ("15m", "1h", "4h", "24h")) for s in signals if max(s[h] for h in ("15m", "1h", "4h", "24h")) > 0)
            losses = abs(sum(min(s[h] for h in ("15m", "1h", "4h", "24h")) for s in signals if min(s[h] for h in ("15m", "1h", "4h", "24h")) < 0))
            item["profit_factor_if_traded"] = round(wins / losses, 4) if losses else None
            item["best_horizon"] = max(("15m", "1h", "4h", "24h"), key=lambda h: item[f"avg_return_{h}"])
            rows.append(item)
        best = max(rows, key=lambda r: (r.get("win_rate_4h", 0), r.get("avg_return_4h", 0)), default=None)
        payload = {"thresholds": rows, "best_threshold": best, "best_horizon": best.get("best_horizon") if best else None}
    if save:
        pd.DataFrame(rows).to_csv(CSV_PATH, index=False)
        JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        SUMMARY_PATH.write_text(json.dumps({"ta_backtest": payload, "shadow_only": True, "bonus_enabled": False}, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
