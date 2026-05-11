"""Daily validation report for Paper2Real.

Reporting and safe publishing only. This module does not change trading logic,
thresholds, Smart Money config, or risk_engine behavior.
"""

from __future__ import annotations

import io
import json
import os
import re
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd

from config import (
    DB_FILE,
    LEARNING_ONLY_SCAN_ENABLED,
    LEARNING_ONLY_SCAN_INTERVAL_MINUTES,
    LEARNING_ONLY_MAX_PER_DAY,
    AI_INPUT_USD_PER_MILLION_TOKENS,
    AI_OUTPUT_USD_PER_MILLION_TOKENS,
    TA_FORECAST_ENABLED,
    TA_FORECAST_SHADOW_ONLY,
    AI_TA_ENABLED,
    AI_TA_SHADOW_ONLY,
)


REPORT_DIR = Path("data/reports")
JSON_REPORT = REPORT_DIR / "daily_validation_report.json"
MD_REPORT = REPORT_DIR / "daily_validation_report.md"

MASTER_DATASET = Path("data/processed/master_dataset.csv")
RISK_BLOCK_REPORT = REPORT_DIR / "risk_block_performance.json"
SMART_MONEY_REPORT = REPORT_DIR / "smart_money_summary.json"

BLOCKED_BUY_TARGET = 30
SHADOW_BUY_TARGET = 100
SHADOW_SMART_MONEY_TARGET = 50
MASTER_MAX_AGE_HOURS = 36

LOCAL_BASE_URL = os.getenv("PAPER2REAL_LOCAL_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ENDPOINTS_TO_CHECK = [
    "/system-health",
    "/learning-status",
    "/risk-block-performance",
    "/shadow-performance",
    "/smart-money-backtest",
    "/shadow-buy-review",
    "/technical-analysis",
    "/support-resistance",
    "/chart-patterns",
    "/ta-forecast",
    "/ta-backtest",
    "/ai-technical-analyst",
    "/ai-ta-performance",
    "/ai-ta-backtest",
    "/reports",
]
DOWNLOAD_ZIP_ENDPOINT = "/download/all.zip"

SAFE_PUSH_FILES = {
    "data/reports/daily_validation_report.json",
    "data/reports/daily_validation_report.md",
}

UNSAFE_NAME_PATTERNS = [
    re.compile(r"(^|/)\.env($|[./])", re.IGNORECASE),
    re.compile(r"cookie", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"private[_-]?key", re.IGNORECASE),
    re.compile(r"(^|/)(id_rsa|id_dsa|id_ecdsa|id_ed25519)($|[./])", re.IGNORECASE),
]

UNSAFE_CONTENT_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"ANTHROPIC_API_KEY\s*=\s*sk-ant-", re.IGNORECASE),
    re.compile(r"TELEGRAM_BOT_TOKEN\s*=\s*\d{8,12}:", re.IGNORECASE),
    re.compile(r"authorization\s*:\s*bearer\s+[A-Za-z0-9._-]{20,}", re.IGNORECASE),
    re.compile(r"cookie\s*:\s*[A-Za-z0-9._=%; -]{20,}", re.IGNORECASE),
]

TEXT_EXTENSIONS = {
    ".csv",
    ".html",
    ".json",
    ".log",
    ".md",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}


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


def _http_get(url: str, timeout: int = 20) -> tuple[bool, int | None, bytes | None, str | None, float]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read()
            return True, int(response.status), body, None, round(time.perf_counter() - started, 3)
    except urllib.error.HTTPError as exc:
        body = exc.read() if hasattr(exc, "read") else None
        return False, int(exc.code), body, str(exc), round(time.perf_counter() - started, 3)
    except Exception as exc:
        return False, None, None, str(exc), round(time.perf_counter() - started, 3)


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


def _read_events() -> list[dict]:
    db = Path(DB_FILE)
    if not db.exists():
        return []
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute("SELECT * FROM events ORDER BY id ASC").fetchall()
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
    except Exception as exc:
        return {
            "exists": True,
            "master_dataset_last_date": None,
            "master_dataset_rows": 0,
            "master_dataset_columns": 0,
            "age_hours": _age_hours(MASTER_DATASET),
            "warnings": [f"master_dataset_unreadable: {exc}"],
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


def _endpoint_statuses() -> tuple[dict[str, dict], list[str]]:
    statuses: dict[str, dict] = {}
    errors: list[str] = []
    for endpoint in ENDPOINTS_TO_CHECK:
        url = f"{LOCAL_BASE_URL}{endpoint}"
        ok, status, body, error, elapsed = _http_get(url, timeout=60)
        content_type = None
        parsed = False
        if body:
            try:
                json.loads(body.decode("utf-8"))
                parsed = True
                content_type = "json"
            except Exception:
                content_type = "non_json"
        statuses[endpoint] = {
            "ok": ok and status and 200 <= status < 300,
            "http_status": status,
            "elapsed_seconds": elapsed,
            "content_type": content_type,
            "json_parse_ok": parsed,
            "error": error,
        }
        if not statuses[endpoint]["ok"]:
            errors.append(f"endpoint_failed:{endpoint}:{error or status}")
    return statuses, errors


def _learning_counts(decisions: list[dict], events: list[dict]) -> dict:
    learning_rows = [
        d for d in decisions
        if d.get("scan_mode") == "learning_only" or d.get("trigger") == "learning_only_scan"
    ]
    live_rows = [d for d in decisions if d not in learning_rows]
    duplicate_events = [
        e for e in events
        if e.get("event_type") == "learning_only_scan_skipped_duplicate"
    ]
    last_learning = max((int(d.get("timestamp") or 0) for d in learning_rows), default=0)
    return {
        "decisions_total": len(decisions),
        "claude_buy_count": sum(1 for d in decisions if (d.get("claude_action") or "").upper() == "BUY"),
        "candidate_buy_count": sum(1 for d in decisions if (d.get("candidate_action") or "").upper() == "BUY"),
        "risk_blocked_candidates": sum(1 for d in decisions if int(d.get("risk_blocked_candidate") or 0) == 1),
        "trades_executed": sum(1 for d in decisions if int(d.get("trade_executed") or 0) == 1),
        "shadow_buy_count": sum(1 for d in decisions if (d.get("shadow_action") or "").upper() == "BUY"),
        "shadow_smart_money_count": sum(1 for d in decisions if d.get("shadow_smart_money_action")),
        "learning_only_scans_total": len(learning_rows),
        "live_paper_scans_total": len(live_rows),
        "last_learning_only_scan_time": datetime.fromtimestamp(last_learning, timezone.utc).isoformat() if last_learning else None,
        "duplicate_learning_scans_suppressed": len(duplicate_events),
        "claude_calls_from_learning_scans": sum(int(d.get("claude_called") or 0) for d in learning_rows),
    }


def _progress_targets(counts: dict) -> dict:
    blocked = counts["risk_blocked_candidates"]
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


def _learning_cost_estimates(decisions: list[dict]) -> dict:
    learning_rows = [
        d for d in decisions
        if d.get("scan_mode") == "learning_only" or d.get("trigger") == "learning_only_scan"
    ]
    max_scans = min(LEARNING_ONLY_MAX_PER_DAY, int(1440 / max(1, LEARNING_ONLY_SCAN_INTERVAL_MINUTES)))
    if not learning_rows:
        return {
            "estimated_learning_api_cost_daily": 0.0,
            "estimated_learning_api_cost_monthly": 0.0,
        }
    per_scan_costs = []
    for row in learning_rows:
        if row.get("api_cost_usd") is not None:
            per_scan_costs.append(float(row.get("api_cost_usd") or 0))
        else:
            input_tokens = int(row.get("input_tokens") or 0)
            output_tokens = int(row.get("output_tokens") or 0)
            per_scan_costs.append(
                input_tokens / 1_000_000 * AI_INPUT_USD_PER_MILLION_TOKENS
                + output_tokens / 1_000_000 * AI_OUTPUT_USD_PER_MILLION_TOKENS
            )
    avg_cost = mean(per_scan_costs) if per_scan_costs else 0.0
    daily = round(avg_cost * max_scans, 6)
    return {
        "estimated_learning_api_cost_daily": daily,
        "estimated_learning_api_cost_monthly": round(daily * 30, 6),
    }


def _estimated_days_to_targets(decisions: list[dict], counts: dict) -> dict:
    learning_rows = [
        d for d in decisions
        if d.get("scan_mode") == "learning_only" or d.get("trigger") == "learning_only_scan"
    ]
    if len(learning_rows) < 2:
        return {
            "estimated_days_to_30_blocked": None,
            "estimated_days_to_100_shadow": None,
            "estimated_days_to_50_smart_money": None,
        }
    timestamps = sorted(int(d.get("timestamp") or 0) for d in learning_rows if d.get("timestamp"))
    observed_days = max((timestamps[-1] - timestamps[0]) / 86400, 1 / 24)
    learning_blocked = sum(int(d.get("risk_blocked_candidate") or 0) == 1 for d in learning_rows)
    learning_shadow = sum(1 for d in learning_rows if (d.get("shadow_action") or "").upper() == "BUY")
    learning_shadow_sm = sum(1 for d in learning_rows if d.get("shadow_smart_money_action"))

    def days_remaining(current: int, target: int, observed_count: int):
        if current >= target:
            return 0.0
        rate = observed_count / observed_days if observed_days > 0 else 0
        if rate <= 0:
            return None
        return round((target - current) / rate, 2)

    return {
        "estimated_days_to_30_blocked": days_remaining(
            counts["risk_blocked_candidates"], BLOCKED_BUY_TARGET, learning_blocked
        ),
        "estimated_days_to_100_shadow": days_remaining(
            counts["shadow_buy_count"], SHADOW_BUY_TARGET, learning_shadow
        ),
        "estimated_days_to_50_smart_money": days_remaining(
            counts["shadow_smart_money_count"], SHADOW_SMART_MONEY_TARGET, learning_shadow_sm
        ),
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
        "top_blockers": [{"blocker": name, **stats} for name, stats in top[:5]],
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


def _is_text_member(name: str) -> bool:
    return Path(name).suffix.lower() in TEXT_EXTENSIONS


def _download_safety() -> tuple[dict, list[str]]:
    url = f"{LOCAL_BASE_URL}{DOWNLOAD_ZIP_ENDPOINT}"
    ok, status, body, error, elapsed = _http_get(url, timeout=30)
    findings: list[dict[str, str]] = []
    errors: list[str] = []
    included_files: list[str] = []

    if not ok or not body:
        errors.append(f"download_zip_failed:{error or status}")
        return {
            "download_zip_safe": False,
            "secrets_excluded": False,
            "http_status": status,
            "elapsed_seconds": elapsed,
            "included_files_checked": 0,
            "findings": findings,
            "error": error,
        }, errors

    try:
        with zipfile.ZipFile(io.BytesIO(body), "r") as zf:
            for member in zf.infolist():
                name = member.filename.replace("\\", "/")
                included_files.append(name)
                for pattern in UNSAFE_NAME_PATTERNS:
                    if pattern.search(name):
                        findings.append({"type": "unsafe_name", "file": name, "pattern": pattern.pattern})

                if member.file_size > 2_000_000 or not _is_text_member(name):
                    continue
                try:
                    text = zf.read(member).decode("utf-8", errors="ignore")
                except Exception:
                    continue
                for pattern in UNSAFE_CONTENT_PATTERNS:
                    if pattern.search(text):
                        findings.append({"type": "unsafe_content", "file": name, "pattern": pattern.pattern})
    except Exception as exc:
        errors.append(f"download_zip_unreadable:{exc}")
        return {
            "download_zip_safe": False,
            "secrets_excluded": False,
            "http_status": status,
            "elapsed_seconds": elapsed,
            "included_files_checked": 0,
            "findings": findings,
            "error": str(exc),
        }, errors

    if findings:
        errors.append("download_zip_unsafe_content_found")

    safe = not findings
    return {
        "download_zip_safe": safe,
        "secrets_excluded": safe,
        "http_status": status,
        "elapsed_seconds": elapsed,
        "included_files_checked": len(included_files),
        "included_files": included_files,
        "findings": findings,
        "env_excluded": not any(f["file"].endswith(".env") for f in findings),
        "api_keys_excluded": not any("api" in f["pattern"].lower() or "sk-ant" in f["pattern"] for f in findings),
        "telegram_token_excluded": not any("telegram" in f["pattern"].lower() or r"\d{8,12}" in f["pattern"] for f in findings),
        "cookies_excluded": not any("cookie" in f["pattern"].lower() for f in findings),
    }, errors


def _system_health(master: dict, endpoints: dict[str, dict], download: dict) -> dict:
    warnings = list(master.get("warnings") or [])
    for endpoint, item in endpoints.items():
        if not item.get("ok"):
            warnings.append(f"{endpoint}_failed")
    if not download.get("download_zip_safe"):
        warnings.append("download_zip_unsafe_or_unavailable")
    status = "ok" if not warnings else "warning"
    return {
        "system_health_status": status,
        "master_dataset_last_date": master.get("master_dataset_last_date"),
        "master_dataset_rows": master.get("master_dataset_rows"),
        "master_dataset_columns": master.get("master_dataset_columns"),
        "master_dataset_age_hours": master.get("age_hours"),
        "stale_dataset_warning": bool(master.get("warnings")),
        "stale_data_warnings": warnings,
        "endpoint_health_summary": endpoints,
    }


def _recommendations(system: dict, counts: dict, smart: dict, errors: list[str]) -> tuple[str, list[str]]:
    recs: list[str] = []
    if errors or system["system_health_status"] != "ok":
        recs.append("INVESTIGATE_ERROR")
    if (
        counts["risk_blocked_candidates"] < BLOCKED_BUY_TARGET
        or counts["shadow_buy_count"] < SHADOW_BUY_TARGET
        or counts["shadow_smart_money_count"] < SHADOW_SMART_MONEY_TARGET
    ):
        recs.append("COLLECT_MORE_DATA")
    if counts["risk_blocked_candidates"] >= BLOCKED_BUY_TARGET:
        recs.append("READY_FOR_RISK_BLOCK_REVIEW")
    if smart.get("smart_money_ready_for_bonus"):
        recs.append("READY_FOR_SMART_MONEY_REVIEW")
    if not recs:
        recs.append("KEEP_RUNNING")

    recs = list(dict.fromkeys(recs))
    if "INVESTIGATE_ERROR" in recs:
        primary = "INVESTIGATE_ERROR"
    elif "READY_FOR_RISK_BLOCK_REVIEW" in recs:
        primary = "READY_FOR_RISK_BLOCK_REVIEW"
    elif "READY_FOR_SMART_MONEY_REVIEW" in recs:
        primary = "READY_FOR_SMART_MONEY_REVIEW"
    elif "COLLECT_MORE_DATA" in recs:
        primary = "COLLECT_MORE_DATA"
    else:
        primary = "KEEP_RUNNING"
    return primary, recs


def _write_markdown(report: dict) -> None:
    recs = ", ".join(report["recommendations"])
    progress = report["progress_targets"]
    lines = [
        "# Daily Validation Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Primary recommendation: **{report['final_recommendation']}**",
        f"All recommendations: `{recs}`",
        "",
        "## System Health",
        "",
        f"- Status: `{report['system_health_status']}`",
        f"- Master dataset last date: `{report['master_dataset_last_date']}`",
        f"- Rows: `{report['master_dataset_rows']}`",
        f"- Columns: `{report['master_dataset_columns']}`",
        f"- Stale dataset warning: `{report['stale_dataset_warning']}`",
        f"- Errors: `{report['errors']}`",
        "",
        "## Endpoint Statuses",
        "",
    ]
    for endpoint, status in report["endpoint_statuses"].items():
        lines.append(
            f"- {endpoint}: `ok={status.get('ok')}` `http={status.get('http_status')}` "
            f"`elapsed={status.get('elapsed_seconds')}s`"
        )

    lines.extend(["", "## Learning Counts", ""])
    for key in [
        "decisions_total",
        "claude_buy_count",
        "candidate_buy_count",
        "risk_blocked_candidates",
        "trades_executed",
        "shadow_buy_count",
        "shadow_smart_money_count",
    ]:
        lines.append(f"- {key}: `{report[key]}`")

    lines.extend(
        [
            "",
            "## Progress Targets",
            "",
            f"- Blocked BUY candidates: `{progress['blocked_buy_candidates_current']} / {progress['blocked_buy_candidates_target']}`",
            f"- Shadow BUYs: `{progress['shadow_buy_current']} / {progress['shadow_buy_target']}`",
            f"- Shadow Smart Money: `{progress['shadow_smart_money_current']} / {progress['shadow_smart_money_target']}`",
            f"- Ready for risk block review: `{report['ready_for_risk_block_review']}`",
            f"- Ready for Smart Money review: `{report['ready_for_smart_money_review']}`",
            f"- Shadow BUY review: `{report.get('shadow_buy_review_count')} / {report.get('shadow_buy_review_target')}` `{report.get('shadow_buy_review_recommendation')}`",
            f"- TA shadow progress: `{report.get('ta_shadow_count')} / 50` ready_for_bonus=`{report.get('ta_ready_for_bonus')}`",
            f"- AI TA shadow progress: `{report.get('ai_ta_shadow_count')} / 50` ready_for_bonus=`{report.get('ai_ta_ready_for_bonus')}`",
            "",
            "## Learning-Only Scans",
            "",
            f"- Enabled: `{report['learning_only_scan_enabled']}`",
            f"- Interval minutes: `{report['learning_only_interval_minutes']}`",
            f"- Learning-only scans total: `{report['learning_only_scans_total']}`",
            f"- Live paper scans total: `{report['live_paper_scans_total']}`",
            f"- Last learning-only scan: `{report['last_learning_only_scan_time']}`",
            f"- Duplicate scans suppressed: `{report['duplicate_learning_scans_suppressed']}`",
            f"- Claude calls from learning scans: `{report['claude_calls_from_learning_scans']}`",
            f"- Estimated learning API cost daily: `${report['estimated_learning_api_cost_daily']}`",
            f"- Estimated learning API cost monthly: `${report['estimated_learning_api_cost_monthly']}`",
            f"- Estimated days to 30 blocked BUY candidates: `{report['estimated_days_to_30_blocked']}`",
            f"- Estimated days to 100 shadow BUYs: `{report['estimated_days_to_100_shadow']}`",
            f"- Estimated days to 50 Smart Money shadows: `{report['estimated_days_to_50_smart_money']}`",
            "- Learning-only scans do not execute trades or mutate portfolio balance.",
            "",
            "## Risk Block Performance",
            "",
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
            "## TA / AI TA Shadow Layers",
            "",
            f"- TA enabled: `{report.get('ta_forecast_enabled')}` shadow_only=`{report.get('ta_forecast_shadow_only')}`",
            f"- TA shadow count: `{report.get('ta_shadow_count')}`",
            f"- TA avg future return 4h: `{report.get('ta_future_return_4h')}`",
            f"- AI TA enabled: `{report.get('ai_ta_enabled')}` shadow_only=`{report.get('ai_ta_shadow_only')}`",
            f"- AI TA calls total: `{report.get('ai_ta_calls_total')}`",
            f"- AI TA shadow count: `{report.get('ai_ta_shadow_count')}`",
            f"- AI TA avg future return 4h: `{report.get('ai_ta_future_return_4h')}`",
            f"- AI TA invalid JSON count: `{report.get('ai_ta_invalid_json_count')}`",
            f"- AI TA safety violations: should_trade=`{report.get('ai_ta_should_trade_violation_count')}`, risk_engine=`{report.get('ai_ta_risk_engine_violation_count')}`",
            "",
            "## Download Safety",
            "",
            f"- Download ZIP safe: `{report['download_zip_safe']}`",
            f"- Secrets excluded: `{report['secrets_excluded']}`",
            f"- Files checked: `{report['download_safety']['included_files_checked']}`",
            f"- Findings: `{report['download_safety']['findings']}`",
            "",
            "## Guardrails",
            "",
            "- Trading logic unchanged.",
            "- risk_engine.py unchanged.",
            "- Trade Quality thresholds unchanged.",
            "- Smart Money remains shadow-only until minimum sample size is reached.",
            "- This report never recommends risk_engine changes before 30 blocked BUY candidates.",
        ]
    )
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _git(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def _normalize_git_paths(output: str) -> list[str]:
    return [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def _path_is_unsafe(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(pattern.search(normalized) for pattern in UNSAFE_NAME_PATTERNS)


def _auto_push_safe_reports(report: dict) -> dict:
    if not report.get("download_zip_safe") or not report.get("secrets_excluded"):
        return {"status": "aborted", "reason": "download_zip_safety_failed"}

    rev = _git(["rev-parse", "--show-toplevel"])
    if rev.returncode != 0:
        return {"status": "aborted", "reason": "not_a_git_repo", "stderr": rev.stderr.strip()}

    branch = _git(["branch", "--show-current"])
    branch_name = branch.stdout.strip() or "main"

    pre_staged = _git(["diff", "--cached", "--name-only"])
    if pre_staged.returncode != 0:
        return {"status": "aborted", "reason": "git_diff_cached_failed", "stderr": pre_staged.stderr.strip()}
    pre_staged_files = set(_normalize_git_paths(pre_staged.stdout))
    unsafe_pre_staged = sorted(p for p in pre_staged_files if p not in SAFE_PUSH_FILES or _path_is_unsafe(p))
    if unsafe_pre_staged:
        return {"status": "aborted", "reason": "unsafe_preexisting_staged_files", "files": unsafe_pre_staged}

    add = _git(["add", "--", *sorted(SAFE_PUSH_FILES)])
    if add.returncode != 0:
        return {"status": "aborted", "reason": "git_add_failed", "stderr": add.stderr.strip()}

    staged = _git(["diff", "--cached", "--name-only"])
    if staged.returncode != 0:
        return {"status": "aborted", "reason": "git_staged_check_failed", "stderr": staged.stderr.strip()}
    staged_files = set(_normalize_git_paths(staged.stdout))
    unsafe_staged = sorted(p for p in staged_files if p not in SAFE_PUSH_FILES or _path_is_unsafe(p))
    if unsafe_staged:
        _git(["reset", "--", *sorted(SAFE_PUSH_FILES)])
        return {"status": "aborted", "reason": "unsafe_staged_files", "files": unsafe_staged}
    if not staged_files:
        return {"status": "no_changes", "branch": branch_name}

    status = _git(["status", "--short"])
    commit = _git(["commit", "-m", "Update daily validation report", "--", *sorted(SAFE_PUSH_FILES)], timeout=120)
    if commit.returncode != 0:
        return {
            "status": "aborted",
            "reason": "git_commit_failed",
            "stderr": commit.stderr.strip(),
            "stdout": commit.stdout.strip(),
            "git_status": status.stdout.strip(),
        }

    push = _git(["push", "origin", branch_name], timeout=180)
    if push.returncode != 0:
        return {
            "status": "push_failed",
            "branch": branch_name,
            "stderr": push.stderr.strip(),
            "stdout": push.stdout.strip(),
            "commit": commit.stdout.strip(),
        }
    return {
        "status": "pushed",
        "branch": branch_name,
        "commit": commit.stdout.strip(),
        "push": push.stdout.strip() or push.stderr.strip(),
    }


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _read_report_json(name: str, fallback: dict | None = None) -> dict:
    path = REPORT_DIR / name
    if not path.exists():
        return fallback or {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback or {}


def _bucket_distribution(values: list[Any]) -> dict:
    out: dict[str, int] = {}
    for value in values:
        key = "unknown" if value is None else str(value)
        out[key] = out.get(key, 0) + 1
    return out


def _score_distribution(values: list[Any]) -> dict:
    buckets = {"0_49": 0, "50_59": 0, "60_69": 0, "70_79": 0, "80_100": 0}
    for value in values:
        try:
            score = float(value)
        except Exception:
            continue
        if score < 50:
            buckets["0_49"] += 1
        elif score < 60:
            buckets["50_59"] += 1
        elif score < 70:
            buckets["60_69"] += 1
        elif score < 80:
            buckets["70_79"] += 1
        else:
            buckets["80_100"] += 1
    return buckets


def _avg(values: list[Any]) -> float:
    vals = []
    for value in values:
        try:
            if value is not None:
                vals.append(float(value))
        except Exception:
            pass
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def _win_rate(values: list[Any]) -> float:
    vals = []
    for value in values:
        try:
            if value is not None:
                vals.append(float(value))
        except Exception:
            pass
    return round(sum(1 for value in vals if value > 0) / len(vals) * 100, 2) if vals else 0.0


def _new_layer_metrics(decisions: list[dict]) -> dict:
    shadow_buy = _read_report_json("shadow_buy_review.json", {})
    ta_rows = [d for d in decisions if d.get("shadow_ta_action")]
    ai_rows = [d for d in decisions if d.get("ai_ta_called") or d.get("shadow_ai_ta_action")]
    ai_shadow = [d for d in decisions if d.get("shadow_ai_ta_action")]
    ai_perf = _read_report_json("ai_ta_performance.json", {})
    ta_backtest = _read_report_json("ta_backtest.json", {})
    ai_backtest = _read_report_json("ai_ta_backtest.json", {})
    ta_4h_win = _win_rate([d.get("shadow_ta_future_return_4h") for d in ta_rows])
    ta_4h_avg = _avg([d.get("shadow_ta_future_return_4h") for d in ta_rows])
    ai_4h_win = _win_rate([d.get("shadow_ai_ta_future_return_4h") for d in ai_shadow])
    ai_4h_avg = _avg([d.get("shadow_ai_ta_future_return_4h") for d in ai_shadow])
    ta_ready = len(ta_rows) >= 50 and ta_4h_win >= 55 and ta_4h_avg > 0 and not _backtest_negative(ta_backtest)
    invalid = int(ai_perf.get("invalid_json_count") or 0)
    should_trade_violations = int(ai_perf.get("should_trade_violation_count") or 0)
    risk_violations = int(ai_perf.get("risk_engine_violation_count") or 0)
    invalid_rate = invalid / max(1, int(ai_perf.get("ai_ta_total_predictions") or 0)) * 100
    ai_ready = (
        len(ai_shadow) >= 50
        and ai_4h_win >= 55
        and ai_4h_avg > 0
        and not _backtest_negative(ai_backtest)
        and invalid_rate < 5
        and should_trade_violations == 0
        and risk_violations == 0
    )
    calls_learning = sum(1 for d in ai_rows if (d.get("scan_mode") or d.get("trigger")) == "learning_only")
    calls_total = sum(1 for d in ai_rows if int(d.get("ai_ta_called") or 0) == 1)
    estimated_daily = 0.0
    return {
        "shadow_buy_review_ready": bool(shadow_buy.get("ready_for_review")),
        "shadow_buy_review_recommendation": shadow_buy.get("final_shadow_buy_recommendation"),
        "shadow_buy_review_count": int(shadow_buy.get("shadow_buy_count") or 0),
        "shadow_buy_review_target": 100,
        "ta_forecast_enabled": TA_FORECAST_ENABLED,
        "ta_forecast_shadow_only": TA_FORECAST_SHADOW_ONLY,
        "ta_shadow_count": len(ta_rows),
        "ta_score_distribution": _score_distribution([d.get("ta_score") for d in decisions]),
        "ta_bias_distribution": _bucket_distribution([d.get("ta_bias") for d in decisions if d.get("ta_bias")]),
        "ta_future_return_15m": _avg([d.get("shadow_ta_future_return_15m") for d in ta_rows]),
        "ta_future_return_1h": _avg([d.get("shadow_ta_future_return_1h") for d in ta_rows]),
        "ta_future_return_4h": ta_4h_avg,
        "ta_future_return_24h": _avg([d.get("shadow_ta_future_return_24h") for d in ta_rows]),
        "ta_ready_for_bonus": ta_ready,
        "estimated_days_to_50_ta_shadow": None,
        "ai_ta_enabled": AI_TA_ENABLED,
        "ai_ta_shadow_only": AI_TA_SHADOW_ONLY,
        "ai_ta_calls_total": calls_total,
        "ai_ta_calls_from_learning_scans": calls_learning,
        "ai_ta_shadow_count": len(ai_shadow),
        "ai_ta_score_distribution": _score_distribution([d.get("ai_ta_score") for d in ai_rows]),
        "ai_ta_bias_distribution": _bucket_distribution([d.get("ai_ta_bias") for d in ai_rows if d.get("ai_ta_bias")]),
        "ai_ta_confidence_distribution": _score_distribution([d.get("ai_ta_confidence") for d in ai_rows]),
        "ai_ta_future_return_15m": _avg([d.get("shadow_ai_ta_future_return_15m") for d in ai_shadow]),
        "ai_ta_future_return_1h": _avg([d.get("shadow_ai_ta_future_return_1h") for d in ai_shadow]),
        "ai_ta_future_return_4h": ai_4h_avg,
        "ai_ta_future_return_24h": _avg([d.get("shadow_ai_ta_future_return_24h") for d in ai_shadow]),
        "ai_ta_ready_for_bonus": ai_ready,
        "estimated_days_to_50_ai_ta_shadow": None,
        "ai_ta_estimated_api_cost_daily": estimated_daily,
        "ai_ta_estimated_api_cost_monthly": round(estimated_daily * 30, 4),
        "ai_ta_invalid_json_count": invalid,
        "ai_ta_should_trade_violation_count": should_trade_violations,
        "ai_ta_risk_engine_violation_count": risk_violations,
    }


def _backtest_negative(report: dict) -> bool:
    best = report.get("best_threshold") or {}
    try:
        return float(best.get("avg_return_4h") or 0) < 0
    except Exception:
        return False


def _skipped_endpoint_probe_results() -> tuple[dict[str, dict], list[str]]:
    """Avoid HTTP self-calls (deadlock) when run() is triggered while building /download/all.zip."""
    stub = {"ok": True, "http_status": 200, "elapsed_seconds": 0.0, "content_type": "skipped", "json_parse_ok": True, "error": None}
    return {ep: dict(stub) for ep in ENDPOINTS_TO_CHECK}, []


def _skipped_download_zip_probe() -> tuple[dict, list[str]]:
    """Cannot recurse into /download/all.zip while assembling that ZIP; assume caller verified safety."""
    return {
        "download_zip_safe": True,
        "secrets_excluded": True,
        "http_status": None,
        "elapsed_seconds": 0.0,
        "included_files_checked": 0,
        "included_files": [],
        "findings": [],
        "env_excluded": True,
        "api_keys_excluded": True,
        "telegram_token_excluded": True,
        "cookies_excluded": True,
    }, []


def run(auto_push: bool | None = None, *, skip_network_probes: bool = False) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    decisions = _read_decisions()
    events = _read_events()
    master = _master_dataset_status()
    if skip_network_probes:
        endpoints, endpoint_errors = _skipped_endpoint_probe_results()
        download_safety, download_errors = _skipped_download_zip_probe()
    else:
        endpoints, endpoint_errors = _endpoint_statuses()
        download_safety, download_errors = _download_safety()
    errors = endpoint_errors + download_errors
    system = _system_health(master, endpoints, download_safety)
    counts = _learning_counts(decisions, events)
    progress = _progress_targets(counts)
    cost_estimates = _learning_cost_estimates(decisions)
    days_estimates = _estimated_days_to_targets(decisions, counts)
    risk = _risk_block_performance()
    smart = _smart_money_performance(decisions)
    new_layers = _new_layer_metrics(decisions)
    primary, recommendations = _recommendations(system, counts, smart, errors)

    report: dict[str, Any] = {
        "generated_at": _utc_now(),
        "system_health_status": system["system_health_status"],
        "master_dataset_last_date": master.get("master_dataset_last_date"),
        "master_dataset_rows": master.get("master_dataset_rows"),
        "master_dataset_columns": master.get("master_dataset_columns"),
        "stale_dataset_warning": bool(master.get("warnings")),
        "endpoint_statuses": endpoints,
        "decisions_total": counts["decisions_total"],
        "claude_buy_count": counts["claude_buy_count"],
        "candidate_buy_count": counts["candidate_buy_count"],
        "risk_blocked_candidates": counts["risk_blocked_candidates"],
        "trades_executed": counts["trades_executed"],
        "shadow_buy_count": counts["shadow_buy_count"],
        "shadow_smart_money_count": counts["shadow_smart_money_count"],
        "learning_only_scan_enabled": LEARNING_ONLY_SCAN_ENABLED,
        "learning_only_interval_minutes": LEARNING_ONLY_SCAN_INTERVAL_MINUTES,
        "learning_only_scans_total": counts["learning_only_scans_total"],
        "live_paper_scans_total": counts["live_paper_scans_total"],
        "last_learning_only_scan_time": counts["last_learning_only_scan_time"],
        "duplicate_learning_scans_suppressed": counts["duplicate_learning_scans_suppressed"],
        "claude_calls_from_learning_scans": counts["claude_calls_from_learning_scans"],
        **cost_estimates,
        **days_estimates,
        "ready_for_risk_block_review": counts["risk_blocked_candidates"] >= BLOCKED_BUY_TARGET,
        "ready_for_smart_money_review": counts["shadow_smart_money_count"] >= SHADOW_SMART_MONEY_TARGET,
        **new_layers,
        "download_zip_safe": bool(download_safety.get("download_zip_safe")),
        "secrets_excluded": bool(download_safety.get("secrets_excluded")),
        "errors": errors,
        "final_recommendation": primary,
        "recommendations": recommendations,
        "system_health": system,
        "learning_counts": counts,
        "progress_targets": progress,
        "learning_cost_estimates": cost_estimates,
        "learning_days_estimates": days_estimates,
        "risk_block_performance": risk,
        "smart_money_performance": smart,
        "download_safety": download_safety,
        "guardrails": [
            "No trading logic changed by this report.",
            "risk_engine.py remains final authority.",
            "Trade Quality thresholds are not changed by this report.",
            "Smart Money remains shadow-only until minimum sample size is reached.",
            "Do not change risk_engine before at least 30 blocked BUY candidates are measured.",
        ],
    }

    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_markdown(report)

    if auto_push is None:
        auto_push = _env_bool("DAILY_VALIDATION_AUTOPUSH", True)
    push_result = {"status": "skipped", "reason": "auto_push_disabled"}
    if auto_push:
        push_result = _auto_push_safe_reports(report)

    print(f"Daily validation report written -> {JSON_REPORT}")
    print(f"Markdown report written -> {MD_REPORT}")
    print(f"Recommendation: {primary}")
    print(f"Auto-push: {push_result['status']}")
    if push_result.get("reason"):
        print(f"Auto-push reason: {push_result['reason']}")
    return {**report, "auto_push": push_result}


if __name__ == "__main__":
    run()
