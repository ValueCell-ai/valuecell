"""Constants for auto trading agent"""

from valuecell.core.types import ComponentType

# Component types
TRADING_COMPONENT_TYPE = ComponentType.FILTERED_CARD_PUSH_NOTIFICATION.value
PORTFOLIO_COMPONENT_TYPE = ComponentType.FILTERED_LINE_CHART.value

# Limits
MAX_SYMBOLS = 10
DEFAULT_CHECK_INTERVAL = 60  # 1 minute in seconds

# Default configuration values
DEFAULT_INITIAL_CAPITAL = 100000
DEFAULT_RISK_PER_TRADE = 0.02
DEFAULT_MAX_POSITIONS = 3
DEFAULT_AGENT_MODEL = "deepseek/deepseek-v3.1-terminus"
