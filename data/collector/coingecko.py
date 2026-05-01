import asyncio
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def _fetch_json(page, path: str):
    for _ in range(3):
        try:
            return await page.evaluate(
                """async (path) => {
                    const r = await fetch(path, {
                        credentials: 'include',
                        headers: {accept: 'application/json'},
                    });
                    if (!r.ok) return null;
                    return await r.json();
                }""",
                path,
            )
        except Exception:
            await asyncio.sleep(2)
    return None


async def _fetch_first_json(page, urls: list[str]):
    for _ in range(3):
        try:
            return await page.evaluate(
                """async (urls) => {
                    for (const url of urls) {
                        try {
                            const r = await fetch(url, {
                                credentials: 'include',
                                headers: {accept: 'application/json'},
                            });
                            if (r.ok) return await r.json();
                        } catch(e) {}
                    }
                    return null;
                }""",
                urls,
            )
        except Exception:
            await asyncio.sleep(2)
    return None


async def _scrape() -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        print("  Loading CoinGecko BTC page...")
        await page.goto(
            "https://www.coingecko.com/en/coins/bitcoin",
            wait_until="domcontentloaded",
            timeout=90000,
        )
        await asyncio.sleep(4)

        print("  Fetching BTC price/volume via Playwright...")
        btc_price = await _fetch_json(page, "/price_charts/bitcoin/usd/max.json")
        btc_market_cap = await _fetch_json(
            page,
            "/market_cap/coins_market_cap_chart_data?coin_ids=1&days=max&locale=en&vs_currency=usd",
        )
        print("  Fetching USDT market cap via Playwright...")
        usdt_market_cap = await _fetch_first_json(
            page,
            [
                "/market_data/price_charts/tether/usd/max.json",
                "/price_charts/825/usd/max.json",
                "https://www.coingecko.com/market_data/price_charts/tether/usd/max.json",
                "https://www.coingecko.com/price_charts/825/usd/max.json",
            ],
        )

        print("  Loading CoinGecko global charts...")
        await page.goto(
            "https://www.coingecko.com/en/charts",
            wait_until="domcontentloaded",
            timeout=90000,
        )
        await asyncio.sleep(4)
        await page.wait_for_load_state("domcontentloaded")

        print("  Fetching total market cap and BTC dominance via Playwright...")
        total_market_cap = await _fetch_json(
            page,
            "/market_cap/total_charts_data?locale=en&vs_currency=usd",
        )
        dominance = await _fetch_json(
            page,
            "/global_charts/bitcoin_dominance_data?locale=en",
        )

        print("  Fetching Altcoin Season Index via Playwright...")
        altcoin_season = await _fetch_first_json(
            page,
            [
                "https://www.coingecko.com/en/coins/categories/alt-season-index",
                "/en/coins/categories/alt-season-index",
            ],
        )
        if not altcoin_season:
            print("  Altcoin season: direct source not available; using BTC dominance fallback")

        await browser.close()

    return {
        "btc_price": btc_price,
        "btc_market_cap": btc_market_cap,
        "total_market_cap": total_market_cap,
        "dominance": dominance,
        "usdt_market_cap": usdt_market_cap,
        "altcoin_season": altcoin_season,
    }


def _series_from_list(data, name: str | None = None) -> list:
    if isinstance(data, dict):
        return data.get("stats", [])
    if isinstance(data, list):
        if name:
            for item in data:
                if isinstance(item, dict) and item.get("name") == name:
                    return item.get("data", [])
        if data and isinstance(data[0], dict):
            return data[0].get("data", [])
    return []


def _date_from_ms(ts) -> object:
    return pd.to_datetime(int(ts), unit="ms").date()


def _date_from_any(value) -> object:
    if isinstance(value, (int, float)) or str(value).isdigit():
        unit = "ms" if int(value) > 10_000_000_000 else "s"
        return pd.to_datetime(int(value), unit=unit).date()
    return pd.to_datetime(value).date()


def _parse_altcoin_index(raw) -> dict:
    rows = {}
    if not raw:
        return rows

    candidates = []
    if isinstance(raw, list):
        candidates = raw
    elif isinstance(raw, dict):
        for key in ["data", "values", "stats", "history"]:
            if isinstance(raw.get(key), list):
                candidates = raw[key]
                break

    for item in candidates:
        try:
            if isinstance(item, list) and len(item) >= 2:
                rows[_date_from_any(item[0])] = item[1]
            elif isinstance(item, dict):
                date = item.get("date") or item.get("timestamp") or item.get("time") or item.get("x")
                value = (
                    item.get("value")
                    or item.get("index")
                    or item.get("altcoinSeasonIndex")
                    or item.get("y")
                )
                if date is not None and value is not None:
                    rows[_date_from_any(date)] = value
        except Exception:
            continue
    return rows


def _parse_coingecko(data: dict, days_back: int = 730) -> pd.DataFrame:
    rows_by_date = {}

    btc = data.get("btc_price") or {}
    price_rows = btc.get("stats", []) if isinstance(btc, dict) else []
    volume_rows = btc.get("total_volumes", []) if isinstance(btc, dict) else []

    for ts, price in price_rows:
        rows_by_date.setdefault(_date_from_ms(ts), {})["btc_close"] = price
    for ts, vol in volume_rows:
        rows_by_date.setdefault(_date_from_ms(ts), {})["btc_volume"] = vol
    print(f"  BTC price rows: {len(price_rows):,}")
    print(f"  BTC volume rows: {len(volume_rows):,}")

    cap_rows = _series_from_list(data.get("btc_market_cap"), "Bitcoin")
    for ts, cap in cap_rows:
        rows_by_date.setdefault(_date_from_ms(ts), {})["btc_market_cap"] = cap
    print(f"  BTC market cap rows: {len(cap_rows):,}")

    total_cap_by_date = {}
    total_rows = _series_from_list(data.get("total_market_cap"), "market_cap")
    for ts, cap in total_rows:
        total_cap_by_date[_date_from_ms(ts)] = cap
    print(f"  Total market cap rows: {len(total_rows):,}")

    dom_rows = _series_from_list(data.get("dominance"), "BTC")
    for ts, dominance in dom_rows:
        rows_by_date.setdefault(_date_from_ms(ts), {})["btc_dominance"] = dominance
    print(f"  BTC dominance rows: {len(dom_rows):,}")

    usdt_raw = data.get("usdt_market_cap")
    usdt_rows = usdt_raw.get("market_caps", []) if isinstance(usdt_raw, dict) else []
    if not usdt_rows:
        usdt_rows = _series_from_list(usdt_raw)
    for ts, cap in usdt_rows:
        rows_by_date.setdefault(_date_from_ms(ts), {})["usdt_market_cap"] = cap
    print(f"  USDT market cap rows: {len(usdt_rows):,}")

    altcoin_rows = _parse_altcoin_index(data.get("altcoin_season"))
    for date, value in altcoin_rows.items():
        rows_by_date.setdefault(date, {})["altcoin_season_index"] = value
    if altcoin_rows:
        print(f"  Altcoin season rows: {len(altcoin_rows):,}")

    for date, vals in rows_by_date.items():
        if vals.get("btc_dominance") is None:
            btc_cap = vals.get("btc_market_cap")
            total_cap = total_cap_by_date.get(date)
            if btc_cap and total_cap:
                vals["btc_dominance"] = btc_cap / total_cap * 100

    rows = []
    for date, vals in sorted(rows_by_date.items()):
        rows.append(
            {
                "date": date,
                "btc_market_cap": vals.get("btc_market_cap"),
                "btc_dominance": vals.get("btc_dominance"),
                "btc_volume": vals.get("btc_volume"),
                "btc_close": vals.get("btc_close"),
                "usdt_market_cap": vals.get("usdt_market_cap"),
                "altcoin_season_index": vals.get("altcoin_season_index"),
            }
        )

    columns = [
        "date",
        "btc_market_cap",
        "btc_dominance",
        "btc_volume",
        "btc_close",
        "usdt_market_cap",
        "altcoin_season_index",
    ]
    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        return df

    max_date = pd.to_datetime(df["date"]).max()
    min_date = max_date - pd.Timedelta(days=days_back)
    df = df[pd.to_datetime(df["date"]) >= min_date]

    numeric_cols = [
        "btc_market_cap",
        "btc_dominance",
        "btc_volume",
        "btc_close",
        "usdt_market_cap",
        "altcoin_season_index",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["btc_market_cap", "btc_dominance"])
    if df["altcoin_season_index"].isna().all():
        dominance_delta = df["btc_dominance"].diff(7)
        df["altcoin_season_index"] = 50
        df.loc[dominance_delta < -1, "altcoin_season_index"] = 75
        df.loc[dominance_delta > 1, "altcoin_season_index"] = 25
        print("  Altcoin season rows: calculated from BTC dominance")
    else:
        dominance_delta = df["btc_dominance"].diff(7)
        fallback = pd.Series(50, index=df.index)
        fallback.loc[dominance_delta < -1] = 75
        fallback.loc[dominance_delta > 1] = 25
        df["altcoin_season_index"] = df["altcoin_season_index"].fillna(fallback)
    return df.sort_values("date").reset_index(drop=True)


def scrape() -> pd.DataFrame:
    print("Scraping CoinGecko via Playwright...")
    data = asyncio.run(_scrape())

    df = _parse_coingecko(data)
    out = OUTPUT_DIR / "coingecko.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df):,} days -> {out}")
    return df


if __name__ == "__main__":
    scrape()
