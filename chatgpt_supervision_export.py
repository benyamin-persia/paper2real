"""GitHub-readable supervision export for Paper2Real.

This module is reporting only. It does not change trading logic, thresholds,
portfolio state, risk engine behavior, or any bonus configuration.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import (
    AI_TA_MAX_TQ_BONUS,
    DB_FILE,
    LEARNING_ONLY_SCAN_EXECUTES_TRADES,
    SMART_MONEY_MAX_TQ_BONUS,
    TA_FORECAST_MAX_TQ_BONUS,
)


REPORT_DIR = Path("data/reports")
ROOT_MD = Path("CHATGPT_SUPERVISION_REPORT.md")
REPORT_MD = REPORT_DIR / "chatgpt_supervision_report.md"
REPORT_JSON = REPORT_DIR / "chatgpt_supervision_report.json"
MANIFEST_JSON = REPORT_DIR / "chatgpt_supervision_manifest.json"

REPOSITORY_SLUG = "benyamin-persia/paper2real"
REQUIRED_REPORTS: dict[str, dict[str, str]] = {
    "daily_validation_report.json": {
        "path": "data/reports/daily_validation_report.json",
        "metric_scope": "canonical daily system health, endpoint, safety, learning, TA, and AI TA summary snapshot",
    },
    "daily_validation_report.md": {
        "path": "data/reports/daily_validation_report.md",
        "metric_scope": "human-readable daily validation summary",
    },
    "risk_block_review.json": {
        "path": "data/reports/risk_block_review.json",
        "metric_scope": "risk-blocked candidate review from decisions.risk_blocked_candidate rows",
    },
    "risk_block_review.md": {
        "path": "data/reports/risk_block_review.md",
        "metric_scope": "human-readable risk-blocked candidate review",
    },
    "smart_money_review.json": {
        "path": "data/reports/smart_money_review.json",
        "metric_scope": "Smart Money shadow evidence review; not an execution approval",
    },
    "smart_money_review.md": {
        "path": "data/reports/smart_money_review.md",
        "metric_scope": "human-readable Smart Money shadow review",
    },
    "shadow_buy_review.json": {
        "path": "data/reports/shadow_buy_review.json",
        "metric_scope": "Shadow BUY evidence review from decisions.shadow_action=BUY rows",
    },
    "shadow_buy_review.md": {
        "path": "data/reports/shadow_buy_review.md",
        "metric_scope": "human-readable Shadow BUY review",
    },
    "shadow_paper_test_report.json": {
        "path": "data/reports/shadow_paper_test_report.json",
        "metric_scope": "paper-only Shadow Paper Test lifecycle and paused-entry state",
    },
    "shadow_paper_test_report.md": {
        "path": "data/reports/shadow_paper_test_report.md",
        "metric_scope": "human-readable Shadow Paper Test state",
    },
    "shadow_buy_failure_diagnosis.json": {
        "path": "data/reports/shadow_buy_failure_diagnosis.json",
        "metric_scope": "read-only failure diagnosis across Shadow BUY records and paper trades",
    },
    "shadow_buy_failure_diagnosis.md": {
        "path": "data/reports/shadow_buy_failure_diagnosis.md",
        "metric_scope": "human-readable Shadow BUY failure diagnosis",
    },
    "strict_resume_shadow_simulation.json": {
        "path": "data/reports/strict_resume_shadow_simulation.json",
        "metric_scope": "read-only staged strict-resume simulation; no entries are enabled",
    },
    "strict_resume_shadow_simulation.md": {
        "path": "data/reports/strict_resume_shadow_simulation.md",
        "metric_scope": "human-readable strict-resume simulation",
    },
    "shadow_paper_resume_plan.json": {
        "path": "data/reports/shadow_paper_resume_plan.json",
        "metric_scope": "staged resume plan; recommendations are not applied automatically",
    },
    "shadow_paper_resume_plan.md": {
        "path": "data/reports/shadow_paper_resume_plan.md",
        "metric_scope": "human-readable staged resume plan",
    },
    "ta_forecast.json": {
        "path": "data/reports/ta_forecast.json",
        "metric_scope": "latest deterministic TA forecast, not historical backtest evidence",
    },
    "ta_summary.json": {
        "path": "data/reports/ta_summary.json",
        "metric_scope": "deterministic TA backtest summary over eligible historical rows and score thresholds",
    },
    "ta_backtest.json": {
        "path": "data/reports/ta_backtest.json",
        "metric_scope": "deterministic TA backtest over eligible historical rows and score thresholds",
    },
    "ai_ta_performance.json": {
        "path": "data/reports/ai_ta_performance.json",
        "metric_scope": "live AI TA call/shadow-candidate performance from decisions rows, not threshold replay",
    },
    "ai_ta_summary.json": {
        "path": "data/reports/ai_ta_summary.json",
        "metric_scope": "AI TA deterministic replay summary; no AI calls are made during backtest",
    },
    "ai_ta_backtest.json": {
        "path": "data/reports/ai_ta_backtest.json",
        "metric_scope": "AI TA deterministic replay of TA thresholds; ai_calls_made=0 by design",
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": str(exc)}


def _git(args: list[str], default: str = "") -> str:
    try:
        return subprocess.check_output(["git", *args], text=True).strip()
    except Exception:
        return default


def _metadata_from_existing_report(path: Path = REPORT_JSON) -> dict:
    existing = _read_json(path)
    return {
        "branch": existing.get("branch") or "",
        "source_commit_sha": existing.get("source_commit_sha") or "",
    }


def repo_metadata() -> dict:
    existing = _metadata_from_existing_report()
    branch = (
        _git(["branch", "--show-current"])
        or os.getenv("SUPERVISION_REPORT_BRANCH")
        or existing["branch"]
        or "shadow-paper-paused-20260513"
    )
    source_commit = (
        _git(["rev-parse", "HEAD"])
        or os.getenv("SUPERVISION_REPORT_COMMIT_SHA")
        or existing["source_commit_sha"]
        or "unknown-commit"
    )
    repository = _git(["remote", "get-url", "origin"], f"https://github.com/{REPOSITORY_SLUG}.git")
    return {"repository": repository, "branch": branch, "source_commit_sha": source_commit}


def load_reports(report_dir: Path = REPORT_DIR) -> dict[str, dict]:
    return {name: _read_json(report_dir / name) for name in REQUIRED_REPORTS if name.endswith(".json")}


def _sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _db_fingerprint(db_file: str = DB_FILE) -> dict:
    path = Path(db_file)
    defaults = {
        "total_decisions": 0,
        "max_decision_id": None,
        "latest_decision_timestamp": None,
        "shadow_buy_count": 0,
        "risk_blocked_candidates": 0,
        "smart_money_shadow_count": 0,
        "ta_shadow_count": 0,
        "ai_ta_shadow_count": 0,
        "paper_open_trades": 0,
        "paper_closed_trades": 0,
    }
    if not path.exists():
        return defaults
    con = sqlite3.connect(path)
    try:
        try:
            row = con.execute(
                """
                SELECT
                    COUNT(*) AS total_decisions,
                    MAX(id) AS max_decision_id,
                    MAX(timestamp) AS latest_decision_timestamp,
                    SUM(CASE WHEN UPPER(COALESCE(shadow_action,''))='BUY' THEN 1 ELSE 0 END) AS shadow_buy_count,
                    SUM(CASE WHEN COALESCE(risk_blocked_candidate,0)=1 THEN 1 ELSE 0 END) AS risk_blocked_candidates,
                    SUM(CASE WHEN COALESCE(shadow_smart_money_action,'')!='' THEN 1 ELSE 0 END) AS smart_money_shadow_count,
                    SUM(CASE WHEN COALESCE(shadow_ta_action,'')!='' THEN 1 ELSE 0 END) AS ta_shadow_count,
                    SUM(CASE WHEN COALESCE(shadow_ai_ta_action,'')!='' THEN 1 ELSE 0 END) AS ai_ta_shadow_count
                FROM decisions
                """
            ).fetchone()
            if row:
                keys = (
                    "total_decisions",
                    "max_decision_id",
                    "latest_decision_timestamp",
                    "shadow_buy_count",
                    "risk_blocked_candidates",
                    "smart_money_shadow_count",
                    "ta_shadow_count",
                    "ai_ta_shadow_count",
                )
                defaults.update({key: row[idx] or 0 for idx, key in enumerate(keys)})
        except sqlite3.OperationalError:
            pass
        try:
            open_closed = con.execute(
                """
                SELECT
                    SUM(CASE WHEN COALESCE(closed,0)=0 THEN 1 ELSE 0 END) AS open_trades,
                    SUM(CASE WHEN COALESCE(closed,0)=1 THEN 1 ELSE 0 END) AS closed_trades
                FROM shadow_paper_trades
                """
            ).fetchone()
            if open_closed:
                defaults["paper_open_trades"] = open_closed[0] or 0
                defaults["paper_closed_trades"] = open_closed[1] or 0
        except sqlite3.OperationalError:
            pass
    finally:
        con.close()
    return defaults


def _value(report: dict, key: str, default: Any = None) -> Any:
    return report.get(key, default) if isinstance(report, dict) else default


def _count_check(name: str, values: dict[str, Any]) -> dict:
    present = {key: value for key, value in values.items() if value is not None}
    unique = set(present.values())
    return {
        "name": name,
        "status": "PASS" if len(unique) <= 1 else "FAIL",
        "values": present,
    }


def count_consistency(reports: dict[str, dict]) -> dict:
    daily = reports.get("daily_validation_report.json", {})
    checks = [
        _count_check(
            "shadow_buy_count",
            {
                "daily.shadow_buy_count": _value(daily, "shadow_buy_count"),
                "daily.shadow_buy_review_count": _value(daily, "shadow_buy_review_count"),
                "shadow_buy_review.shadow_buy_count": _value(reports.get("shadow_buy_review.json", {}), "shadow_buy_count"),
                "shadow_paper_test.shadow_buy_review_count": _value(
                    reports.get("shadow_paper_test_report.json", {}), "shadow_buy_review_count"
                ),
                "shadow_buy_failure_diagnosis.total_shadow_buy_records": _value(
                    reports.get("shadow_buy_failure_diagnosis.json", {}), "total_shadow_buy_records"
                ),
                "strict_resume_shadow_simulation.total_shadow_buy_records": _value(
                    reports.get("strict_resume_shadow_simulation.json", {}), "total_shadow_buy_records"
                ),
            },
        ),
        _count_check(
            "risk_blocked_candidates",
            {
                "daily.risk_blocked_candidates": _value(daily, "risk_blocked_candidates"),
                "risk_block_review.total_blocked_candidates": _value(
                    reports.get("risk_block_review.json", {}), "total_blocked_candidates"
                ),
            },
        ),
        _count_check(
            "smart_money_shadow_count",
            {
                "daily.shadow_smart_money_count": _value(daily, "shadow_smart_money_count"),
                "smart_money_review.smart_money_shadow_count": _value(
                    reports.get("smart_money_review.json", {}), "smart_money_shadow_count"
                ),
            },
        ),
    ]
    mismatches = [check for check in checks if check["status"] != "PASS"]
    return {"status": "PASS" if not mismatches else "FAIL", "checks": checks, "mismatches": mismatches}


def _raw_base(repo_meta: dict, ref: str) -> str:
    return f"https://raw.githubusercontent.com/{REPOSITORY_SLUG}/{ref}"


def _browser_base(repo_meta: dict, ref: str) -> str:
    return f"https://github.com/{REPOSITORY_SLUG}/blob/{ref}"


def _required_report_inventory(repo_meta: dict, report_dir: Path) -> dict:
    branch = repo_meta["branch"]
    commit = repo_meta["source_commit_sha"]
    inventory = {}
    for name, meta in REQUIRED_REPORTS.items():
        path = meta["path"]
        local = Path(path) if Path(path).is_absolute() else Path(path)
        inventory[name] = {
            "path": path,
            "present": local.exists(),
            "generated_at": _value(_read_json(local), "generated_at") if path.endswith(".json") else None,
            "metric_scope": meta["metric_scope"],
            "branch_raw_url": f"{_raw_base(repo_meta, branch)}/{path}",
            "branch_github_url": f"{_browser_base(repo_meta, branch)}/{path}",
            "commit_pinned_raw_url": f"{_raw_base(repo_meta, commit)}/{path}",
            "commit_pinned_github_url": f"{_browser_base(repo_meta, commit)}/{path}",
            "sha256": _sha256(local),
        }
    return inventory


def _validation_checks(summary: dict) -> list[dict]:
    checks = [
        ("System health is ok", summary["system_health_status"] == "ok", "daily_validation_report.json: system_health_status"),
        ("Dataset is not stale", summary["stale_dataset_warning"] is False, "daily_validation_report.json: stale_dataset_warning"),
        ("Download ZIP is safe", summary["download_zip_safe"] is True, "daily_validation_report.json: download_zip_safe"),
        ("Secrets excluded", summary["secrets_excluded"] is True, "daily_validation_report.json: secrets_excluded"),
        ("No real trades executed", summary["trades_executed"] == 0, "daily_validation_report.json: trades_executed"),
        ("Paper test entries disabled", summary["paper_test_entries_enabled"] is False, "shadow_paper_test_report.json"),
        ("Paper test has no open trades", summary["paper_open_trades"] == 0, "shadow_paper_test_report.json"),
        ("Risk engine recommendation is keep as-is", summary["final_risk_recommendation"] == "KEEP_AS_IS", "risk_block_review.json"),
        (
            "Smart Money remains shadow-only",
            summary["final_smart_money_recommendation"] == "SMART_MONEY_STAYS_SHADOW",
            "smart_money_review.json",
        ),
        (
            "Shadow BUY remains shadow-only",
            summary["final_shadow_buy_recommendation"] == "SHADOW_BUY_STAYS_SHADOW",
            "shadow_buy_review.json",
        ),
        ("Shadow BUY positive expectancy is false", summary["shadow_buy_positive_expectancy"] is False, "shadow_buy_review.json"),
        ("TA bonus not ready/enabled", summary["ta_ready_for_bonus"] is False, "daily_validation_report.json"),
        ("AI TA bonus not ready/enabled", summary["ai_ta_ready_for_bonus"] is False, "daily_validation_report.json"),
        ("Strict resume says do not resume", summary["strict_resume_recommendation"] == "DO_NOT_RESUME_YET", "strict_resume_shadow_simulation.json"),
        ("Report counts are consistent", summary["count_consistency"]["status"] == "PASS", "count_consistency"),
        ("All required exported paths exist", all(item["present"] for item in summary["required_reports"].values()), "required_reports"),
    ]
    return [{"name": name, "status": "PASS" if ok else "FAIL", "evidence": evidence} for name, ok, evidence in checks]


def build_summary(
    reports: dict[str, dict],
    repo_meta: dict,
    report_dir: Path = REPORT_DIR,
    *,
    snapshot_id: str | None = None,
    db_fingerprint: dict | None = None,
) -> dict:
    bundle_generated_at = _utc_now()
    snapshot_id = snapshot_id or hashlib.sha256(
        json.dumps(
            {
                "bundle_generated_at": bundle_generated_at,
                "commit": repo_meta["source_commit_sha"],
                "counts": count_consistency(reports),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    daily = reports.get("daily_validation_report.json", {})
    paper = reports.get("shadow_paper_test_report.json", {})
    risk = reports.get("risk_block_review.json", {})
    smart = reports.get("smart_money_review.json", {})
    shadow = reports.get("shadow_buy_review.json", {})
    strict = reports.get("strict_resume_shadow_simulation.json", {})
    consistency = count_consistency(reports)
    smart_min_sample = bool(_value(_value(daily, "smart_money_performance", {}), "smart_money_ready_for_bonus", False))
    smart_bonus_approved = _value(smart, "final_smart_money_recommendation") == "SMART_MONEY_READY_FOR_BONUS"
    summary = {
        "generated_at": bundle_generated_at,
        "snapshot_id": snapshot_id,
        "bundle_generated_at": bundle_generated_at,
        "repository": repo_meta["repository"],
        "branch": repo_meta["branch"],
        "source_commit_sha": repo_meta["source_commit_sha"],
        "branch_raw_base_url": _raw_base(repo_meta, repo_meta["branch"]),
        "commit_pinned_raw_base_url": _raw_base(repo_meta, repo_meta["source_commit_sha"]),
        "private_server_note": "Live server is intentionally private. External supervisors should validate GitHub-exported artifacts.",
        "supervision_verdict": "EXPORT_NOT_AUDIT_CLEAN" if consistency["status"] != "PASS" else "DO_NOT_RESUME_TRADING_OR_PAPER_TEST",
        "system_health_status": _value(daily, "system_health_status"),
        "stale_dataset_warning": _value(daily, "stale_dataset_warning"),
        "download_zip_safe": _value(daily, "download_zip_safe"),
        "secrets_excluded": _value(daily, "secrets_excluded"),
        "trades_executed": _value(daily, "trades_executed"),
        "paper_test_entries_enabled": _value(paper, "paper_test_entries_enabled"),
        "paper_test_status": _value(paper, "current_status"),
        "paper_open_trades": _value(paper, "open_test_trades"),
        "paper_closed_trades": _value(paper, "closed_test_trades"),
        "paper_total_pnl_usd": _value(paper, "total_pnl_usd"),
        "final_risk_recommendation": _value(risk, "final_risk_recommendation"),
        "final_smart_money_recommendation": _value(smart, "final_smart_money_recommendation"),
        "smart_money_minimum_sample_reached": smart_min_sample,
        "smart_money_bonus_approved": smart_bonus_approved,
        "final_shadow_buy_recommendation": _value(shadow, "final_shadow_buy_recommendation"),
        "shadow_buy_positive_expectancy": _value(shadow, "positive_expectancy"),
        "ta_ready_for_bonus": _value(daily, "ta_ready_for_bonus"),
        "ai_ta_ready_for_bonus": _value(daily, "ai_ta_ready_for_bonus"),
        "strict_resume_recommendation": _value(strict, "recommendation"),
        "strict_candidates_count": _value(strict, "strict_candidates_count"),
        "strict_candidate_4h_win_rate": _value(strict, "strict_candidate_win_rate_4h"),
        "strict_candidate_avg_return_4h": _value(strict, "strict_candidate_avg_return_4h"),
        "failed_paper_trades_filtered_out": _value(strict, "failed_paper_trades_filtered_out"),
        "count_consistency": consistency,
        "db_fingerprint": {**_db_fingerprint(), **(db_fingerprint or {})},
        "required_reports": _required_report_inventory(repo_meta, report_dir),
    }
    summary["raw_github_urls"] = {
        name: item["commit_pinned_raw_url"] for name, item in summary["required_reports"].items()
    }
    summary["validation_checks"] = _validation_checks(summary)
    return summary


def build_manifest(
    reports: dict[str, dict],
    summary: dict,
    repo_meta: dict,
    *,
    db_fingerprint: dict | None = None,
) -> dict:
    daily = reports.get("daily_validation_report.json", {})
    paper = reports.get("shadow_paper_test_report.json", {})
    fingerprint = {**_db_fingerprint(), **(db_fingerprint or {})}
    fingerprint["shadow_buy_count"] = int(daily.get("shadow_buy_count") or fingerprint.get("shadow_buy_count") or 0)
    fingerprint["smart_money_shadow_count"] = int(
        daily.get("shadow_smart_money_count") or fingerprint.get("smart_money_shadow_count") or 0
    )
    fingerprint["ta_shadow_count"] = int(daily.get("ta_shadow_count") or fingerprint.get("ta_shadow_count") or 0)
    fingerprint["ai_ta_shadow_count"] = int(
        daily.get("ai_ta_shadow_count") or fingerprint.get("ai_ta_shadow_count") or 0
    )
    fingerprint["paper_open_trades"] = int(paper.get("open_test_trades") or fingerprint.get("paper_open_trades") or 0)
    fingerprint["paper_closed_trades"] = int(
        paper.get("closed_test_trades") or fingerprint.get("paper_closed_trades") or 0
    )
    report_files = {
        name: item["path"] for name, item in (summary.get("required_reports") or {}).items()
    }
    return {
        "generated_at": summary.get("generated_at") or summary.get("bundle_generated_at") or _utc_now(),
        "git_branch": repo_meta.get("branch"),
        "git_commit": repo_meta.get("source_commit_sha"),
        "report_files": report_files,
        "report_file_sha256": {
            name: item.get("sha256") for name, item in (summary.get("required_reports") or {}).items()
        },
        "db_fingerprint": fingerprint,
        "safety_flags": {
            "paper_test_entries_enabled": bool(paper.get("paper_test_entries_enabled")),
            "real_trading_enabled": bool(LEARNING_ONLY_SCAN_EXECUTES_TRADES),
            "bonuses_enabled": any(
                float(value or 0) > 0
                for value in (SMART_MONEY_MAX_TQ_BONUS, TA_FORECAST_MAX_TQ_BONUS, AI_TA_MAX_TQ_BONUS)
            ),
            "stale_dataset_warning": bool(daily.get("stale_dataset_warning")),
            "download_zip_safe": bool(daily.get("download_zip_safe")),
            "secrets_excluded": bool(daily.get("secrets_excluded")),
        },
    }


def _line_value(label: str, value: Any) -> str:
    return f"- {label}: `{value}`"


def render_markdown(summary: dict, reports: dict[str, dict]) -> str:
    lines = [
        "# Paper2Real ChatGPT Supervision Report",
        "",
        f"Snapshot ID: `{summary['snapshot_id']}`",
        f"Bundle generated at: `{summary['bundle_generated_at']}`",
        f"Source commit SHA: `{summary['source_commit_sha']}`",
        "",
        "## Executive Verdict",
        "",
        "**DO NOT RESUME Shadow Paper Test. Do not enable bonuses. Do not change trading logic.**",
        "",
        _line_value("Supervision verdict", summary["supervision_verdict"]),
        _line_value("Count consistency", summary["count_consistency"]["status"]),
        _line_value("System health", summary["system_health_status"]),
        _line_value("Stale dataset warning", summary["stale_dataset_warning"]),
        _line_value("Real trades executed", summary["trades_executed"]),
        _line_value("Paper test status", summary["paper_test_status"]),
        _line_value("Paper entries enabled", summary["paper_test_entries_enabled"]),
        _line_value("Final risk recommendation", summary["final_risk_recommendation"]),
        _line_value("Final Smart Money recommendation", summary["final_smart_money_recommendation"]),
        _line_value("Smart Money minimum sample reached", summary["smart_money_minimum_sample_reached"]),
        _line_value("Smart Money bonus approved", summary["smart_money_bonus_approved"]),
        _line_value("Final Shadow BUY recommendation", summary["final_shadow_buy_recommendation"]),
        _line_value("TA ready for bonus", summary["ta_ready_for_bonus"]),
        _line_value("AI TA ready for bonus", summary["ai_ta_ready_for_bonus"]),
        _line_value("Strict resume recommendation", summary["strict_resume_recommendation"]),
        "",
        "## Machine Entry Point",
        "",
        "- Machine source of truth: `data/reports/chatgpt_supervision_report.json`",
        "- Human source of truth: `CHATGPT_SUPERVISION_REPORT.md`",
        "- Use commit-pinned URLs for immutable audits. Branch URLs are convenient but mutable.",
        "",
        "## Validation Checklist",
        "",
    ]
    for check in summary["validation_checks"]:
        lines.append(f"- `{check['status']}` {check['name']} ({check['evidence']})")
    lines.extend(["", "## Count Consistency", ""])
    for check in summary["count_consistency"]["checks"]:
        lines.append(f"- `{check['status']}` {check['name']}: `{json.dumps(check['values'], sort_keys=True)}`")
    lines.extend(["", "## Required Report Inventory", ""])
    for name, item in summary["required_reports"].items():
        lines.append(f"- `{item['path']}`")
        lines.append(f"  - Present: `{item['present']}`")
        lines.append(f"  - Generated at: `{item['generated_at']}`")
        lines.append(f"  - Metric scope: {item['metric_scope']}")
        lines.append(f"  - Branch raw URL: {item['branch_raw_url']}")
        lines.append(f"  - Commit-pinned raw URL: {item['commit_pinned_raw_url']}")
        lines.append(f"  - SHA-256: `{item['sha256']}`")
    return "\n".join(lines) + "\n"


def save_exports(
    summary: dict,
    reports: dict[str, dict],
    repo_meta: dict,
    *,
    db_fingerprint: dict | None = None,
) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    MANIFEST_JSON.write_text(
        json.dumps(build_manifest(reports, summary, repo_meta, db_fingerprint=db_fingerprint), indent=2),
        encoding="utf-8",
    )
    rendered = render_markdown(summary, reports)
    REPORT_MD.write_text(rendered, encoding="utf-8")
    ROOT_MD.write_text(rendered, encoding="utf-8")


def run(
    save: bool = True,
    *,
    report_dir: Path = REPORT_DIR,
    repo_meta: dict | None = None,
    db_fingerprint: dict | None = None,
) -> dict:
    reports = load_reports(report_dir)
    metadata = repo_meta or repo_metadata()
    summary = build_summary(reports, metadata, report_dir, db_fingerprint=db_fingerprint)
    if save:
        save_exports(summary, reports, metadata, db_fingerprint=db_fingerprint)
    return summary


if __name__ == "__main__":
    print(json.dumps(run(save=True), indent=2))
