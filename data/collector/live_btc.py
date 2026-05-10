"""Redundant live BTC 15m candle provider using Playwright browser fetches.

Primary source order:
1. Kraken OHLC
2. Coinbase candles
3. Yahoo Finance v8
4. cached data/raw/live_btc_15m.csv as emergency fallback

This module intentionally fetches public JSON through a Playwright browser
context instead of scraping fragile chart DOM.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright


LIVE_CANDLES_FILE = Path("data/raw/live_btc_15m.csv")
STATUS_FILE = Path("data/raw/live_btc_source_status.json")
MIN_CANDLES = 100
MAX_AGE_MINUTES = 20

# Reuse one Playwright fetch briefly so /portfolio, /system-health, and scans do not each launch a browser (TrueNAS was spending ~30–90s per call).
_LIVE_CACHE_LOCK = asyncio.Lock()
_cached_live_df: pd.DataFrame | None = None
_cached_live_mono: float = 0.0
LIVE_CANDLE_CACHE_TTL_SEC = 45.0


def _clean(df: pd.DataFrame, source: str) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["timestamp", "open", "high", "low", "close"])
    df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"])
    df["source"] = source
    return df.tail(250).reset_index(drop=True)


def _status_for(df: pd.DataFrame, source: str) -> dict:
    if df.empty:
        return {"source": source, "ok": False, "reason": "empty"}
    latest = pd.to_datetime(df["timestamp"].iloc[-1], utc=True, errors="coerce")
    age_min = None
    if pd.notna(latest):
        age_min = (datetime.now(timezone.utc) - latest.to_pydatetime()).total_seconds() / 60
    zero_all = float((df["volume"].fillna(0) <= 0).mean())
    zero_recent = float((df["volume"].tail(50).fillna(0) <= 0).mean())
    reasons = []
    if len(df) < MIN_CANDLES:
        reasons.append(f"only_{len(df)}_candles")
    if age_min is None or age_min > MAX_AGE_MINUTES:
        reasons.append(f"stale_{round(age_min, 1) if age_min is not None else 'unknown'}m")
    if df["close"].isna().any():
        reasons.append("missing_close")
    volume_quality = "unreliable" if zero_all > 0.10 or zero_recent > 0.20 else "reliable"
    return {
        "source": source,
        "ok": not reasons,
        "reason": ", ".join(reasons) if reasons else "ok",
        "rows": int(len(df)),
        "latest_timestamp": latest.isoformat() if pd.notna(latest) else None,
        "age_minutes": round(age_min, 2) if age_min is not None else None,
        "zero_volume_ratio": round(zero_all, 3),
        "recent_zero_volume_ratio": round(zero_recent, 3),
        "volume_quality": volume_quality,
    }


async def _new_context(p):
    browser = await p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ],
    )
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 900},
        locale="en-US",
        timezone_id="America/New_York",
    )
    await context.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4] });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        window.chrome = window.chrome || { runtime: {} };
        """
    )
    return browser, context


async def _fetch_json(page, url: str, headers: dict | None = None):
    try:
        return await page.evaluate(
            """async ({url, headers}) => {
                const res = await fetch(url, {
                    credentials: 'include',
                    headers: headers || {}
                });
                const text = await res.text();
                return { ok: res.ok, status: res.status, text };
            }""",
            {"url": url, "headers": headers or {}},
        )
    except Exception:
        # Some exchange endpoints deny cross-origin browser fetches but still
        # render JSON when the browser navigates directly to the public URL.
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        text = await page.locator("body").inner_text(timeout=10000)
        return {
            "ok": bool(response and response.ok),
            "status": response.status if response else 0,
            "text": text,
        }


async def _kraken(page) -> pd.DataFrame:
    await page.goto("https://www.kraken.com", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(800)
    payload = await _fetch_json(page, "https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=15")
    if not payload.get("ok"):
        raise RuntimeError(f"kraken_http_{payload.get('status')}")
    data = json.loads(payload["text"])
    raw = data.get("result", {}).get("XXBTZUSD") or data.get("result", {}).get("XBTUSD")
    if not raw:
        for key, value in data.get("result", {}).items():
            if key != "last" and isinstance(value, list):
                raw = value
                break
    if not raw:
        raise RuntimeError("kraken_no_ohlc")
    rows = [
        {
            "timestamp": pd.to_datetime(float(x[0]), unit="s"),
            "open": x[1],
            "high": x[2],
            "low": x[3],
            "close": x[4],
            "volume": x[6],
        }
        for x in raw
    ]
    return _clean(pd.DataFrame(rows), "kraken")


async def _coinbase(page) -> pd.DataFrame:
    await page.goto("https://www.coinbase.com", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(800)
    end = int(time.time())
    start = end - 300 * 900
    url = (
        "https://api.exchange.coinbase.com/products/BTC-USD/candles"
        f"?granularity=900&start={datetime.fromtimestamp(start, timezone.utc).isoformat()}"
        f"&end={datetime.fromtimestamp(end, timezone.utc).isoformat()}"
    )
    payload = await _fetch_json(page, url)
    if not payload.get("ok"):
        raise RuntimeError(f"coinbase_http_{payload.get('status')}")
    raw = json.loads(payload["text"])
    if not isinstance(raw, list) or not raw:
        raise RuntimeError("coinbase_no_candles")
    df = pd.DataFrame(raw, columns=["timestamp", "low", "high", "open", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    return _clean(df, "coinbase")


async def _yahoo(page) -> pd.DataFrame:
    await page.goto("https://finance.yahoo.com", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(1500)
    urls = [
        "https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=15m&range=5d",
        "https://query2.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=15m&range=5d",
    ]
    last_error = None
    for url in urls:
        try:
            payload = await _fetch_json(page, url)
            if not payload.get("ok"):
                raise RuntimeError(f"yahoo_http_{payload.get('status')}")
            data = json.loads(payload["text"])
            result = data["chart"]["result"][0]
            timestamps = result.get("timestamp") or []
            quote = result["indicators"]["quote"][0]
            df = pd.DataFrame(
                {
                    "timestamp": pd.to_datetime(timestamps, unit="s"),
                    "open": quote.get("open", []),
                    "high": quote.get("high", []),
                    "low": quote.get("low", []),
                    "close": quote.get("close", []),
                    "volume": quote.get("volume", []),
                }
            )
            return _clean(df, "yahoo")
        except Exception as e:
            last_error = e
    raise RuntimeError(f"yahoo_failed: {last_error}")


def _cached() -> pd.DataFrame:
    if not LIVE_CANDLES_FILE.exists():
        return pd.DataFrame()
    df = pd.read_csv(LIVE_CANDLES_FILE)
    if "source" not in df.columns:
        df["source"] = "cache"
    return _clean(df, "cache")


def _save(df: pd.DataFrame, status: dict) -> None:
    LIVE_CANDLES_FILE.parent.mkdir(parents=True, exist_ok=True)
    cols = ["timestamp", "open", "high", "low", "close", "volume", "source"]
    df[cols].to_csv(LIVE_CANDLES_FILE, index=False)
    STATUS_FILE.write_text(json.dumps(status, indent=2), encoding="utf-8")


async def _fetch_live_candles_playwright() -> pd.DataFrame:
    status = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selected_source": None,
        "buy_block": False,
        "sources": [],
    }
    async with async_playwright() as p:
        browser, context = await _new_context(p)
        try:
            page = await context.new_page()
            for name, fn in (("kraken", _kraken), ("coinbase", _coinbase), ("yahoo", _yahoo)):
                try:
                    df = await fn(page)
                    source_status = _status_for(df, name)
                    status["sources"].append(source_status)
                    if source_status["ok"]:
                        status["selected_source"] = name
                        status["volume_quality"] = source_status["volume_quality"]
                        _save(df, status)
                        return df
                except Exception as e:
                    status["sources"].append({"source": name, "ok": False, "reason": str(e)[:300]})
        finally:
            await browser.close()

    cached = _cached()
    cache_status = _status_for(cached, "cache")
    status["sources"].append(cache_status)
    if not cached.empty:
        status["selected_source"] = "cache"
        status["buy_block"] = True
        status["volume_quality"] = cache_status.get("volume_quality")
        _save(cached, status)
        return cached
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(status, indent=2), encoding="utf-8")
    raise RuntimeError("No live BTC candle source available")


async def get_live_candles() -> pd.DataFrame:
    global _cached_live_df, _cached_live_mono
    async with _LIVE_CACHE_LOCK:
        now = time.monotonic()
        if (
            _cached_live_df is not None
            and not _cached_live_df.empty
            and (now - _cached_live_mono) < LIVE_CANDLE_CACHE_TTL_SEC
        ):
            return _cached_live_df.copy()
        df = await _fetch_live_candles_playwright()
        _cached_live_df = df
        _cached_live_mono = time.monotonic()
        return df.copy()


def read_status() -> dict:
    if not STATUS_FILE.exists():
        return {}
    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def scrape() -> pd.DataFrame:
    return asyncio.run(get_live_candles())


if __name__ == "__main__":
    out = scrape()
    print(f"Saved {len(out)} live BTC candles from {out['source'].iloc[-1] if not out.empty else 'none'}")
