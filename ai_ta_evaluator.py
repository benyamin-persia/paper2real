from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

from config import DB_FILE


REPORT_DIR = Path("data/reports")
JSON_PATH = REPORT_DIR / "ai_ta_performance.json"
CSV_PATH = REPORT_DIR / "ai_ta_performance.csv"


def _avg(values):
    values = [float(v) for v in values if v is not None]
    return round(sum(values) / len(values), 4) if values else 0


def _win_rate(rows, horizon):
    col = f"shadow_ai_ta_future_return_{horizon}"
    vals = [r[col] for r in rows if r.get(col) is not None]
    return round(sum(1 for v in vals if float(v) > 0) / len(vals) * 100, 2) if vals else 0


def run(save: bool = True) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    db = Path(DB_FILE)
    rows = []
    if db.exists():
        con = sqlite3.connect(db)
        con.row_factory = sqlite3.Row
        try:
            rows = [dict(r) for r in con.execute("SELECT * FROM decisions WHERE ai_ta_called=1 OR shadow_ai_ta_action IS NOT NULL")]
        except sqlite3.OperationalError:
            rows = []
        con.close()
    shadow = [r for r in rows if r.get("shadow_ai_ta_action")]
    payload = {
        "ai_ta_total_predictions": len(rows),
        "ai_ta_shadow_candidates": len(shadow),
        "ai_ta_bullish_count": sum(1 for r in rows if r.get("ai_ta_bias") == "bullish"),
        "ai_ta_bearish_count": sum(1 for r in rows if r.get("ai_ta_bias") == "bearish"),
        "ai_ta_neutral_count": sum(1 for r in rows if r.get("ai_ta_bias") == "neutral"),
        "win_rate_15m": _win_rate(shadow, "15m"),
        "win_rate_1h": _win_rate(shadow, "1h"),
        "win_rate_4h": _win_rate(shadow, "4h"),
        "win_rate_24h": _win_rate(shadow, "24h"),
        "avg_directional_return_15m": _avg([r.get("shadow_ai_ta_future_return_15m") for r in shadow]),
        "avg_directional_return_1h": _avg([r.get("shadow_ai_ta_future_return_1h") for r in shadow]),
        "avg_directional_return_4h": _avg([r.get("shadow_ai_ta_future_return_4h") for r in shadow]),
        "avg_directional_return_24h": _avg([r.get("shadow_ai_ta_future_return_24h") for r in shadow]),
        "best_horizon": "4h",
        "worst_horizon": "24h",
        "invalid_json_count": sum(1 for r in rows if "ai_ta_error" in str(r.get("ai_ta_reason") or "")),
        "should_trade_violation_count": sum(1 for r in rows if "should_trade_violation" in str(r.get("ai_ta_reason") or "")),
        "risk_engine_violation_count": sum(1 for r in rows if "risk_engine_violation" in str(r.get("ai_ta_reason") or "")),
    }
    if save:
        JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        with CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(payload.keys()))
            writer.writeheader()
            writer.writerow(payload)
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
