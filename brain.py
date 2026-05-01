import json
import anthropic
from config import ANTHROPIC_API_KEY
from data.processor.matcher import find_similar, summarize_similar

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

SYSTEM_PROMPT = """You are a Bitcoin market analyst. Your default answer is HOLD.

You advise only. A deterministic risk engine has final authority over execution.
Your job is to give an honest, skeptical assessment — not to find reasons to trade.

STRICT RULES:
- Respond ONLY with valid JSON matching this exact schema:
  {
    "action": "BUY" | "SELL" | "HOLD",
    "confidence": 0-100,
    "reason": "concise explanation of the strongest signal driving your decision",
    "risk_summary": "one sentence on what could invalidate this trade",
    "invalid_if": ["list", "of", "conditions", "that", "would", "cancel", "this"]
  }
- If confidence < 60, action MUST be HOLD — do not force a trade.
- If any key data is missing, stale, or contradictory, action MUST be HOLD.
- If historical win rate < 55%, action MUST be HOLD.
- Never BUY into extreme greed (Fear & Greed > 80) without very strong confirmation.
- Never SELL into extreme fear (Fear & Greed < 20) without very strong confirmation.
- A missed trade is acceptable. A weak trade is not.
- Never chase a pump. Never panic sell.
- Challenge every signal — look for reasons it could fail before reasons to enter.
"""


def decide(signal: dict, portfolio: dict) -> dict:
    """
    signal:    current market data (price, RSI, MACD, etc.)
    portfolio: current paper trading portfolio state
    Returns:   {"action": "BUY"|"SELL"|"HOLD", "reason": str, "confidence": int}
    """

    # find 20 most similar historical moments
    similar  = find_similar(signal, n=20)
    summary  = summarize_similar(similar)
    has_data = bool(summary)

    if client is None:
        return {
            "action": "HOLD",
            "reason": "ANTHROPIC_API_KEY is missing - holding to avoid unmanaged trades",
            "confidence": 0,
            "historical_summary": summary,
        }

    # build historical evidence section
    if has_data:
        evidence = f"""
HISTORICAL EVIDENCE ({summary['matches_found']} similar past moments found):
- Win rate (hit 3% profit before 1% loss): {summary['historical_win_rate_pct']}%
- Average return after 1h:  {summary['avg_return_1h']:+.2f}%
- Average return after 4h:  {summary['avg_return_4h']:+.2f}%
- Average return after 24h: {summary['avg_return_24h']:+.2f}%
- Best case 4h:  {summary['best_case_4h']:+.2f}%
- Worst case 4h: {summary['worst_case_4h']:+.2f}%
- Past signals at similar moments → BUY:{summary['buy_signals']} SELL:{summary['sell_signals']} HOLD:{summary['hold_signals']}
"""
    else:
        evidence = "\nHISTORICAL EVIDENCE: Dataset not yet collected. Proceed conservatively.\n"

    def _fmt(val, fmt=None, suffix=""):
        if val is None:
            return "N/A"
        return f"{val:{fmt}}{suffix}" if fmt else f"{val}{suffix}"

    user_message = f"""
LIVE TECHNICALS:
- BTC Price:      ${signal.get('price', 0):,.2f}
- RSI (14):       {_fmt(signal.get('rsi_14'))}
- MACD:           {_fmt(signal.get('macd'))} | Signal: {_fmt(signal.get('macd_signal'))} | {'Bullish' if signal.get('macd_bullish') else 'Bearish'}
- EMA 20/50/200:  {_fmt(signal.get('ema_20'), '.0f')} / {_fmt(signal.get('ema_50'), '.0f')} / {_fmt(signal.get('ema_200'), '.0f')}
- Above EMA 200:  {signal.get('above_ema200', 'N/A')} | Above EMA 50: {signal.get('above_ema50', 'N/A')}
- BB width:       {_fmt(signal.get('bb_width'))} (squeeze < 0.02)
- ATR (14):       {_fmt(signal.get('atr_14'))}
- Stoch K:        {_fmt(signal.get('stoch_k'))}
- Volume ratio:   {_fmt(signal.get('volume_ratio'))} (>1.5 = high volume)

MARKET STRUCTURE (daily):
- Fear & Greed:       {_fmt(signal.get('fear_greed_index'))} — {signal.get('fear_greed_label', 'N/A')}
- BTC Dominance:      {_fmt(signal.get('btc_dominance'), '.1f', '%')}
- Altcoin Season Idx: {_fmt(signal.get('altcoin_season_index'))} (>75 = altseason, <25 = BTC season)
- BTC Market Cap:     ${signal.get('btc_market_cap', 0) or 0:,.0f}
- USDT Market Cap:    ${signal.get('usdt_market_cap', 0) or 0:,.0f}

DERIVATIVES (daily):
- Funding Rate:       {_fmt(signal.get('funding_rate'))} (positive = longs paying, market bullish)
- Open Interest:      ${signal.get('open_interest', 0) or 0:,.0f}
- Long/Short Ratio:   {_fmt(signal.get('long_short_ratio'))}
- ETF Flow (today):   ${signal.get('etf_flow_usd', 0) or 0:,.0f}
- Long Liquidations:  ${signal.get('long_liquidations', 0) or 0:,.0f}
- Short Liquidations: ${signal.get('short_liquidations', 0) or 0:,.0f}

MACRO:
- S&P 500:  {_fmt(signal.get('sp500'), '.0f')}
- DXY:      {_fmt(signal.get('dxy'), '.2f')} (USD index — rising DXY = bearish for BTC)
- VIX:      {_fmt(signal.get('vix'), '.1f')} (fear index — >30 = high risk-off)
- Gold:     ${_fmt(signal.get('gold'), '.0f')}

HALVING CYCLE:
- Days since last halving (Apr 2024): {_fmt(signal.get('days_since_halving'))}
- Days to next halving (~Apr 2028):   {_fmt(signal.get('days_to_next_halving'))}
- Cycle progress: {_fmt(signal.get('halving_cycle_pct'))}% (bull runs typically peak 12-18 months after halving)

ALERT STATUS:
- Stablecoin depeg: {signal.get('stablecoin_depeg') or 'None'}
- Exchange alert:   {signal.get('exchange_hack_alert') or 'None'}

{evidence}

PORTFOLIO:
- Cash:       ${portfolio['cash_balance_usd']:,.2f}
- BTC held:   {portfolio['btc_held']} BTC (${portfolio['btc_value_usd']:,.2f})
- Total:      ${portfolio['total_portfolio_usd']:,.2f}
- Return:     {portfolio['return_pct']}%
- Open trades:{portfolio['open_trades']}
- Unrealized: ${portfolio['unrealized_pnl_usd']:,.2f}

Based on the historical evidence and current conditions, what is your decision?
Your default is HOLD. Only deviate if the evidence is strong and consistent.

Respond ONLY with this exact JSON (no markdown, no extra text):
{{
  "action": "BUY" | "SELL" | "HOLD",
  "confidence": 0-100,
  "reason": "strongest signal driving your decision",
  "risk_summary": "one sentence on what could invalidate this trade",
  "invalid_if": ["condition1", "condition2"]
}}
"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text = message.content[0].text.strip()

    # strip markdown code fences if present
    if "```" in text:
        text = text.split("```")[1].strip()
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        result = json.loads(text)
        action     = result.get("action", "HOLD").upper()
        confidence = int(result.get("confidence", 0))

        # enforce schema — if action is not a valid value, default to HOLD
        if action not in ("BUY", "SELL", "HOLD"):
            action = "HOLD"

        # enforce confidence floor at this layer too (risk_engine will also check)
        if confidence < 60 and action != "HOLD":
            action = "HOLD"

        return {
            "action":           action,
            "confidence":       confidence,
            "reason":           result.get("reason", "No reason provided"),
            "risk_summary":     result.get("risk_summary", ""),
            "invalid_if":       result.get("invalid_if", []),
            "historical_summary": summary,
        }
    except (json.JSONDecodeError, ValueError):
        return {
            "action":             "HOLD",
            "reason":             "Malformed AI response — holding to be safe",
            "confidence":         0,
            "risk_summary":       "Response could not be parsed",
            "invalid_if":         [],
            "historical_summary": summary,
        }
