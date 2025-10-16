import os

from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.vectordb.lancedb import LanceDb
from agno.vectordb.search import SearchType

from valuecell.utils.db import resolve_lancedb_uri

# embedder = SentenceTransformerEmbedder(id="all-MiniLM-L6-v2", dimensions=384)
# reranker = SentenceTransformerReranker(model="BAAI/bge-reranker-v2-m3", top_n=8)
# embedder = GeminiEmbedder(id="gemini-embedding-001", dimensions=1536)
embedder = OpenAIEmbedder(
    dimensions=int(os.getenv("EMBEDDER_DIMENSION", 1536)),
    id=os.getenv("EMBEDDER_MODEL"),
    base_url=os.getenv("EMBEDDER_BASE_URL"),
    api_key=os.getenv("EMBEDDER_API_KEY"),
)


vector_db = LanceDb(
    table_name="research_agent_knowledge_base",
    uri=resolve_lancedb_uri(),
    embedder=embedder,
    # reranker=reranker,
    search_type=SearchType.hybrid,
    use_tantivy=False,
)
