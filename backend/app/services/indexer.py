from typing import List, Optional
from app.models.chunk import Chunk
from app.services.embedding_generator import EmbeddingGenerator
from app.services.vector_store import VectorStore


class Indexer:
    """Embeds chunks and writes them to the vector store."""

    def __init__(self, embedder: EmbeddingGenerator = None, vector_store: VectorStore = None):
        self.embedder = embedder or EmbeddingGenerator()
        self.vector_store = vector_store or VectorStore()

    def index_chunks(self, chunks: List[Chunk], repo_path: Optional[str] = None) -> int:
        """
        Embed and store a list of chunks.

        Args:
            repo_path: if given, the returned count is scoped to this
                repo only. Without it, the count is the entire store
                (every repo ever indexed), which is rarely what a caller
                actually wants to display back to the user.

        Returns:
            Number of chunks now in the store (for repo_path if given,
            otherwise the whole store).
        """
        if not chunks:
            return self.vector_store.count(repo_path)

        chunks = self._dedupe_chunk_ids(chunks)

        print(f"Embedding {len(chunks)} chunks...")
        embeddings = self.embedder.embed_chunks(chunks)
        failed = len(chunks) - len(embeddings)
        print(f"Generated {len(embeddings)} embeddings ({failed} failed).")

        print("Writing to vector store...")
        self.vector_store.add(chunks, embeddings)

        return self.vector_store.count(repo_path)

    def _dedupe_chunk_ids(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Guard against chunk_id collisions reaching the vector store, which
        raises and aborts the whole batch. Should be rare now that chunk_id
        includes repo_path + start_line, but this keeps a single bad ID
        from discarding every other successfully-processed chunk in the run.
        """
        seen = {}
        deduped = []
        for chunk in chunks:
            if chunk.chunk_id in seen:
                prev = seen[chunk.chunk_id]
                print(
                    f"Warning: duplicate chunk_id {chunk.chunk_id} - "
                    f"keeping {prev.file_path}:{prev.name}, "
                    f"dropping {chunk.file_path}:{chunk.name}"
                )
                continue
            seen[chunk.chunk_id] = chunk
            deduped.append(chunk)
        return deduped