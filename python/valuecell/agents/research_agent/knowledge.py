from pathlib import Path
from typing import Optional

from agno.knowledge.chunking.markdown import MarkdownChunking
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.markdown_reader import MarkdownReader
from agno.knowledge.reader.pdf_reader import PDFReader
from loguru import logger

from .vdb import get_vector_db

_knowledge_cache: Optional[Knowledge] = None


def get_knowledge() -> Optional[Knowledge]:
    """Lazily create and cache the Knowledge instance.

    Returns None when embeddings/vector DB are unavailable, enabling a
    tools-only mode without knowledge search.
    """
    global _knowledge_cache
    if _knowledge_cache is not None:
        return _knowledge_cache

    vdb = get_vector_db()
    if vdb is None:
        logger.warning(
            "ResearchAgent Knowledge disabled: vector DB unavailable (no embeddings)."
        )
        return None

    try:
        _knowledge_cache = Knowledge(
            vector_db=vdb,
            max_results=10,
        )
        return _knowledge_cache
    except Exception as e:
        logger.warning(
            "Failed to create Knowledge for ResearchAgent; disabling. Error: {}",
            e,
        )
        return None


md_reader = MarkdownReader(chunking_strategy=MarkdownChunking())
pdf_reader = PDFReader(chunking_strategy=MarkdownChunking())


async def insert_md_file_to_knowledge(
    name: str, path: Path, metadata: Optional[dict] = None
):
    knowledge = get_knowledge()
    if knowledge is None:
        logger.warning(
            "Skipping markdown insertion: Knowledge disabled (no embeddings configured)."
        )
        return
    await knowledge.add_content_async(
        name=name,
        path=path,
        metadata=metadata,
        reader=md_reader,
    )


async def insert_pdf_file_to_knowledge(url: str, metadata: Optional[dict] = None):
    knowledge = get_knowledge()
    if knowledge is None:
        logger.warning(
            "Skipping PDF insertion: Knowledge disabled (no embeddings configured)."
        )
        return
    await knowledge.add_content_async(
        url=url,
        metadata=metadata,
        reader=pdf_reader,
    )
