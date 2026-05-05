import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
WEBHOOK_SECRET    = os.getenv("WEBHOOK_SECRET", "my_secret_123")

STARTING_BALANCE  = float(os.getenv("STARTING_BALANCE", "10000"))  # USD
TRADE_SIZE_PCT    = float(os.getenv("TRADE_SIZE_PCT", "0.10"))      # 10% of balance per trade
MAX_OPEN_TRADES   = int(os.getenv("MAX_OPEN_TRADES", "3"))

# Safety mechanisms — auto-pause trading if any of these trigger
MAX_DRAWDOWN_PCT      = float(os.getenv("MAX_DRAWDOWN_PCT", "20"))    # stop if portfolio drops 20%
MAX_CONSECUTIVE_LOSS  = int(os.getenv("MAX_CONSECUTIVE_LOSS", "4"))   # stop after 4 losses in a row
DAILY_LOSS_LIMIT_PCT  = float(os.getenv("DAILY_LOSS_LIMIT_PCT", "5")) # stop if down 5% in one day
MONTHLY_LOSS_LIMIT_PCT = float(os.getenv("MONTHLY_LOSS_LIMIT_PCT", "15")) # stop if down 15% in one month

DB_FILE = "paper_trader.db"

AI_INPUT_USD_PER_MILLION_TOKENS = float(os.getenv("AI_INPUT_USD_PER_MILLION_TOKENS", "3.00"))
AI_OUTPUT_USD_PER_MILLION_TOKENS = float(os.getenv("AI_OUTPUT_USD_PER_MILLION_TOKENS", "15.00"))

TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_MIN_SEVERITY = os.getenv("TELEGRAM_MIN_SEVERITY", "WARNING").upper()

# ATR stop multipliers — shared by risk_engine.py and trader.py
ATR_INITIAL_STOP_MULT = float(os.getenv("ATR_INITIAL_STOP_MULT", "1.5"))  # initial stop = entry - 1.5×ATR
ATR_TRAIL_STOP_MULT   = float(os.getenv("ATR_TRAIL_STOP_MULT",   "2.0"))  # trailing stop = peak - 2.0×ATR
