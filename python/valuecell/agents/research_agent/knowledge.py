from pathlib import Path
from typing import Optional

from agno.knowledge.chunking.markdown import MarkdownChunking
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.markdown_reader import MarkdownReader

from .vdb import vector_db

knowledge = Knowledge(
    vector_db=vector_db,
    max_results=10,
)
md_reader = MarkdownReader(chunking_strategy=MarkdownChunking())


async def insert_md_file_to_knowledge(
    name: str, path: Path, metadata: Optional[dict] = None
):
    await knowledge.add_content_async(
        name=name,
        path=path,
        metadata=metadata,
        reader=md_reader,
    )
