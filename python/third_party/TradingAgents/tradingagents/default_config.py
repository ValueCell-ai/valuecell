import os
from pathlib import Path

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Look for .env file in the project root directory
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)
        print(f"✅ Loaded environment variables from {env_file} (with override)")
    else:
        print(f"ℹ️  No .env file found at {env_file}, using system environment variables")
except ImportError:
    print("⚠️  python-dotenv not installed. Install it with: pip install python-dotenv")
    print("   Environment variables will be read from system environment only.")

def str_to_bool(value):
    """Convert string to boolean, handling various string representations."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return bool(value)

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_dir": os.getenv("TRADINGAGENTS_DATA_DIR", "./data"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    "llm_provider": os.getenv("TRADINGAGENTS_LLM_PROVIDER", "openai"),
    "deep_think_llm": os.getenv("TRADINGAGENTS_DEEP_THINK_LLM", "o4-mini"),
    "quick_think_llm": os.getenv("TRADINGAGENTS_QUICK_THINK_LLM", "gpt-4o-mini"),
    "backend_url": os.getenv("TRADINGAGENTS_BACKEND_URL", "https://api.openai.com/v1"),
    # Embeddings settings
    "EMBEDDER_BASE_URL": os.getenv("EMBEDDER_BASE_URL", "https://api.openai.com/v1"),
    "EMBEDDER_MODEL_ID": os.getenv("EMBEDDER_MODEL_ID", "text-embedding-3-small"),
    # Debate and discussion settings
    "max_debate_rounds": int(os.getenv("TRADINGAGENTS_MAX_DEBATE_ROUNDS", "1")),
    "max_risk_discuss_rounds": int(os.getenv("TRADINGAGENTS_MAX_RISK_DISCUSS_ROUNDS", "1")),
    "max_recur_limit": int(os.getenv("TRADINGAGENTS_MAX_RECUR_LIMIT", "100")),
    # Tool settings
    "online_tools": str_to_bool(os.getenv("TRADINGAGENTS_ONLINE_TOOLS", "True")),
}
