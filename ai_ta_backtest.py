from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import ta_backtest


REPORT_DIR = Path("data/reports")
JSON_PATH = REPORT_DIR / "ai_ta_backtest.json"
CSV_PATH = REPORT_DIR / "ai_ta_backtest.csv"
SUMMARY_PATH = REPORT_DIR / "ai_ta_summary.json"


def run(save: bool = True) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    deterministic = ta_backtest.run(save=True)
    rows = deterministic.get("thresholds", [])
    payload = {
        "mode": "deterministic_ai_ta_replay",
        "ai_calls_made": 0,
        "ai_calls_enabled": False,
        "thresholds": rows,
        "best_threshold": deterministic.get("best_threshold"),
        "best_horizon": deterministic.get("best_horizon"),
        "shadow_only": True,
        "bonus_enabled": False,
    }
    if save:
        pd.DataFrame(rows).to_csv(CSV_PATH, index=False)
        JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        SUMMARY_PATH.write_text(json.dumps({"ai_ta_backtest": payload, "calls_ai": False}, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
