#!/usr/bin/env python3
"""Paper2Real report monitor.

Read-only monitor:
- checks the live server first, then GitHub raw reports as fallback
- alerts via Telegram on safety/reporting changes and readiness thresholds
- never imports app trading modules and never executes trades
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SERVER_BASE = os.getenv("PAPER2REAL_SERVER_BASE", "http://192.168.196.102:8000").rstrip("/")
GITHUB_BASE_RAW = os.getenv(
    "PAPER2REAL_GITHUB_REPORTS_RAW",
    "https://raw.githubusercontent.com/benyamin-persia/paper2real/main/data/reports",
).rstrip("/")
CHECK_INTERVAL_HOURS = float(os.getenv("PAPER2REAL_MONITOR_INTERVAL_HOURS", "12"))
STATE_FILE = Path(os.getenv("PAPER2REAL_MONITOR_STATE", "data/reports/monitor_paper2real_state.json"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

SHADOW_BUY_ALERT = int(os.getenv("PAPER2REAL_SHADOW_BUY_ALERT", "100"))
SMART_MONEY_ALERT = int(os.getenv("PAPER2REAL_SMART_MONEY_ALERT", "50"))
TA_SHADOW_ALERT = int(os.getenv("PAPER2REAL_TA_SHADOW_ALERT", "50"))
AI_TA_SHADOW_ALERT = int(os.getenv("PAPER2REAL_AI_TA_SHADOW_ALERT", "50"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_get(url: str, timeout: int = 15) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "paper2real-monitor/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"http_{response.status}")
        payload = response.read().decode("utf-8")
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise RuntimeError("json_root_not_object")
    return value


def fetch_report(file_name: str) -> tuple[dict[str, Any], str]:
    urls = [
        f"{SERVER_BASE}/report-file?path=data/reports/{file_name}",
        f"{GITHUB_BASE_RAW}/{file_name}",
    ]
    errors: list[str] = []
    for url in urls:
        try:
            return _json_get(url), url
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError(f"Cannot fetch {file_name}; " + " | ".join(errors))


def telegram_alert(message: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set; alert not sent")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    body = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": message[:3900]}).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status >= 400:
                print(f"Telegram alert failed: http_{response.status}")
    except Exception as exc:
        print(f"Telegram alert failed: {exc}")


def _load_state() -> dict[str, Any]:
    try:
        if STATE_FILE.exists():
            value = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
    except Exception:
        pass
    return {}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _dedupe_alerts(alerts: list[str]) -> list[str]:
    state = _load_state()
    digest = hashlib.sha256("\n".join(alerts).encode("utf-8")).hexdigest() if alerts else ""
    if digest and digest == state.get("last_alert_digest"):
        print("Alerts unchanged since last run; Telegram suppressed.")
        return []
    state["last_checked_at"] = _utc_now()
    state["last_alert_digest"] = digest
    state["last_alerts"] = alerts
    _save_state(state)
    return alerts


def _distribution_count(value: Any) -> int:
    if isinstance(value, dict):
        return sum(int(v or 0) for v in value.values())
    try:
        return int(value or 0)
    except Exception:
        return 0


def check_reports() -> list[str]:
    alerts: list[str] = []
    sources: dict[str, str] = {}

    daily, sources["daily"] = fetch_report("daily_validation_report.json")
    supervision, sources["supervision"] = fetch_report("chatgpt_supervision_report.json")
    shadow, sources["shadow_buy"] = fetch_report("shadow_buy_review.json")
    smart, sources["smart_money"] = fetch_report("smart_money_review.json")
    ta_summary, sources["ta_summary"] = fetch_report("ta_summary.json")
    ai_perf, sources["ai_ta_performance"] = fetch_report("ai_ta_performance.json")
    ai_summary, sources["ai_ta_summary"] = fetch_report("ai_ta_summary.json")

    if daily.get("system_health_status") != "ok":
        alerts.append(f"System health: {daily.get('system_health_status')} ({daily.get('runtime_hard_block_reason') or 'see daily report'})")
    if daily.get("stale_dataset_warning"):
        alerts.append(f"Stale dataset: age={daily.get('master_dataset_age_hours')}h")
    if daily.get("execution_frozen"):
        alerts.append(f"Execution frozen: blockers={daily.get('runtime_hard_blockers')}")

    verdict = supervision.get("supervision_verdict", "")
    consistency = (supervision.get("count_consistency") or {}).get("status")
    if consistency != "PASS":
        alerts.append(f"Count consistency: {consistency}")
    if "DO_NOT_RESUME" not in str(verdict):
        alerts.append(f"Supervision changed: {verdict}")

    shadow_count = int(shadow.get("shadow_buy_count") or daily.get("shadow_buy_review_count") or 0)
    shadow_rec = shadow.get("final_shadow_buy_recommendation", "")
    if shadow_count >= SHADOW_BUY_ALERT or "READY" in shadow_rec:
        alerts.append(f"Shadow BUY threshold: {shadow_count}, recommendation={shadow_rec}")

    smart_count = int(smart.get("smart_money_shadow_count") or daily.get("shadow_smart_money_count") or 0)
    smart_rec = smart.get("final_smart_money_recommendation", "")
    if smart_count >= SMART_MONEY_ALERT or "READY" in smart_rec:
        alerts.append(f"Smart Money threshold: {smart_count}, recommendation={smart_rec}")

    ta_shadow = int(daily.get("ta_shadow_count") or ta_summary.get("ta_shadow_count") or ta_summary.get("shadow_count") or 0)
    if ta_shadow >= TA_SHADOW_ALERT:
        alerts.append(f"TA shadow threshold: {ta_shadow}")

    ai_shadow = int(
        daily.get("ai_ta_shadow_count")
        or ai_perf.get("ai_ta_shadow_candidates")
        or ai_summary.get("ai_ta_shadow_count")
        or ai_summary.get("shadow_count")
        or 0
    )
    if ai_shadow >= AI_TA_SHADOW_ALERT:
        alerts.append(f"AI TA shadow threshold: {ai_shadow}")

    print(
        json.dumps(
            {
                "checked_at": _utc_now(),
                "sources": sources,
                "supervision_verdict": verdict,
                "count_consistency": consistency,
                "execution_frozen": daily.get("execution_frozen"),
                "shadow_buy_count": shadow_count,
                "smart_money_shadow_count": smart_count,
                "ta_shadow_count": ta_shadow,
                "ai_ta_shadow_count": ai_shadow,
                "alerts": alerts,
            },
            indent=2,
        )
    )
    return alerts


def run_once() -> int:
    try:
        alerts = check_reports()
    except Exception as exc:
        alerts = [f"Paper2Real monitor failed: {exc}"]

    alerts = _dedupe_alerts(alerts)
    if alerts:
        message = "Paper2Real Alerts:\n" + "\n".join(f"- {alert}" for alert in alerts)
        telegram_alert(message)
        print(message)
        return 1
    print("No new alert triggered.")
    return 0


def main() -> None:
    once = os.getenv("PAPER2REAL_MONITOR_ONCE", "").lower() in {"1", "true", "yes", "on"}
    while True:
        print(f"Checking Paper2Real reports at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        run_once()
        if once:
            return
        time.sleep(CHECK_INTERVAL_HOURS * 3600)


if __name__ == "__main__":
    main()
