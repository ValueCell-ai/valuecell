"""Constants for auto trading agent"""

# Limits
MAX_SYMBOLS = 10
DEFAULT_CHECK_INTERVAL = 60  # 1 minute in seconds

# Default configuration values
DEFAULT_INITIAL_CAPITAL = 100000
DEFAULT_RISK_PER_TRADE = 0.02
DEFAULT_MAX_POSITIONS = 3

# Environment variable keys for model override
# These allow users to override specific models via environment variables
ENV_PARSER_MODEL_ID = "AUTO_TRADING_PARSER_MODEL_ID"
ENV_SIGNAL_MODEL_ID = "AUTO_TRADING_SIGNAL_MODEL_ID"
ENV_PRIMARY_MODEL_ID = "AUTO_TRADING_AGENT_MODEL_ID"

# Deprecated (kept for backward compatibility)
DEFAULT_AGENT_MODEL = "deepseek/deepseek-v3.1-terminus"
