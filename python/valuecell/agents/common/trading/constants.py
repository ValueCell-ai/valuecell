"""Default constants used across the strategy_agent package.

Centralizes defaults so they can be imported from one place.
"""

DEFAULT_INITIAL_CAPITAL = 100000.0
DEFAULT_AGENT_MODEL = "deepseek-ai/DeepSeek-V3.1-Terminus"
DEFAULT_MODEL_PROVIDER = "siliconflow"
DEFAULT_MAX_POSITIONS = 5
DEFAULT_MAX_SYMBOLS = 5
DEFAULT_MAX_LEVERAGE = 10.0
DEFAULT_CAP_FACTOR = 1.5

# Feature grouping constants
FEATURE_GROUP_BY_KEY = "group_by_key"
FEATURE_GROUP_BY_INTERVAL_PREFIX = "interval_"
FEATURE_GROUP_BY_MARKET_SNAPSHOT = "market_snapshot"
