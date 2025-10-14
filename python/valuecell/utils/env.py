import os


def agent_debug_mode_enabled() -> bool:
    return os.getenv("AGENT_DEBUG_MODE", "false").lower() == "true"
