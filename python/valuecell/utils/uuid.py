from uuid import uuid4


def generate_uuid(prefix: str = None) -> str:
    if not prefix:
        return str(uuid4().hex)

    return f"{prefix}-{uuid4().hex}"


def generate_item_id() -> str:
    return generate_uuid("item")


def generate_thread_id() -> str:
    return generate_uuid("th")


def generate_conversation_id() -> str:
    return generate_uuid("conv")


def generate_task_id() -> str:
    return generate_uuid("task")
