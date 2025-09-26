"""
Interactive agent launcher script.
Allows users to select an agent from available options and launch it using uv.
"""

import os
from pathlib import Path
import subprocess
from datetime import datetime
from typing import Dict

import questionary

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
SEC_AGENT_NAME = "SecAgent"
TRADING_AGENTS_NAME = "TradingAgentsAdapter"
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
PYTHON_DIR = PROJECT_DIR / "python"

# Mapping from agent name to launch command
MAP_NAME_COMMAND: Dict[str, str] = {}
for name, analyst in MAP_NAME_ANALYST.items():
    MAP_NAME_COMMAND[name] = (
        f"cd {PYTHON_DIR}/third_party/ai-hedge-fund && uv run python -m adapter --analyst {analyst}"
    )
MAP_NAME_COMMAND[SEC_AGENT_NAME] = "uv run -m valuecell.agents.sec_agent"
MAP_NAME_COMMAND[TRADING_AGENTS_NAME] = (
    f"cd {PYTHON_DIR}/third_party/TradingAgents && uv run -m adapter"
)


def check_envfile_is_set():
    env_path = PROJECT_DIR / ".env"
    if not env_path.exists():
        print(
            f".env file not found at {env_path}. Please create it with necessary environment variables. "
            "check python/.env.example for reference."
        )
        exit(1)


def main():
    check_envfile_is_set()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    log_dir = f"logs/{timestamp}"
    agents = list(MAP_NAME_COMMAND.keys())

    # Use questionary multi-select to allow choosing multiple agents
    selected_agents = questionary.checkbox(
        "Choose agents to launch (use space to select, enter to confirm):",
        choices=agents,
    ).ask()

    if not selected_agents:
        print("No agents selected.")
        exit(0)

    os.makedirs(log_dir, exist_ok=True)
    print(f"Logs will be saved to {log_dir}/")

    processes = []
    logfiles = []
    for selected_agent in selected_agents:
        logfile_path = f"{log_dir}/{selected_agent}.log"
        print(f"Starting agent: {selected_agent} - output to {logfile_path}")

        # Open logfile for writing
        logfile = open(logfile_path, "w")
        logfiles.append(logfile)

        # Launch command using Popen with output redirected to logfile
        launch_command = MAP_NAME_COMMAND[selected_agent]
        process = subprocess.Popen(
            launch_command, shell=True, stdout=logfile, stderr=logfile
        )
        processes.append(process)
    print("All agents launched. Waiting for tasks...")

    # Launch backend
    logfile_path = f"{log_dir}/backend.log"
    print(f"Starting backend - output to {logfile_path}")
    logfile = open(logfile_path, "w")
    logfiles.append(logfile)
    launch_command = f"cd {PYTHON_DIR} && uv run -m valuecell.server.main"
    process = subprocess.Popen(
        launch_command, shell=True, stdout=logfile, stderr=logfile
    )
    processes.append(process)

    for process in processes:
        process.wait()
    for logfile in logfiles:
        logfile.close()
    print(f"All agents finished. Check {log_dir}/ for output.")


if __name__ == "__main__":
    main()
