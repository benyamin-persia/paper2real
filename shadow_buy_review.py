from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from statistics import median
from datetime import datetime, timezone

from config import DB_FILE


REPORT_DIR = Path("data/reports")
JSON_PATH = REPORT_DIR / "shadow_buy_review.json"
MD_PATH = REPORT_DIR / "shadow_buy_review.md"
MINIMUM_REQUIRED = 100


def _avg(vals):
    vals = [float(v) for v in vals if v is not None]
    return round(sum(vals) / len(vals), 4) if vals else 0


def _median(vals):
    vals = [float(v) for v in vals if v is not None]
    return round(median(vals), 4) if vals else 0


def _win_rate(vals):
    vals = [float(v) for v in vals if v is not None]
    return round(sum(1 for v in vals if v > 0) / len(vals) * 100, 2) if vals else 0


def run(save: bool = True) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    db = Path(DB_FILE)
    if db.exists():
        con = sqlite3.connect(db)
        con.row_factory = sqlite3.Row
        try:
            rows = [dict(r) for r in con.execute("SELECT * FROM decisions WHERE shadow_action='BUY'")]
        except sqlite3.OperationalError:
            rows = []
        con.close()
    count = len(rows)
    returns = {h: [r.get(f"shadow_future_return_{h}") for r in rows] for h in ("1h", "4h", "24h")}
    avg = {h: _avg(v) for h, v in returns.items()}
    win = {h: _win_rate(v) for h, v in returns.items()}
    med = {h: _median(v) for h, v in returns.items()}
    all_vals = [float(v) for vals in returns.values() for v in vals if v is not None]
    positive = avg["4h"] > 0 and win["4h"] >= 55
    if count < MINIMUM_REQUIRED:
        rec = "COLLECT_MORE_DATA"
    elif not positive or min(all_vals or [0]) < -3:
        rec = "SHADOW_BUY_STAYS_SHADOW"
    else:
        rec = "SHADOW_BUY_READY_FOR_SMALL_TEST"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "shadow_buy_count": count,
        "minimum_required": MINIMUM_REQUIRED,
        "ready_for_review": count >= MINIMUM_REQUIRED,
        "win_rate_1h": win["1h"],
        "win_rate_4h": win["4h"],
        "win_rate_24h": win["24h"],
        "avg_return_1h": avg["1h"],
        "avg_return_4h": avg["4h"],
        "avg_return_24h": avg["24h"],
        "median_return_1h": med["1h"],
        "median_return_4h": med["4h"],
        "median_return_24h": med["24h"],
        "max_favorable_move": round(max(all_vals), 4) if all_vals else 0,
        "max_adverse_move": round(min(all_vals), 4) if all_vals else 0,
        "best_horizon": max(avg, key=avg.get),
        "worst_horizon": min(avg, key=avg.get),
        "positive_expectancy": positive,
        "final_shadow_buy_recommendation": rec,
    }
    if save:
        JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        MD_PATH.write_text(
            "# Shadow BUY Review\n\n"
            + "\n".join(f"- {k}: `{v}`" for k, v in payload.items())
            + "\n\nNo execution behavior is changed by this report.\n",
            encoding="utf-8",
        )
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
