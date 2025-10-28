from types import SimpleNamespace

from valuecell.core.plan.planner import ExecutionPlanner
from valuecell.core.task.models import TaskPattern


def _make_task_brief():
    return SimpleNamespace(
        agent_name="demo_agent",
        title="demo task",
        query="do something",
        pattern=TaskPattern.ONCE,
        schedule_config=None,
    )


def test_handoff_preserves_parent_thread_id_and_new_conversation_id():
    parent_conversation_id = "conv_parent"
    parent_thread_id = "thread_parent"

    # Bypass __init__ to avoid heavy dependencies in planner construction
    planner = ExecutionPlanner.__new__(ExecutionPlanner)

    tb = _make_task_brief()
    task = planner._create_task(
        tb,
        user_id="user-1",
        conversation_id=parent_conversation_id,
        thread_id=parent_thread_id,
        handoff_from_super_agent=True,
    )

    assert task.handoff_from_super_agent is True
    assert task.conversation_id != parent_conversation_id  # new sub-conversation
    assert task.thread_id == parent_thread_id  # Spec A: reuse parent thread


def test_no_handoff_keeps_conversation_and_thread():
    parent_conversation_id = "conv_parent"
    parent_thread_id = "thread_parent"

    planner = ExecutionPlanner.__new__(ExecutionPlanner)

    tb = _make_task_brief()
    task = planner._create_task(
        tb,
        user_id="user-1",
        conversation_id=parent_conversation_id,
        thread_id=parent_thread_id,
        handoff_from_super_agent=False,
    )

    assert task.handoff_from_super_agent is False
    assert task.conversation_id == parent_conversation_id
    assert task.thread_id == parent_thread_id
