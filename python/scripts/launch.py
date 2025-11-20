"""
Interactive agent launcher script.
Allows users to select an agent from available options and launch it using uv.
"""

import os
import shlex
import signal
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict

from valuecell.utils.env import ensure_system_env_dir, get_system_env_path

# Mapping from agent name to analyst key (for ai-hedge-fund agents)
MAP_NAME_ANALYST: Dict[str, str] = {
    "AswathDamodaranAgent": "aswath_damodaran",
    "BenGrahamAgent": "ben_graham",
    "BillAckmanAgent": "bill_ackman",
    "CathieWoodAgent": "cathie_wood",
    "CharlieMungerAgent": "charlie_munger",
    "FundamentalsAnalystAgent": "fundamentals_analyst",
    "MichaelBurryAgent": "michael_burry",
    "MohnishPabraiAgent": "mohnish_pabrai",
    "PeterLynchAgent": "peter_lynch",
    "PhilFisherAgent": "phil_fisher",
    "RakeshJhunjhunwalaAgent": "rakesh_jhunjhunwala",
    "SentimentAnalystAgent": "sentiment_analyst",
    "StanleyDruckenmillerAgent": "stanley_druckenmiller",
    "TechnicalAnalystAgent": "technical_analyst",
    "ValuationAnalystAgent": "valuation_analyst",
    "WarrenBuffettAgent": "warren_buffett",
}
TRADING_AGENTS_NAME = "TradingAgents"
RESEARCH_AGENT_NAME = "ResearchAgent"
AUTO_TRADING_AGENT_NAME = "AutoTradingAgent"
NEWS_AGENT_NAME = "NewsAgent"
STRATEGY_AGENT_NAME = "StrategyAgent"
# AGENTS = list(MAP_NAME_ANALYST.keys()) + [
#     TRADING_AGENTS_NAME,
#     RESEARCH_AGENT_NAME,
#     AUTO_TRADING_AGENT_NAME,
# ]
AGENTS = [
    RESEARCH_AGENT_NAME,
    AUTO_TRADING_AGENT_NAME,
    NEWS_AGENT_NAME,
    STRATEGY_AGENT_NAME,
]

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
PYTHON_DIR = PROJECT_DIR / "python"
ENV_PATH = get_system_env_path()

# Convert paths to POSIX format (forward slashes) for cross-platform compatibility
# as_posix() works on both Windows and Unix systems
PROJECT_DIR_STR = PROJECT_DIR.as_posix()
PYTHON_DIR_STR = PYTHON_DIR.as_posix()
# Quote path to handle spaces (e.g., macOS Application Support)
ENV_PATH_STR = f'"{ENV_PATH.as_posix()}"'

AUTO_TRADING_ENV_OVERRIDES = {
    "AUTO_TRADING_EXCHANGE": os.getenv("AUTO_TRADING_EXCHANGE"),
}
AUTO_TRADING_ENV_PREFIX = " ".join(
    f"{key}={value}"
    for key, value in AUTO_TRADING_ENV_OVERRIDES.items()
    if value not in (None, "")
)
if AUTO_TRADING_ENV_PREFIX:
    AUTO_TRADING_ENV_PREFIX = f"{AUTO_TRADING_ENV_PREFIX} "

# Mapping from agent name to launch command
MAP_NAME_COMMAND: Dict[str, str] = {}
# Remove external agent entries
# for name, analyst in MAP_NAME_ANALYST.items():
#     MAP_NAME_COMMAND[name] = (
#         f"uv run --env-file {ENV_PATH_STR} -m adapter --analyst {analyst}"
#     )
# MAP_NAME_COMMAND[TRADING_AGENTS_NAME] = (
#     f"uv run --env-file {ENV_PATH_STR} -m adapter"
# )
# Keep only first-party agents
MAP_NAME_COMMAND[RESEARCH_AGENT_NAME] = (
    f"uv run --env-file {ENV_PATH_STR} -m valuecell.agents.research_agent"
)
MAP_NAME_COMMAND[AUTO_TRADING_AGENT_NAME] = (
    f"{AUTO_TRADING_ENV_PREFIX}uv run --env-file {ENV_PATH_STR} -m valuecell.agents.auto_trading_agent"
)
MAP_NAME_COMMAND[NEWS_AGENT_NAME] = (
    f"uv run --env-file {ENV_PATH_STR} -m valuecell.agents.news_agent"
)
MAP_NAME_COMMAND[STRATEGY_AGENT_NAME] = (
    f"uv run --env-file {ENV_PATH_STR} -m valuecell.agents.strategy_agent"
)
BACKEND_COMMAND = f"uv run --env-file {ENV_PATH_STR} -m valuecell.server.main"
FRONTEND_URL = "http://localhost:1420"


def check_envfile_is_set():
    if not ENV_PATH.exists():
        # Attempt to create system .env from repository example
        example = PROJECT_DIR / ".env.example"
        if example.exists():
            try:
                import shutil

                ensure_system_env_dir()
                shutil.copy(example, ENV_PATH)
                print(f"Created system .env from example: {ENV_PATH}")
            except Exception as e:
                print(f"Failed to create system .env from example: {e}")
        # Re-check after attempt
        if not ENV_PATH.exists():
            print(
                f"System .env not found at {ENV_PATH}. Please create it with necessary environment variables. "
                "System paths — macOS: ~/Library/Application Support/ValueCell/.env; Linux: ~/.config/valuecell/.env; Windows: %APPDATA%\\ValueCell\\.env."
            )
            exit(1)


def main():
    check_envfile_is_set()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    log_dir = f"{PROJECT_DIR_STR}/logs/{timestamp}"

    # Use questionary multi-select to allow choosing multiple agents
    # selected_agents = questionary.checkbox(
    #     "Choose agents to launch (use space to select, enter to confirm):",
    #     choices=AGENTS,
    # ).ask()
    selected_agents = AGENTS

    if not selected_agents:
        print("No agents selected.")
        exit(1)

    os.makedirs(log_dir, exist_ok=True)
    print(f"Logs will be saved to {log_dir}/")

    # processes = []
    logfiles = []

    print(
        "Agents are now managed in-process by RemoteConnections; external processes are no longer started."
    )

    # Launch backend
    logfile_path = f"{log_dir}/backend.log"
    print(f"Starting backend - output to {logfile_path}")
    print(f"Frontend available at {FRONTEND_URL}")
    logfile = open(logfile_path, "w")
    logfiles.append(logfile)
    # Start the backend in a new process group so we can terminate children.
    # On Windows use CREATE_NEW_PROCESS_GROUP; on POSIX use start_new_session.
    process = subprocess.Popen(
        shlex.split(BACKEND_COMMAND),
        shell=False,
        stdout=logfile,
        stderr=logfile,
        cwd=PYTHON_DIR_STR,
        creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0),
        start_new_session=(os.name == "posix"),
    )
    # processes.append(process)
    # for process in processes:
    #     process.wait()
    print(f"Backend (and agents) started with PID: {process.pid}")

    try:
        process.wait()
    except KeyboardInterrupt:
        print("\nStopping backend...")

        # Attempt graceful termination of the whole process group.
        try:
            if os.name == "posix":
                # send SIGTERM to the process group
                os.killpg(process.pid, signal.SIGTERM)
            else:
                # Windows: try to send CTRL_BREAK to the process group
                try:
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                except Exception:
                    process.terminate()
        except Exception:
            # Fallback to terminating the parent process
            try:
                process.terminate()
            except Exception:
                pass

        # Wait briefly for graceful shutdown
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Force kill the whole group if still alive
            try:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
            print("Backend forced killed.")

    for logfile in logfiles:
        logfile.close()
    print(f"All agents finished. Check {log_dir}/ for output.")


if __name__ == "__main__":
    main()
