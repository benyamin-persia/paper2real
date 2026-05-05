import re
from datetime import datetime, timezone

import httpx

import trader
from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_ENABLED,
    TELEGRAM_MIN_SEVERITY,
)


SEVERITY_RANK = {"INFO": 10, "WARNING": 20, "CRITICAL": 30}

SECRET_PATTERNS = [
    re.compile(r"(?i)(ANTHROPIC_API_KEY|TELEGRAM_BOT_TOKEN|WEBHOOK_SECRET|API_KEY|TOKEN|PASSWORD|COOKIE|AUTHORIZATION)\s*=\s*([^\s]+)"),
    re.compile(r"(?i)(authorization|cookie|x-api-key)\s*:\s*([^\n\r]+)"),
    re.compile(r"bot\d{8,12}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"sk-ant-[A-Za-z0-9_-]+"),
]


def redact(value) -> str:
    text = str(value)
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(lambda m: f"{m.group(1) if m.groups() else 'SECRET'}=[REDACTED]", text)
    return text


def configured() -> bool:
    return bool(TELEGRAM_ENABLED and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def should_send(severity: str) -> bool:
    if not configured():
        return False
    min_rank = SEVERITY_RANK.get(TELEGRAM_MIN_SEVERITY.upper(), 20)
    return SEVERITY_RANK.get(severity.upper(), 10) >= min_rank


def status() -> dict:
    return {
        "enabled": TELEGRAM_ENABLED,
        "configured": configured(),
        "chat_id_configured": bool(TELEGRAM_CHAT_ID),
        "bot_token_configured": bool(TELEGRAM_BOT_TOKEN),
        "min_severity": TELEGRAM_MIN_SEVERITY,
        "note": "Secrets are never returned by this endpoint.",
    }


def format_message(severity: str, event_type: str, message: str, metadata: dict | None = None) -> str:
    lines = [
        f"[{severity.upper()}] {event_type}",
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "",
        redact(message),
    ]
    clean_meta = {}
    for key, value in (metadata or {}).items():
        if key.lower() in {"token", "api_key", "password", "cookie", "authorization", "secret"}:
            clean_meta[key] = "[REDACTED]"
        elif value is not None:
            clean_meta[key] = redact(value)
    if clean_meta:
        lines.append("")
        for key, value in clean_meta.items():
            lines.append(f"{key}: {value}")
    return "\n".join(lines)[:3900]


async def notify(
    severity: str,
    event_type: str,
    message: str,
    *,
    actor: str = "system",
    source: str | None = None,
    symbol: str | None = "BTC/USD",
    status_text: str | None = None,
    metadata: dict | None = None,
    force: bool = False,
) -> dict:
    severity = severity.upper()
    safe_message = redact(message)
    event_id = trader.log_event(
        severity,
        event_type,
        safe_message,
        actor=actor,
        source=source,
        symbol=symbol,
        status=status_text,
        metadata=metadata or {},
    )

    if not configured() or (not force and not should_send(severity)):
        reason = "telegram_not_configured_or_below_min_severity"
        trader.update_event_telegram(event_id, False, reason)
        return {"event_id": event_id, "telegram_sent": False, "reason": reason, **status()}

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": format_message(severity, event_type, safe_message, metadata),
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=payload)
            if response.status_code >= 400:
                err = f"telegram_http_{response.status_code}: {redact(response.text[:500])}"
                trader.update_event_telegram(event_id, False, err)
                return {"event_id": event_id, "telegram_sent": False, "error": err}
        trader.update_event_telegram(event_id, True)
        return {"event_id": event_id, "telegram_sent": True}
    except Exception as exc:
        err = redact(str(exc))
        trader.update_event_telegram(event_id, False, err)
        return {"event_id": event_id, "telegram_sent": False, "error": err}
