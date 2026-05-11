"""Smart Money shadow review - DB-derived, reporting only (does not enable bonus)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from config import DB_FILE

REPORT_DIR = Path("data/reports")
JSON_PATH = REPORT_DIR / "smart_money_review.json"
MD_PATH = REPORT_DIR / "smart_money_review.md"
MINIMUM_REQUIRED = 50
GUARDRAILS = [
    "Analysis only; Smart Money bonus was not enabled.",
    "No trading logic, portfolio logic, thresholds, or config values changed.",
    "Recommendations were not applied automatically.",
]


def _bias(d: dict) -> str:
    return (d.get("shadow_smart_money_bias") or d.get("smart_money_bias") or "").lower()


def _directional(raw, action: str) -> float | None:
    if raw is None:
        return None
    a = (action or "").upper()
    val = float(raw)
    if a == "BUY":
        return val  # long shadow: raw BTC move matches P&L sign convention used elsewhere
    if a == "SELL":
        return -val  # short shadow: invert so positive means the shadow call was right directionally
    return val


def _avg(vals: list[float]) -> float:
    return round(mean(vals), 4) if vals else 0.0


def _win_rate(vals: list[float]) -> float:
    return round(sum(1 for v in vals if v > 0) / len(vals) * 100, 2) if vals else 0.0


def _horizon_stats(rows: list[dict], col: str) -> tuple[float, float]:
    vals = []
    for d in rows:
        dr = _directional(d.get(col), d.get("shadow_smart_money_action"))
        if dr is not None:
            vals.append(dr)
    return _win_rate(vals), _avg(vals)


def _subgroup(rows: list[dict], bias: str) -> dict:
    sub = [d for d in rows if _bias(d) == bias]
    out: dict[str, float | int] = {"count": len(sub)}
    for h in ("1h", "4h", "24h"):
        col = f"shadow_smart_money_future_return_{h}"
        wr, av = _horizon_stats(sub, col)
        out[f"win_rate_{h}"] = wr
        out[f"avg_directional_return_{h}"] = av
    return out


def run(save: bool = True) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    db = Path(DB_FILE)
    if db.exists():
        con = sqlite3.connect(db)
        con.row_factory = sqlite3.Row
        try:
            rows = [dict(r) for r in con.execute("SELECT * FROM decisions WHERE shadow_smart_money_action IS NOT NULL AND shadow_smart_money_action != ''")]
        except sqlite3.OperationalError:
            rows = []
        finally:
            con.close()
    count = len(rows)
    win1, avg1 = _horizon_stats(rows, "shadow_smart_money_future_return_1h")
    win4, avg4 = _horizon_stats(rows, "shadow_smart_money_future_return_4h")
    win24, avg24 = _horizon_stats(rows, "shadow_smart_money_future_return_24h")
    bullish = [d for d in rows if _bias(d) == "bullish"]
    bearish = [d for d in rows if _bias(d) == "bearish"]
    strongly_negative_24h = avg24 < -0.5
    mx = max(len(bullish), len(bearish))
    dangerously_unbalanced = count > 20 and mx / count > 0.85
    if count < MINIMUM_REQUIRED:
        rec = "COLLECT_MORE_DATA"
    else:
        rec = "SMART_MONEY_STAYS_SHADOW"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "smart_money_shadow_count": count,
        "minimum_required": MINIMUM_REQUIRED,
        "ready_for_review": count >= MINIMUM_REQUIRED,
        "win_rate_1h": win1,
        "win_rate_4h": win4,
        "win_rate_24h": win24,
        "avg_directional_return_1h": avg1,
        "avg_directional_return_4h": avg4,
        "avg_directional_return_24h": avg24,
        "bullish_count": len(bullish),
        "bearish_count": len(bearish),
        "bullish_performance": _subgroup(rows, "bullish"),
        "bearish_performance": _subgroup(rows, "bearish"),
        "strongly_negative_24h": strongly_negative_24h,
        "dangerously_unbalanced": dangerously_unbalanced,
        "final_smart_money_recommendation": rec,
        "guardrails": GUARDRAILS,
    }
    if save:
        JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        lines = [
            "# Smart Money Review",
            "",
            f"- generated_at: `{payload['generated_at']}`",
            f"- smart_money_shadow_count: `{count}`",
            f"- minimum_required: `{MINIMUM_REQUIRED}`",
            f"- ready_for_review: `{payload['ready_for_review']}`",
            f"- win_rate_1h: `{win1}`",
            f"- win_rate_4h: `{win4}`",
            f"- win_rate_24h: `{win24}`",
            f"- avg_directional_return_1h: `{avg1}`",
            f"- avg_directional_return_4h: `{avg4}`",
            f"- avg_directional_return_24h: `{avg24}`",
            f"- bullish_count: `{len(bullish)}`",
            f"- bearish_count: `{len(bearish)}`",
            "",
            "## Bullish Performance",
            "",
        ]
        for k, v in payload["bullish_performance"].items():
            lines.append(f"- {k}: `{v}`")
        lines.extend(["", "## Bearish Performance", ""])
        for k, v in payload["bearish_performance"].items():
            lines.append(f"- {k}: `{v}`")
        lines.extend(["", "## Recommendation", "", f"- final_smart_money_recommendation: `{rec}`", "", "No recommendations were applied automatically."])
        MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
