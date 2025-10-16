# Agno Framework Injected Constants
# Reference: https://docs.agno.com/

# Key for tracking business context, request types, and operational information
# Used for monitoring, analytics, and debugging purposes
METADATA = "metadata"

# Key for injecting user profiles and temporal context information
# Enables personalized and time-aware agent responses
DEPENDENCIES = "dependencies"


# ValueCell Framework Injected Constants
# Context keys for retrieving runtime data and user-specific information

# User profile data key
# Contains user preferences, settings, and historical interaction data
USER_PROFILE = "user_profile"

# Current context data key
# Provides situational awareness and state information for the agent
CURRENT_CONTEXT = "current_context"

# Language preference key
# Specifies the user's preferred language for responses and interactions
LANGUAGE = "language"

# Timezone configuration key
# Defines the user's timezone for temporal calculations and time-sensitive operations
TIMEZONE = "timezone"


# ValueCell Framework Runtime Constants

# ExecutionContext Storage Keys
# Stores the planning task for planning context
PLANNING_TASK = "planning_task"

# Original User Input Key
# Stores the original user input
ORIGINAL_USER_INPUT = "original_user_input"
