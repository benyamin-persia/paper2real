import asyncio
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def _install_coinglass_require(page):
    return await page.evaluate(
        """() => {
            window.webpackChunk_N_E.push([
                [Math.floor(Math.random() * 1000000)],
                {},
                function(req) { window.__cg_req = req; },
            ]);
            return !!window.__cg_req;
        }"""
    )


async def _fetch_first_capi_array(page, urls: list[str]):
    return await page.evaluate(
        """async (urls) => {
            const findArray = (value) => {
                if (Array.isArray(value)) return value;
                if (!value || typeof value !== 'object') return [];
                for (const key of ['data', 'list', 'rows', 'result', 'history']) {
                    const nested = findArray(value[key]);
                    if (nested.length) return nested;
                }
                return [];
            };

            for (const url of urls) {
                try {
                    const r = await fetch(url, {
                        credentials: 'include',
                        headers: {
                            accept: 'application/json',
                            origin: 'https://www.coinglass.com',
                            referer: 'https://www.coinglass.com/',
                        },
                    });
                    if (!r.ok) continue;
                    const d = await r.json();
                    const data = findArray(d?.data);
                    if (data.length) return {url, data, code: d.code, msg: d.msg};
                } catch(e) {}
            }
            return null;
        }""",
        urls,
    )


async def _fetch_named_capi_array(page, name: str, urls: list[str]):
    result = await _fetch_first_capi_array(page, urls)
    if result:
        print(f"  {name}: {len(result['data']):,} rows from {result['url']}")
    else:
        print(f"  {name}: failed")
    return result


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

        print("  Loading CoinGlass funding page...")
        await page.goto(
            "https://www.coinglass.com/FundingRate",
            wait_until="domcontentloaded",
            timeout=90000,
        )
        await asyncio.sleep(8)
        await _install_coinglass_require(page)

        print("  Fetching funding rate history from capi...")
        funding = await _fetch_named_capi_array(
            page,
            "Funding rate fetch",
            [
                "https://capi.coinglass.com/api/futures/fundingRate/chart?symbol=BTC&type=1&interval=1d",
                "https://capi.coinglass.com/api/v2/futures/fundingRate/oi-weight/history?symbol=BTC&interval=1d&limit=730",
                "https://capi.coinglass.com/api/futures/fundingRate/home/list?symbol=BTC&interval=1d",
            ],
        )
        decoded_funding = None
        if not funding:
            print("  Reading decoded funding rate history from CoinGlass app...")
            decoded_funding = await page.evaluate(
                """async () => {
                    const api = window.__cg_req && window.__cg_req(94126);
                    if (!api || !api.iOq) return null;
                    try {
                        return await api.iOq({
                            symbol: 'BTC',
                            interval: 'h8',
                            index: 'avg_fr_kline',
                            limit: 3000,
                        });
                    } catch(e) {
                        return null;
                    }
                }"""
            )
            data = decoded_funding.get("data") if isinstance(decoded_funding, dict) else []
            print(f"  Funding decoded fallback: {len(data) if isinstance(data, list) else 0:,} rows")

        print("  Loading CoinGlass liquidations page...")
        await page.goto(
            "https://www.coinglass.com/liquidations",
            wait_until="domcontentloaded",
            timeout=90000,
        )
        await asyncio.sleep(8)
        await _install_coinglass_require(page)

        print("  Reading decoded liquidation history from CoinGlass app...")
        liquidation = await page.evaluate(
            """async () => {
                const api = window.__cg_req && window.__cg_req(94126);
                if (!api || !api.UKl) return null;

                const ranges = ['all', '730d', '365d', '180d', '90d'];
                let best = null;
                for (const range of ranges) {
                    try {
                        const result = await api.UKl({
                            symbol: 'BTC',
                            timeType: 4,
                            range,
                        });
                        const data = Array.isArray(result?.data) ? result.data : [];
                        if (!best || data.length > best.data.length) {
                            best = {range, data, code: result?.code, msg: result?.msg};
                        }
                    } catch(e) {}
                }
                return best;
            }"""
        )

        print("  Fetching Open Interest history from capi...")
        open_interest = await _fetch_first_capi_array(
            page,
            [
                "https://capi.coinglass.com/api/futures/openInterest/chart?symbol=BTC&interval=1d",
                "https://capi.coinglass.com/api/v2/futures/openInterest/history?symbol=BTC&interval=1d&limit=730",
                "https://capi.coinglass.com/api/futures/openInterest/history/chart?symbol=BTC&interval=1d",
            ],
        )
        if open_interest:
            print(f"  Open Interest fetch: {len(open_interest['data']):,} rows")
        else:
            print("  Open Interest fetch: failed")

        print("  Fetching Long/Short Ratio from capi...")
        long_short = await _fetch_named_capi_array(
            page,
            "Long/Short fetch",
            [
                "https://capi.coinglass.com/api/futures/longShortRate/chart?symbol=BTC&type=1&interval=1d",
                "https://capi.coinglass.com/api/v2/futures/longShort/history?symbol=BTC&interval=1d&limit=730&type=1",
                "https://capi.coinglass.com/api/futures/longShortAccount?symbol=BTC&interval=1d",
            ],
        )
        decoded_long_short = None
        if not long_short:
            print("  Loading CoinGlass long/short page...")
            await page.goto(
                "https://www.coinglass.com/LongShortRatio",
                wait_until="domcontentloaded",
                timeout=90000,
            )
            await asyncio.sleep(8)
            await _install_coinglass_require(page)
            print("  Reading decoded long/short history from CoinGlass app...")
            decoded_long_short = await page.evaluate(
                """async () => {
                    const api = window.__cg_req && window.__cg_req(94126);
                    if (!api || !api.ygi) return null;
                    try {
                        return await api.ygi({
                            symbol: 'Binance_BTCUSDT#global_account_kline',
                            interval: '1d',
                            limit: 3000,
                            minLimit: false,
                        });
                    } catch(e) {
                        return null;
                    }
                }"""
            )
            data = (
                decoded_long_short.get("data")
                if isinstance(decoded_long_short, dict)
                else []
            )
            print(f"  Long/Short decoded fallback: {len(data) if isinstance(data, list) else 0:,} rows")

        print("  Fetching BTC ETF flows from capi...")
        etf_flow = await _fetch_first_capi_array(
            page,
            [
                "https://capi.coinglass.com/api/etf/flow/history?limit=365",
                "https://capi.coinglass.com/api/etf/bitcoin/flow/history",
                "https://capi.coinglass.com/api/etf/flow",
            ],
        )
        if etf_flow:
            print(f"  ETF flow fetch: {len(etf_flow['data']):,} rows")
        else:
            print("  ETF flow fetch: failed")

        print("  Reading decoded Open Interest / ETF data from CoinGlass app...")
        decoded_extra = await page.evaluate(
            """async () => {
                const api = window.__cg_req && window.__cg_req(94126);
                if (!api) return {};
                const out = {};
                try {
                    out.open_interest = await api.UAh({
                        symbol: 'BTC',
                        timeType: 0,
                        exchangeName: '',
                        currency: 'USD',
                        type: 0,
                    });
                } catch(e) {}
                try {
                    out.etf_flow = await api.W64({});
                } catch(e) {}
                return out;
            }"""
        )

        await browser.close()

    return {
        "funding": funding or decoded_funding,
        "liquidation": liquidation,
        "open_interest": open_interest or decoded_extra.get("open_interest"),
        "long_short": long_short or decoded_long_short,
        "etf_flow": etf_flow or decoded_extra.get("etf_flow"),
    }


def _parse_funding(raw) -> pd.DataFrame:
    direct = _parse_direct_value_rows(
        raw,
        "funding_rate",
        ["r", "rate", "value", "c"],
    )
    if not direct.empty:
        return direct.groupby("date", as_index=False)["funding_rate"].mean()

    items = raw.get("data", []) if isinstance(raw, dict) else []
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        values = item.get("data")
        if not isinstance(values, list) or len(values) < 5:
            continue
        try:
            rows.append(
                {
                    "date": pd.to_datetime(int(values[0]), unit="s").date(),
                    "funding_rate": float(values[4]),
                }
            )
        except Exception:
            continue
    df = pd.DataFrame(rows, columns=["date", "funding_rate"])
    if not df.empty:
        return df.groupby("date", as_index=False)["funding_rate"].mean()

    data = raw.get("data", {}) if isinstance(raw, dict) else {}
    dates = data.get("dateList", [])
    data_map = data.get("dataMap", {})

    rows = []
    if not dates or not isinstance(data_map, dict):
        return pd.DataFrame(columns=["date", "funding_rate"])

    exchanges = [name for name, values in data_map.items() if isinstance(values, list)]
    for i, ts in enumerate(dates):
        rates = []
        for exchange in exchanges:
            values = data_map.get(exchange) or []
            if i < len(values):
                rate = pd.to_numeric(values[i], errors="coerce")
                if pd.notna(rate):
                    rates.append(float(rate))
        if rates:
            rows.append(
                {
                    "date": pd.to_datetime(int(ts), unit="ms").date(),
                    "funding_rate": sum(rates) / len(rates),
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["date", "funding_rate"])
    return (
        df.groupby("date", as_index=False)["funding_rate"]
        .mean()
        .sort_values("date")
        .reset_index(drop=True)
    )


def _parse_liquidation(raw) -> pd.DataFrame:
    items = raw.get("data", []) if isinstance(raw, dict) else []
    rows = []
    for item in items:
        try:
            rows.append(
                {
                    "date": pd.to_datetime(int(item["createTime"]), unit="ms").date(),
                    "long_liquidations": float(item.get("buyVolUsd") or 0),
                    "short_liquidations": float(item.get("sellVolUsd") or 0),
                }
            )
        except Exception:
            continue

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(
            columns=["date", "long_liquidations", "short_liquidations"]
        )
    return (
        df.groupby("date", as_index=False)[
            ["long_liquidations", "short_liquidations"]
        ]
        .sum()
        .sort_values("date")
        .reset_index(drop=True)
    )


def _item_date(item: dict):
    ts = item.get("t") or item.get("time") or item.get("createTime") or item.get("date")
    if ts is None:
        return None
    if isinstance(ts, str) and not ts.isdigit():
        return pd.to_datetime(ts).date()
    ts = int(ts)
    return pd.to_datetime(ts, unit="ms" if ts > 10_000_000_000 else "s").date()


def _parse_direct_value_rows(raw, column: str, keys: list[str]) -> pd.DataFrame:
    items = raw.get("data", []) if isinstance(raw, dict) else []
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            date = _item_date(item)
            value = None
            for key in keys:
                if item.get(key) is not None:
                    value = item.get(key)
                    break
            if date is not None and value is not None:
                rows.append({"date": date, column: float(value)})
        except Exception:
            continue
    return pd.DataFrame(rows, columns=["date", column]).dropna()


def _parse_open_interest(raw) -> pd.DataFrame:
    direct = _parse_direct_value_rows(
        raw,
        "open_interest",
        ["o", "openInterest", "open_interest", "c", "value"],
    )
    if not direct.empty:
        return direct.drop_duplicates("date").sort_values("date").reset_index(drop=True)

    data = raw.get("data", {}) if isinstance(raw, dict) else {}
    dates = data.get("dateList", [])
    data_map = data.get("dataMap", {})
    rows = []
    if dates and isinstance(data_map, dict):
        exchanges = [name for name, values in data_map.items() if isinstance(values, list)]
        for i, ts in enumerate(dates):
            values = []
            for exchange in exchanges:
                series = data_map.get(exchange) or []
                if i < len(series):
                    value = pd.to_numeric(series[i], errors="coerce")
                    if pd.notna(value):
                        values.append(float(value))
            if values:
                rows.append(
                    {
                        "date": pd.to_datetime(int(ts), unit="ms").date(),
                        "open_interest": sum(values),
                    }
                )
    return pd.DataFrame(rows, columns=["date", "open_interest"]).drop_duplicates("date")


def _parse_long_short(raw) -> pd.DataFrame:
    direct = _parse_direct_value_rows(
        raw,
        "long_short_ratio",
        ["longRate", "longRatio", "longShortRate", "r", "value"],
    )
    if not direct.empty:
        return direct.drop_duplicates("date").sort_values("date").reset_index(drop=True)

    items = raw.get("data", []) if isinstance(raw, dict) else []
    rows = []
    for item in items:
        if not isinstance(item, list) or len(item) < 2:
            continue
        try:
            rows.append(
                {
                    "date": pd.to_datetime(int(item[0]), unit="s").date(),
                    "long_short_ratio": float(item[1]),
                }
            )
        except Exception:
            continue
    df = pd.DataFrame(rows, columns=["date", "long_short_ratio"])
    if not df.empty:
        return df.groupby("date", as_index=False)["long_short_ratio"].mean()

    data = raw.get("data", {}) if isinstance(raw, dict) else {}
    dates = data.get("dateList", [])
    ratios = data.get("longShortRateList") or data.get("longRateList") or []
    rows = []
    for i, ts in enumerate(dates):
        if i < len(ratios):
            try:
                rows.append(
                    {
                        "date": pd.to_datetime(int(ts), unit="ms").date(),
                        "long_short_ratio": float(ratios[i]),
                    }
                )
            except Exception:
                continue
    df = pd.DataFrame(rows, columns=["date", "long_short_ratio"])
    return df.groupby("date", as_index=False)["long_short_ratio"].mean()


def _parse_etf_flow(raw) -> pd.DataFrame:
    direct = _parse_direct_value_rows(
        raw,
        "etf_flow",
        ["totalFlow", "netFlow", "flow", "changeUsd", "value"],
    )
    if not direct.empty:
        return direct.drop_duplicates("date").sort_values("date").reset_index(drop=True)

    items = raw.get("data", []) if isinstance(raw, dict) else []
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            date = _item_date(item)
            value = (
                item.get("totalFlow")
                or item.get("netFlow")
                or item.get("flow")
                or item.get("changeUsd")
                or item.get("change")
            )
            if date is not None and value is not None:
                rows.append({"date": date, "etf_flow": float(value)})
        except Exception:
            continue
    return pd.DataFrame(rows, columns=["date", "etf_flow"]).drop_duplicates("date")


def scrape() -> pd.DataFrame:
    print("Scraping CoinGlass via Playwright...")
    result = asyncio.run(_scrape())

    df_f = _parse_funding(result.get("funding") or {})
    df_l = _parse_liquidation(result.get("liquidation") or {})
    df_oi = _parse_open_interest(result.get("open_interest") or {})
    df_ls = _parse_long_short(result.get("long_short") or {})
    df_etf = _parse_etf_flow(result.get("etf_flow") or {})
    print(f"  Funding: {len(df_f):,} days, Liquidation: {len(df_l):,} days")
    print(f"  Open Interest: {len(df_oi):,} days")
    print(f"  Long/Short Ratio: {len(df_ls):,} days")
    print(f"  ETF Flow: {len(df_etf):,} days")

    frames = [df_f, df_l, df_oi, df_ls, df_etf]
    df = pd.DataFrame(columns=["date"])
    for frame in frames:
        if frame is not None and not frame.empty:
            df = frame if df.empty else pd.merge(df, frame, on="date", how="outer")

    if df.empty:
        df = pd.DataFrame(
            columns=[
                "date",
                "funding_rate",
                "long_liquidations",
                "short_liquidations",
                "open_interest",
                "long_short_ratio",
                "etf_flow",
            ]
        )

    for col in [
        "funding_rate",
        "long_liquidations",
        "short_liquidations",
        "open_interest",
        "long_short_ratio",
        "etf_flow",
    ]:
        if col not in df.columns:
            df[col] = pd.NA
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df[["long_liquidations", "short_liquidations"]] = df[
        ["long_liquidations", "short_liquidations"]
    ].fillna(0)

    df = df[
        [
            "date",
            "funding_rate",
            "long_liquidations",
            "short_liquidations",
            "open_interest",
            "long_short_ratio",
            "etf_flow",
        ]
    ].sort_values("date").reset_index(drop=True)

    out = OUTPUT_DIR / "coinglass.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df):,} rows -> {out}")
    return df


if __name__ == "__main__":
    scrape()
