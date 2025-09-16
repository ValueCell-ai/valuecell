from a2a.types import Task
from valuecell.core.session import get_default_session_manager, Role


async def store_task_in_session(task: Task) -> None:
    session_id = task.metadata.get("session_id")
    if not session_id:
        return

    session_manager = get_default_session_manager()
    if not task.artifacts:
        return
    if not task.artifacts[-1].parts:
        return
    content = task.artifacts[-1].parts[-1].root.text
    await session_manager.add_message(session_id, Role.AGENT, content)
