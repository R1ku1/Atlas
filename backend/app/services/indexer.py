from typing import List
from app.models.chunk import Chunk
from app.services.embedding_generator import EmbeddingGenerator
from app.services.vector_store import VectorStore


class Indexer:
    """Embeds chunks and writes them to the vector store."""

    def __init__(self, embedder: EmbeddingGenerator = None, vector_store: VectorStore = None):
        self.embedder = embedder or EmbeddingGenerator()
        self.vector_store = vector_store or VectorStore()

    def index_chunks(self, chunks: List[Chunk]) -> int:
        """
        Embed and store a list of chunks.

        Returns:
            Total number of chunks now in the vector store.
        """
        if not chunks:
            return self.vector_store.count()

        print(f"Embedding {len(chunks)} chunks...")
        embeddings = self.embedder.embed_chunks(chunks)
        failed = len(chunks) - len(embeddings)
        print(f"Generated {len(embeddings)} embeddings ({failed} failed).")

        print("Writing to vector store...")
        self.vector_store.add(chunks, embeddings)

        return self.vector_store.count()