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

SHADOW_BUY_SCORE_THRESHOLD = float(os.getenv("SHADOW_BUY_SCORE_THRESHOLD", "60"))
TRADE_QUALITY_BUY_THRESHOLD = float(os.getenv("TRADE_QUALITY_BUY_THRESHOLD", "65"))
TRADE_QUALITY_CAN_PROPOSE_BUY = os.getenv("TRADE_QUALITY_CAN_PROPOSE_BUY", "true").lower() in {"1", "true", "yes", "on"}
STRATEGY_VERSION = os.getenv("STRATEGY_VERSION", "tq65_shadow60_risk_v1")

SMART_MONEY_ENABLED = os.getenv("SMART_MONEY_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
SMART_MONEY_SCORE_ENABLED = os.getenv("SMART_MONEY_SCORE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
SMART_MONEY_MAX_SCORE = float(os.getenv("SMART_MONEY_MAX_SCORE", "15"))
SMART_MONEY_SHADOW_ONLY = os.getenv("SMART_MONEY_SHADOW_ONLY", "true").lower() in {"1", "true", "yes", "on"}
SMART_MONEY_TIMEFRAMES = [
    x.strip() for x in os.getenv("SMART_MONEY_TIMEFRAMES", "15m,1h,4h").split(",") if x.strip()
]
SMART_MONEY_SWING_LENGTH = int(os.getenv("SMART_MONEY_SWING_LENGTH", "5"))
SMART_MONEY_MIN_SCORE_FOR_BUY_BONUS = float(os.getenv("SMART_MONEY_MIN_SCORE_FOR_BUY_BONUS", "60"))
SMART_MONEY_MAX_TQ_BONUS = float(os.getenv("SMART_MONEY_MAX_TQ_BONUS", "0"))
SMART_MONEY_NO_REPAINT = os.getenv("SMART_MONEY_NO_REPAINT", "true").lower() in {"1", "true", "yes", "on"}

LEARNING_ONLY_SCAN_ENABLED = os.getenv("LEARNING_ONLY_SCAN_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
LEARNING_ONLY_SCAN_INTERVAL_MINUTES = int(os.getenv("LEARNING_ONLY_SCAN_INTERVAL_MINUTES", "60"))
LEARNING_ONLY_SCAN_EXECUTES_TRADES = os.getenv("LEARNING_ONLY_SCAN_EXECUTES_TRADES", "false").lower() in {"1", "true", "yes", "on"}
LEARNING_ONLY_CALL_CLAUDE_MODE = os.getenv("LEARNING_ONLY_CALL_CLAUDE_MODE", "selective").lower()
LEARNING_ONLY_MAX_PER_DAY = int(os.getenv("LEARNING_ONLY_MAX_PER_DAY", "24"))

# ATR stop multipliers — shared by risk_engine.py and trader.py
ATR_INITIAL_STOP_MULT = float(os.getenv("ATR_INITIAL_STOP_MULT", "1.5"))  # initial stop = entry - 1.5×ATR
ATR_TRAIL_STOP_MULT   = float(os.getenv("ATR_TRAIL_STOP_MULT",   "2.0"))  # trailing stop = peak - 2.0×ATR
