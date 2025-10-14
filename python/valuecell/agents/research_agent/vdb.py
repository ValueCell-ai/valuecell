from agno.knowledge.embedder.sentence_transformer import SentenceTransformerEmbedder
from agno.knowledge.reranker.sentence_transformer import SentenceTransformerReranker
from agno.vectordb.lancedb import LanceDb
from agno.vectordb.search import SearchType

from valuecell.utils.db import resolve_lancedb_uri

embedder = SentenceTransformerEmbedder(id="all-mpnet-base-v2", dimensions=768)
reranker = SentenceTransformerReranker(model="BAAI/bge-reranker-v2-m3", top_n=8)

vector_db = LanceDb(
    table_name="research_agent_knowledge_base",
    uri=resolve_lancedb_uri(),
    embedder=embedder,
    reranker=reranker,
    search_type=SearchType.hybrid,
)
