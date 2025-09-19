"""Example usage of i18n for Agent communication in ValueCell."""

# TODO: This file is a temporary file, it will be removed in the future.
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the parent directory to Python path to enable imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# Set environment for example
os.environ["LANG"] = "zh-Hans"
os.environ["TIMEZONE"] = "Asia/Shanghai"

try:
    from valuecell.services.agent_context import (
        get_agent_context,
        get_current_user_id,
        get_i18n_context,
        t,
    )
    from valuecell.api.i18n_api import get_i18n_api
    from valuecell.config.settings import get_settings
except ImportError as e:
    print(f"Import error: {e}")
    print("Please make sure you're running this from the correct directory.")
    sys.exit(1)


class ExampleAgent:
    """Example agent that uses i18n context."""

    def __init__(self, name: str):
        """Initialize agent."""
        self.name = name
        self.agent_context = get_agent_context()

    def process_user_request(self, user_id: str, request: str) -> str:
        """Process user request with user's i18n context."""
        # Set user context for this agent
        self.agent_context.set_user_context(user_id)

        # Get user's i18n context
        context = self.agent_context.get_i18n_context()

        # Use user's language for responses
        welcome = self.agent_context.translate("messages.welcome")
        processing = self.agent_context.translate("common.loading")

        # Format current time in user's timezone
        now = datetime.now()
        formatted_time = self.agent_context.format_datetime(now)

        # Format some numbers
        sample_amount = 1234.56
        formatted_currency = self.agent_context.format_currency(sample_amount)

        response = f"""
{self.name} Agent Response:
{welcome}
{processing}

Request: {request}
Current time: {formatted_time}
Sample amount: {formatted_currency}
User language: {context.language}
User timezone: {context.timezone}
"""
        return response.strip()

    def batch_process_users(self, user_requests: dict) -> dict:
        """Process requests for multiple users with their respective contexts."""
        results = {}

        for user_id, request in user_requests.items():
            # Use context manager for temporary user context
            with self.agent_context.user_context(user_id):
                # All operations within this block use the specific user's i18n settings
                welcome = t("messages.welcome")
                success = t("messages.data_saved")

                # Format data for this user
                now = datetime.now()
                formatted_time = self.agent_context.format_datetime(now, "time")

                results[user_id] = {
                    "agent": self.name,
                    "welcome": welcome,
                    "status": success,
                    "time": formatted_time,
                    "language": self.agent_context.get_current_language(),
                    "timezone": self.agent_context.get_current_timezone(),
                    "response": f"Processed: {request}",
                }

        return results


def setup_test_users():
    """Setup test users with different i18n preferences."""
    i18n_api = get_i18n_api()

    # User 1: English (US)
    i18n_api.set_user_context(
        "user1", {"language": "en-US", "timezone": "America/New_York"}
    )

    # User 2: Chinese (Simplified)
    i18n_api.set_user_context(
        "user2", {"language": "zh-Hans", "timezone": "Asia/Shanghai"}
    )

    # User 3: Chinese (Traditional - Hong Kong)
    i18n_api.set_user_context(
        "user3", {"language": "zh-Hant", "timezone": "Asia/Hong_Kong"}
    )

    # User 4: English (UK)
    i18n_api.set_user_context(
        "user4", {"language": "en-GB", "timezone": "Europe/London"}
    )


def main():
    """Main example function."""
    print("=== ValueCell Agent i18n Example ===\n")

    # Setup test users
    setup_test_users()

    # Create example agents
    financial_agent = ExampleAgent("Financial")
    portfolio_agent = ExampleAgent("Portfolio")

    print("1. Single User Processing:")
    print("-" * 50)

    # Process request for each user
    users = ["user1", "user2", "user3", "user4"]
    for user_id in users:
        response = financial_agent.process_user_request(
            user_id, "Show me my portfolio performance"
        )
        print(f"\n{user_id.upper()}:")
        print(response)

    print("\n" + "=" * 60)
    print("2. Batch Processing with Context Management:")
    print("-" * 50)

    # Batch process multiple users
    user_requests = {
        "user1": "Calculate my returns",
        "user2": "分析我的投资组合",
        "user3": "顯示我的資產配置",
        "user4": "Update my risk profile",
    }

    results = portfolio_agent.batch_process_users(user_requests)

    for user_id, result in results.items():
        print(f"\n{user_id.upper()} Results:")
        for key, value in result.items():
            print(f"  {key}: {value}")

    print("\n" + "=" * 60)
    print("3. Agent Context Information:")
    print("-" * 50)

    # Show how agents can get user context
    agent_context = get_agent_context()

    for user_id in users:
        agent_context.set_user_context(user_id)
        context = get_i18n_context()

        print(f"\n{user_id.upper()} Context:")
        print(f"  Language: {context.language}")
        print(f"  Timezone: {context.timezone}")
        print(f"  Currency: {context.currency_symbol}")
        print(f"  Date Format: {context.date_format}")
        print(f"  Current User ID: {get_current_user_id()}")

    print("\n" + "=" * 60)
    print("4. API Integration Example:")
    print("-" * 50)

    # Show how to get configuration from API
    settings = get_settings()
    api_config = settings.get_api_config()
    i18n_config = settings.get_i18n_config()

    print("API Configuration:")
    for key, value in api_config.items():
        print(f"  {key}: {value}")

    print("\nI18n Configuration:")
    for key, value in i18n_config.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()
