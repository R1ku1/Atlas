from typing import List, Dict, Any, Optional
from app.services.embedding_generator import EmbeddingGenerator
from app.services.vector_store import VectorStore


class SearchService:
    """Semantic search over indexed code chunks."""

    def __init__(self, embedder: EmbeddingGenerator = None, vector_store: VectorStore = None):
        self.embedder = embedder or EmbeddingGenerator()
        self.vector_store = vector_store or VectorStore()

    def search(self, query: str, top_k: int = 5, repo_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search indexed chunks by natural language query.

        Args:
            repo_path: scopes the search to one repository. If omitted,
                the search runs across every repo ever indexed into this
                store - only leave it out deliberately.

        Returns:
            List of dicts: chunk_id, content, metadata, distance - sorted
            by relevance (lowest distance first, as returned by Chroma).
        """
        query_embedding = self.embedder.embed_query(query)
        return self.vector_store.query(query_embedding, top_k=top_k, repo_path=repo_path)