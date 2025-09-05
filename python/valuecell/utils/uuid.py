from uuid import uuid4


def generate_uuid(prefix: str = None) -> str:
    if not prefix:
        return str(uuid4().hex)

    return f"{prefix}-{uuid4().hex}"
