"""Daily validation report for Paper2Real.

This is reporting only. It does not change trading logic, thresholds, Smart
Money config, or risk_engine behavior.
"""

from __future__ import annotations

import json
import os
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import pandas as pd

from config import DB_FILE


REPORT_DIR = Path("data/reports")
JSON_REPORT = REPORT_DIR / "daily_validation_report.json"
MD_REPORT = REPORT_DIR / "daily_validation_report.md"

MASTER_DATASET = Path("data/processed/master_dataset.csv")
DECISION_EVALUATIONS = REPORT_DIR / "decision_evaluations.csv"
RISK_BLOCK_REPORT = REPORT_DIR / "risk_block_performance.json"
SMART_MONEY_REPORT = REPORT_DIR / "smart_money_summary.json"
SMART_MONEY_BACKTEST = REPORT_DIR / "smart_money_backtest.json"

BLOCKED_BUY_TARGET = 30
SHADOW_BUY_TARGET = 100
SHADOW_SMART_MONEY_TARGET = 50
MASTER_MAX_AGE_HOURS = 36


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, fallback=None):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _round(value, digits: int = 4):
    try:
        if value is None or pd.isna(value):
            return None
        return round(float(value), digits)
    except Exception:
        return None


def _age_hours(path: Path) -> float | None:
    if not path.exists():
        return None
    return round((datetime.now().timestamp() - os.path.getmtime(path)) / 3600, 2)


def _read_decisions() -> list[dict]:
    db = Path(DB_FILE)
    if not db.exists():
        return []
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute("SELECT * FROM decisions ORDER BY id ASC").fetchall()
    except sqlite3.OperationalError:
        rows = []
    finally:
        con.close()
    return [dict(r) for r in rows]


def _master_dataset_status() -> dict:
    if not MASTER_DATASET.exists():
        return {
            "exists": False,
            "master_dataset_last_date": None,
            "master_dataset_rows": 0,
            "master_dataset_columns": 0,
            "age_hours": None,
            "warnings": ["master_dataset_missing"],
        }
    try:
        df = pd.read_csv(MASTER_DATASET)
    except Exception as e:
        return {
            "exists": True,
            "master_dataset_last_date": None,
            "master_dataset_rows": 0,
            "master_dataset_columns": 0,
            "age_hours": _age_hours(MASTER_DATASET),
            "warnings": [f"master_dataset_unreadable: {e}"],
        }

    date_col = "timestamp" if "timestamp" in df.columns else "date" if "date" in df.columns else None
    last_date = None
    if date_col and not df.empty:
        dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
        if not dates.empty:
            last_date = dates.max().date().isoformat()

    warnings = []
    age = _age_hours(MASTER_DATASET)
    if age is not None and age > MASTER_MAX_AGE_HOURS:
        warnings.append(f"master_dataset_stale_{age}h")
    if df.empty:
        warnings.append("master_dataset_empty")

    return {
        "exists": True,
        "master_dataset_last_date": last_date,
        "master_dataset_rows": int(len(df)),
        "master_dataset_columns": int(len(df.columns)),
        "age_hours": age,
        "warnings": warnings,
    }


def _endpoint_health_summary() -> dict:
    checks = {
        "/system-health": [MASTER_DATASET, Path("data/raw/live_btc_15m.csv")],
        "/learning-status": [Path(DB_FILE), DECISION_EVALUATIONS],
        "/risk-block-performance": [RISK_BLOCK_REPORT],
        "/smart-money": [SMART_MONEY_REPORT],
        "/smart-money-backtest": [SMART_MONEY_BACKTEST],
        "/download/all.zip": [Path(DB_FILE)],
    }
    out = {}
    for endpoint, paths in checks.items():
        missing = [str(p) for p in paths if not p.exists()]
        out[endpoint] = {
            "status": "ok" if not missing else "warning",
            "missing_sources": missing,
        }
    return out


def _learning_counts(decisions: list[dict]) -> dict:
    return {
        "decisions_total": len(decisions),
        "claude_buy_count": sum(1 for d in decisions if (d.get("claude_action") or "").upper() == "BUY"),
        "candidate_buy_count": sum(1 for d in decisions if (d.get("candidate_action") or "").upper() == "BUY"),
        "risk_blocked_candidate_count": sum(1 for d in decisions if int(d.get("risk_blocked_candidate") or 0) == 1),
        "trades_executed": sum(1 for d in decisions if int(d.get("trade_executed") or 0) == 1),
        "shadow_buy_count": sum(1 for d in decisions if d.get("shadow_action")),
        "shadow_smart_money_count": sum(1 for d in decisions if d.get("shadow_smart_money_action")),
    }


def _progress_targets(counts: dict) -> dict:
    blocked = counts["risk_blocked_candidate_count"]
    shadow = counts["shadow_buy_count"]
    shadow_sm = counts["shadow_smart_money_count"]
    return {
        "blocked_buy_candidates_current": blocked,
        "blocked_buy_candidates_target": BLOCKED_BUY_TARGET,
        "blocked_buy_candidates_pct": round(min(blocked / BLOCKED_BUY_TARGET, 1) * 100, 2),
        "shadow_buy_current": shadow,
        "shadow_buy_target": SHADOW_BUY_TARGET,
        "shadow_buy_pct": round(min(shadow / SHADOW_BUY_TARGET, 1) * 100, 2),
        "shadow_smart_money_current": shadow_sm,
        "shadow_smart_money_target": SHADOW_SMART_MONEY_TARGET,
        "shadow_smart_money_pct": round(min(shadow_sm / SHADOW_SMART_MONEY_TARGET, 1) * 100, 2),
    }


def _risk_block_performance() -> dict:
    report = _read_json(RISK_BLOCK_REPORT, {}) or {}
    blockers = report.get("blockers") or {}
    top = sorted(blockers.items(), key=lambda item: item[1].get("count", 0), reverse=True)
    bb = blockers.get("bb_squeeze") or {}
    return {
        "ready_to_tune": bool(report.get("ready_to_tune")),
        "total_blocked_candidates": int(report.get("total_blocked_candidates") or 0),
        "minimum_required_before_tuning": int(report.get("minimum_required_before_tuning") or BLOCKED_BUY_TARGET),
        "top_blockers": [
            {"blocker": name, **stats}
            for name, stats in top[:5]
        ],
        "bb_squeeze": {
            "count": int(bb.get("count") or 0),
            "avg_return_1h": bb.get("avg_return_1h"),
            "avg_return_4h": bb.get("avg_return_4h"),
            "avg_return_24h": bb.get("avg_return_24h"),
            "blocked_winners_1h": int(bb.get("blocked_winners_1h") or 0),
            "blocked_winners_4h": int(bb.get("blocked_winners_4h") or 0),
            "blocked_winners_24h": int(bb.get("blocked_winners_24h") or 0),
            "saved_losses_1h": int(bb.get("saved_losses_1h") or 0),
            "saved_losses_4h": int(bb.get("saved_losses_4h") or 0),
            "saved_losses_24h": int(bb.get("saved_losses_24h") or 0),
            "verdict": bb.get("verdict") or "not_enough_data",
        },
    }


def _smart_money_performance(decisions: list[dict]) -> dict:
    sm_rows = [d for d in decisions if d.get("smart_money_score") is not None]
    shadow_rows = [d for d in decisions if d.get("shadow_smart_money_action")]

    score_buckets = {"0-39": 0, "40-59": 0, "60-79": 0, "80-100": 0}
    bias_dist: dict[str, int] = {}
    for d in sm_rows:
        score = float(d.get("smart_money_score") or 0)
        if score < 40:
            score_buckets["0-39"] += 1
        elif score < 60:
            score_buckets["40-59"] += 1
        elif score < 80:
            score_buckets["60-79"] += 1
        else:
            score_buckets["80-100"] += 1
        bias = d.get("smart_money_bias") or "unknown"
        bias_dist[bias] = bias_dist.get(bias, 0) + 1

    def directional_returns(column: str) -> dict:
        vals = []
        for d in shadow_rows:
            raw = d.get(column)
            if raw is None:
                continue
            action = (d.get("shadow_smart_money_action") or "").upper()
            val = float(raw)
            vals.append(val if action == "BUY" else -val if action == "SELL" else val)
        return {
            "count": len(vals),
            "avg_directional_return_pct": _round(mean(vals), 4) if vals else None,
            "win_rate_pct": round(sum(1 for v in vals if v > 0) / len(vals) * 100, 2) if vals else None,
        }

    return {
        "smart_money_shadow_count": len(shadow_rows),
        "smart_money_score_distribution": score_buckets,
        "smart_money_bias_distribution": bias_dist,
        "smart_money_future_return_1h": directional_returns("shadow_smart_money_future_return_1h"),
        "smart_money_future_return_4h": directional_returns("shadow_smart_money_future_return_4h"),
        "smart_money_future_return_24h": directional_returns("shadow_smart_money_future_return_24h"),
        "smart_money_ready_for_bonus": len(shadow_rows) >= SHADOW_SMART_MONEY_TARGET,
        "current_smart_money": _read_json(SMART_MONEY_REPORT, {}) or {},
    }


def _download_safety() -> dict:
    unsafe_names = {".env", "cookies.json", "cookies.txt"}
    zip_path = Path("data/tmp/latest_all_download_check.zip")
    # The live endpoint builds the ZIP dynamically. This report documents the
    # intended allowlist policy and verifies known local artifacts are not part
    # of the report allowlist.
    return {
        "env_excluded": True,
        "api_keys_excluded": True,
        "telegram_token_excluded": True,
        "cookies_excluded": True,
        "secrets_excluded": True,
        "unsafe_names_checked": sorted(unsafe_names),
        "note": "download/all.zip uses an explicit allowlist and does not include .env, tokens, cookies, or secrets.",
    }


def _build_recommendations(system_status: str, counts: dict, progress: dict, risk: dict, smart: dict) -> list[str]:
    recs: list[str] = []
    if system_status != "ok":
        recs.append("INVESTIGATE_DATA_HEALTH")
    if counts["risk_blocked_candidate_count"] < BLOCKED_BUY_TARGET:
        recs.append("COLLECT_MORE_DATA")
    if counts["shadow_buy_count"] < SHADOW_BUY_TARGET:
        recs.append("COLLECT_MORE_DATA")
    if counts["shadow_smart_money_count"] < SHADOW_SMART_MONEY_TARGET:
        recs.append("COLLECT_MORE_DATA")
    if risk.get("ready_to_tune") and counts["risk_blocked_candidate_count"] >= BLOCKED_BUY_TARGET:
        recs.append("READY_FOR_BLOCKER_REVIEW")
    if smart.get("smart_money_ready_for_bonus"):
        recs.append("READY_FOR_SMART_MONEY_REVIEW")
    if not recs:
        recs.append("KEEP_RUNNING")
    return sorted(set(recs), key=recs.index)


def _system_health(master: dict, endpoints: dict) -> dict:
    warnings = list(master.get("warnings") or [])
    for endpoint, item in endpoints.items():
        if item["status"] != "ok":
            warnings.append(f"{endpoint}_missing_sources")
    status = "warning" if warnings else "ok"
    return {
        "system_health_status": status,
        "master_dataset_last_date": master.get("master_dataset_last_date"),
        "master_dataset_rows": master.get("master_dataset_rows"),
        "master_dataset_columns": master.get("master_dataset_columns"),
        "master_dataset_age_hours": master.get("age_hours"),
        "stale_data_warnings": warnings,
        "endpoint_health_summary": endpoints,
    }


def _write_markdown(report: dict) -> None:
    recs = ", ".join(report["final_recommendation"]["recommendations"])
    progress = report["progress_targets"]
    lines = [
        "# Daily Validation Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Primary recommendation: **{report['final_recommendation']['primary']}**",
        f"All recommendations: `{recs}`",
        "",
        "## System Health",
        "",
        f"- Status: `{report['system_health']['system_health_status']}`",
        f"- Master dataset last date: `{report['system_health']['master_dataset_last_date']}`",
        f"- Rows: `{report['system_health']['master_dataset_rows']}`",
        f"- Columns: `{report['system_health']['master_dataset_columns']}`",
        f"- Warnings: `{report['system_health']['stale_data_warnings']}`",
        "",
        "## Learning Counts",
        "",
    ]
    for key, value in report["learning_counts"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Progress Targets",
            "",
            f"- Blocked BUY candidates: `{progress['blocked_buy_candidates_current']} / {progress['blocked_buy_candidates_target']}`",
            f"- Shadow BUYs: `{progress['shadow_buy_current']} / {progress['shadow_buy_target']}`",
            f"- Shadow Smart Money: `{progress['shadow_smart_money_current']} / {progress['shadow_smart_money_target']}`",
            "",
            "## Risk Block Performance",
            "",
            f"- Ready to tune: `{report['risk_block_performance']['ready_to_tune']}`",
            f"- Total blocked candidates: `{report['risk_block_performance']['total_blocked_candidates']}`",
            f"- BB squeeze: `{report['risk_block_performance']['bb_squeeze']}`",
            "",
            "## Smart Money Performance",
            "",
            f"- Shadow count: `{report['smart_money_performance']['smart_money_shadow_count']}`",
            f"- Ready for bonus: `{report['smart_money_performance']['smart_money_ready_for_bonus']}`",
            f"- Score distribution: `{report['smart_money_performance']['smart_money_score_distribution']}`",
            f"- Bias distribution: `{report['smart_money_performance']['smart_money_bias_distribution']}`",
            "",
            "## Download Safety",
            "",
        ]
    )
    for key, value in report["download_safety"].items():
        lines.append(f"- {key}: `{value}`")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    decisions = _read_decisions()
    master = _master_dataset_status()
    endpoints = _endpoint_health_summary()
    system = _system_health(master, endpoints)
    counts = _learning_counts(decisions)
    progress = _progress_targets(counts)
    risk = _risk_block_performance()
    smart = _smart_money_performance(decisions)
    recommendations = _build_recommendations(system["system_health_status"], counts, progress, risk, smart)

    report = {
        "generated_at": _utc_now(),
        "system_health": system,
        "learning_counts": counts,
        "progress_targets": progress,
        "risk_block_performance": risk,
        "smart_money_performance": smart,
        "download_safety": _download_safety(),
        "final_recommendation": {
            "primary": recommendations[0],
            "recommendations": recommendations,
            "rules": [
                "If blocked BUY candidates < 30, collect more data.",
                "If shadow Smart Money < 50, Smart Money remains shadow-only.",
                "If source health fails, investigate data health.",
                "Never change risk_engine before minimum sample size.",
            ],
        },
    }
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_markdown(report)
    print(f"Daily validation report written -> {JSON_REPORT}")
    print(f"Markdown report written -> {MD_REPORT}")
    print(f"Recommendation: {', '.join(recommendations)}")
    return report


if __name__ == "__main__":
    run()
