#!/usr/bin/env python3
"""
TradingAgents Adapter Startup Script

This script is used to start the TradingAgents adapter service, allowing it to be accessed by the valuecell core agent system.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project path to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Add valuecell path
valuecell_root = project_root.parent.parent / "valuecell"
sys.path.insert(0, str(valuecell_root))

from valuecell.core.agent.decorator import create_wrapped_agent
from adapter.__main__ import TradingAgents

# Set logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_environment():
    """Set environment variables"""
    # Set default port
    if not os.getenv("AGENT_PORT"):
        os.environ["AGENT_PORT"] = "10002"
    
    # Set project directory
    os.environ["TRADINGAGENTS_PROJECT_DIR"] = str(project_root)
    
    logger.info(f"Agent will start on port {os.getenv('AGENT_PORT', '10002')}")
    logger.info(f"Project directory: {project_root}")


async def main():
    try:
        setup_environment()
        
        logger.info("🚀 Starting TradingAgents ...")
        
        # Create and start agent
        agent = create_wrapped_agent(TradingAgents)
        await agent.serve()
        
    except KeyboardInterrupt:
        logger.info("👋 Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"❌ Failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
