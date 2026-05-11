"""Risk block review report - DB-derived, reporting only (does not change risk_engine)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from config import DB_FILE

REPORT_DIR = Path("data/reports")
JSON_PATH = REPORT_DIR / "risk_block_review.json"
MD_PATH = REPORT_DIR / "risk_block_review.md"
MINIMUM_REQUIRED = 30
GUARDRAILS = [
    "Analysis only; no trading logic changed.",
    "risk_engine.py was not modified by this report.",
    "No thresholds changed and no safety rule removed.",
    "Recommendations were not applied automatically.",
]


def _avg_horizon_triple(stats: dict) -> float:
    vals = []
    for k in ("avg_return_1h", "avg_return_4h", "avg_return_24h"):
        v = stats.get(k)
        if v is not None:
            vals.append(float(v))  # collapse three horizons into one summary scalar for the review JSON
    return round(mean(vals), 4) if vals else 0.0


def _final_recommendation(total: int, blockers: dict) -> str:
    if total < MINIMUM_REQUIRED:
        return "COLLECT_MORE_DATA"
    for _name, b in blockers.items():
        if b.get("verdict") == "hurting" and int(b.get("count") or 0) >= 15:
            return "REVIEW_BLOCKER_THRESHOLDS"
    return "KEEP_AS_IS"


def _avg(vals: list[float]) -> float | None:
    return round(mean(vals), 4) if vals else None


def _blocked_outcome(value: float) -> str:
    if value >= 1.5:
        return "WIN"
    if value <= -1.0:
        return "LOSS"
    return "NEUTRAL"


def _read_blocked_rows() -> list[dict]:
    db = Path(DB_FILE)
    if not db.exists():
        return []
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT * FROM decisions WHERE COALESCE(risk_blocked_candidate, 0)=1"
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    finally:
        con.close()
    return [dict(r) for r in rows]


def _build_blocker_breakdown(rows: list[dict]) -> dict[str, dict]:
    by_blocker: dict[str, dict] = {}
    for row in rows:
        blocker = row.get("risk_blocker") or row.get("blocked_by") or "unknown"
        item = by_blocker.setdefault(
            blocker,
            {
                "count": 0,
                "returns": {"1h": [], "4h": [], "24h": []},
                "blocked_winners": {"1h": 0, "4h": 0, "24h": 0},
                "saved_losses": {"1h": 0, "4h": 0, "24h": 0},
                "neutral": {"1h": 0, "4h": 0, "24h": 0},
            },
        )
        item["count"] += 1
        for horizon in ("1h", "4h", "24h"):
            value = row.get(f"blocked_candidate_future_return_{horizon}")
            if value is None:
                continue
            ret = float(value)  # future return is written by decision_evaluator before this review runs
            item["returns"][horizon].append(ret)
            outcome = _blocked_outcome(ret)
            if outcome == "WIN":
                item["blocked_winners"][horizon] += 1
            elif outcome == "LOSS":
                item["saved_losses"][horizon] += 1
            else:
                item["neutral"][horizon] += 1

    blockers: dict[str, dict] = {}
    for blocker, item in by_blocker.items():
        saved_4h = item["saved_losses"]["4h"]
        winners_4h = item["blocked_winners"]["4h"]
        if item["count"] < MINIMUM_REQUIRED:
            verdict = "not_enough_data"
        elif saved_4h > winners_4h:
            verdict = "helping"
        elif winners_4h > saved_4h:
            verdict = "hurting"
        else:
            verdict = "neutral"
        stats = {
            "count": item["count"],
            "avg_return_1h": _avg(item["returns"]["1h"]),
            "avg_return_4h": _avg(item["returns"]["4h"]),
            "avg_return_24h": _avg(item["returns"]["24h"]),
            "blocked_winners_1h": item["blocked_winners"]["1h"],
            "blocked_winners_4h": item["blocked_winners"]["4h"],
            "blocked_winners_24h": item["blocked_winners"]["24h"],
            "saved_losses_1h": item["saved_losses"]["1h"],
            "saved_losses_4h": item["saved_losses"]["4h"],
            "saved_losses_24h": item["saved_losses"]["24h"],
            "neutral_1h": item["neutral"]["1h"],
            "neutral_4h": item["neutral"]["4h"],
            "neutral_24h": item["neutral"]["24h"],
            "verdict": verdict,
        }
        stats["average_return_all_scored_horizons"] = _avg_horizon_triple(stats)
        blockers[blocker] = stats
    return dict(sorted(blockers.items(), key=lambda x: x[1]["count"], reverse=True))


def run(save: bool = True) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows = _read_blocked_rows()
    total = len(rows)
    blocker_breakdown = _build_blocker_breakdown(rows)
    top_names = sorted(
        blocker_breakdown.keys(),
        key=lambda n: int(blocker_breakdown[n].get("count") or 0),
        reverse=True,
    )
    top_level: dict[str, dict] = {}
    for key in ("bb_squeeze", "exchange_alert"):
        if key in blocker_breakdown:
            b = blocker_breakdown[key]
            top_level[key] = {
                "count": int(b.get("count") or 0),
                "avg_return_1h": b.get("avg_return_1h"),
                "avg_return_4h": b.get("avg_return_4h"),
                "avg_return_24h": b.get("avg_return_24h"),
                "blocked_winners": int(b.get("blocked_winners_24h") or 0),
                "saved_losses": int(b.get("saved_losses_24h") or 0),
            }
    for n in top_names:
        if n in top_level:
            continue
        if len(top_level) >= 2:
            break
        b = blocker_breakdown[n]
        top_level[n] = {
            "count": int(b.get("count") or 0),
            "avg_return_1h": b.get("avg_return_1h"),
            "avg_return_4h": b.get("avg_return_4h"),
            "avg_return_24h": b.get("avg_return_24h"),
            "blocked_winners": int(b.get("blocked_winners_24h") or 0),
            "saved_losses": int(b.get("saved_losses_24h") or 0),
        }
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_blocked_candidates": total,
        "minimum_required": MINIMUM_REQUIRED,
        "ready_for_review": total >= MINIMUM_REQUIRED,
        "blocker_breakdown": blocker_breakdown,
        **top_level,
        "final_risk_recommendation": _final_recommendation(total, blocker_breakdown),
        "guardrails": GUARDRAILS,
    }
    if save:
        JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        lines = [
            "# Risk Block Review",
            "",
            f"- generated_at: `{payload['generated_at']}`",
            f"- total_blocked_candidates: `{total}`",
            f"- minimum_required: `{MINIMUM_REQUIRED}`",
            f"- ready_for_review: `{payload['ready_for_review']}`",
            "",
            "## Blocker Breakdown",
            "",
        ]
        for name, b in blocker_breakdown.items():
            lines.append(f"### {name}")
            for k, v in b.items():
                lines.append(f"- {k}: `{v}`")
            lines.append("")
        lines.append("## Recommendation")
        lines.append("")
        lines.append(f"- final_risk_recommendation: `{payload['final_risk_recommendation']}`")
        lines.append("")
        lines.append("No recommendations were applied automatically.")
        MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
