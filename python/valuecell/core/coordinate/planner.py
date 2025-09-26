"""Planner: create execution plans from user input.

This module implements the ExecutionPlanner which uses an LLM-based
planning agent to convert a user request into a structured
`ExecutionPlan` consisting of `Task` objects. The planner supports
Human-in-the-Loop flows by emitting `UserInputRequest` objects (backed by
an asyncio.Event) when the planner requires clarification.

The planner is intentionally thin: it delegates reasoning to an AI agent
and performs JSON parsing/validation of the planner's output.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Callable, List, Optional

from a2a.types import AgentCard
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.tools.user_control_flow import UserControlFlowTools

from valuecell.core.agent.connect import RemoteConnections
from valuecell.core.coordinate.planner_prompts import (
    PLANNER_INSTRUCTIONS,
    create_prompt_with_datetime,
)
from valuecell.core.task import Task, TaskPattern, TaskStatus
from valuecell.core.types import UserInput
from valuecell.utils import generate_uuid

from .models import ExecutionPlan, PlannerInput, PlannerResponse

logger = logging.getLogger(__name__)


class UserInputRequest:
    """
    Represents a request for user input during plan creation or execution.

    This class uses asyncio.Event to enable non-blocking waiting for user responses
    in the Human-in-the-Loop workflow.
    """

    def __init__(self, prompt: str):
        """Create a new request object for planner-driven user input.

        Args:
            prompt: Human-readable prompt describing the information needed.
        """
        self.prompt = prompt
        self.response: Optional[str] = None
        self.event = asyncio.Event()

    async def wait_for_response(self) -> str:
        """Block until a response is provided and return it.

        This is an awaitable helper designed to be used by planner code that
        wants to pause execution until the external caller supplies the
        requested value via `provide_response`.
        """
        await self.event.wait()
        return self.response

    def provide_response(self, response: str):
        """Supply the user's response and wake any waiter.

        Args:
            response: The text provided by the user to satisfy the prompt.
        """
        self.response = response
        self.event.set()


class ExecutionPlanner:
    """
    Creates execution plans by analyzing user input and determining appropriate agent tasks.

    This planner uses AI to understand user requests and break them down into
    executable tasks that can be handled by specific agents. It supports
    Human-in-the-Loop interactions when additional clarification is needed.
    """

    def __init__(
        self,
        agent_connections: RemoteConnections,
    ):
        self.agent_connections = agent_connections

    async def create_plan(
        self, user_input: UserInput, user_input_callback: Optional[Callable] = None
    ) -> ExecutionPlan:
        """
        Create an execution plan from user input.

        This method orchestrates the planning agent run and returns a
        validated `ExecutionPlan` instance. The optional `user_input_callback`
        is called whenever the planner requests clarification; the callback
        should accept a `UserInputRequest` and arrange for the user's answer to
        be provided (typically by calling `UserInputRequest.provide_response`).

        Args:
            user_input: The user's request to be planned.
            user_input_callback: Optional async callback invoked with
                `UserInputRequest` instances when clarification is required.

        Returns:
            ExecutionPlan: A structured plan with tasks for execution.
        """
        plan = ExecutionPlan(
            plan_id=generate_uuid("plan"),
            conversation_id=user_input.meta.conversation_id,
            user_id=user_input.meta.user_id,
            orig_query=user_input.query,  # Store the original query
            created_at=datetime.now().isoformat(),
        )

        # Analyze input and create appropriate tasks
        tasks = await self._analyze_input_and_create_tasks(
            user_input, user_input_callback
        )
        plan.tasks = tasks

        return plan

    async def _analyze_input_and_create_tasks(
        self, user_input: UserInput, user_input_callback: Optional[Callable] = None
    ) -> List[Task]:
        """
        Analyze user input and produce a list of `Task` objects.

        The planner delegates reasoning to an LLM agent which must output a
        JSON document conforming to `PlannerResponse`. If the planner pauses to
        request user input, the provided `user_input_callback` will be
        invoked for each requested field.

        Args:
            user_input: The original user input to analyze.
            user_input_callback: Optional async callback used for Human-in-the-Loop.

        Returns:
            A list of `Task` objects derived from the planner response.
        """
        # Create planning agent with appropriate tools and instructions
        agent = Agent(
            model=OpenRouter(
                id=os.getenv("PLANNER_MODEL_ID", "google/gemini-2.5-pro"),
                max_tokens=None,
            ),
            tools=[
                UserControlFlowTools(),
                self.tool_get_agent_description,
            ],
            markdown=False,
            debug_mode=os.getenv("AGENT_DEBUG_MODE", "false").lower() == "true",
            instructions=[
                create_prompt_with_datetime(PLANNER_INSTRUCTIONS),
            ],
        )

        # Execute planning with the agent
        run_response = agent.run(
            message=PlannerInput(
                desired_agent_name=user_input.desired_agent_name,
                query=user_input.query,
            )
        )

        # Handle user input requests through Human-in-the-Loop workflow
        while run_response.is_paused:
            for tool in run_response.tools_requiring_user_input:
                input_schema = tool.user_input_schema

                for field in input_schema:
                    if user_input_callback:
                        # Use callback for async user input
                        # TODO: prompt options if available
                        request = UserInputRequest(field.description)
                        await user_input_callback(request)
                        user_value = await request.wait_for_response()
                    else:
                        # Fallback to synchronous input for testing/simple scenarios
                        user_value = input(f"{field.description}: ")

                    field.value = user_value

            # Continue agent execution with updated inputs
            run_response = agent.continue_run(
                run_id=run_response.run_id, updated_tools=run_response.tools
            )

            if not run_response.is_paused:
                break

        # Parse planning result and create tasks
        try:
            plan_content = run_response.content
            if plan_content.startswith("```json\n") and plan_content.endswith("\n```"):
                # Strip markdown code block if present
                plan_content = "\n".join(plan_content.split("\n")[1:-1])
            plan_raw = PlannerResponse.model_validate_json(plan_content)
        except Exception as e:
            raise ValueError(
                f"Planner produced invalid JSON for PlannerResponse: {e}. "
                f"Raw content: {run_response.content}"
            ) from e
        logger.info(f"Planner produced plan: {plan_raw}")
        if not plan_raw.adequate or not plan_raw.tasks:
            # If information is still inadequate, return empty task list
            raise ValueError(
                "Planner indicated information is inadequate or produced no tasks."
                f" Reason: {plan_raw.reason}"
            )
        return [
            self._create_task(
                user_input.meta.conversation_id,
                user_input.meta.user_id,
                task.agent_name,
                task.query,
                task.pattern,
            )
            for task in plan_raw.tasks
        ]

    def _create_task(
        self,
        conversation_id: str,
        user_id: str,
        agent_name: str,
        query: str,
        pattern: TaskPattern = TaskPattern.ONCE,
    ) -> Task:
        """
        Create a new task for the specified agent.

        Args:
            conversation_id: Conversation this task belongs to
            user_id: User who requested this task
            agent_name: Name of the agent to execute the task
            query: Query/prompt for the agent
            pattern: Execution pattern (once or recurring)

        Returns:
            Task: Configured task ready for execution.
        """
        return Task(
            task_id=generate_uuid("task"),
            conversation_id=conversation_id,
            user_id=user_id,
            agent_name=agent_name,
            status=TaskStatus.PENDING,
            query=query,
            pattern=pattern,
        )

    def tool_get_agent_description(self, agent_name: str) -> str:
        """
        Get the capabilities description of a specified agent by name.

        This function returns capability information for agents that can be used
        in the planning process to determine if an agent is suitable for a task.

        Args:
            agent_name: The name of the agent whose capabilities are to be retrieved

        Returns:
            str: A description of the agent's capabilities and supported operations.
        """
        if card := self.agent_connections.get_agent_card(agent_name):
            if isinstance(card, AgentCard):
                return agentcard_to_prompt(card)
            if isinstance(card, dict):
                return str(card)
            return agentcard_to_prompt(card)

        return "The requested agent could not be found or is not available."


def agentcard_to_prompt(card: AgentCard):
    """Convert an AgentCard to an LLM-friendly prompt string.

    Args:
        card: The AgentCard object or JSON structure describing an agent.

    Returns:
        A formatted string suitable for inclusion in the planner's instructions.
    """

    # Start with basic agent information
    prompt = f"# Agent: {card.name}\n\n"

    # Add description
    prompt += f"**Description:** {card.description}\n\n"

    # Add skills section
    if card.skills:
        prompt += "## Available Skills\n\n"

        for i, skill in enumerate(card.skills, 1):
            prompt += f"### {i}. {skill.name} (`{skill.id}`)\n\n"
            prompt += f"**Description:** {skill.description}\n\n"

            # Add examples if available
            if skill.examples:
                prompt += "**Examples:**\n"
                for example in skill.examples:
                    prompt += f"- {example}\n"
                prompt += "\n"

            # Add tags if available
            if skill.tags:
                tags_str = ", ".join([f"`{tag}`" for tag in skill.tags])
                prompt += f"**Tags:** {tags_str}\n\n"

            # Add separator between skills (except for the last one)
            if i < len(card.skills):
                prompt += "---\n\n"

    return prompt.strip()
