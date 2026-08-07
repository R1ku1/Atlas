import requests
from typing import List, Tuple
from app.models.chunk import Chunk


class EmbeddingGenerator:
    """Generates embeddings for chunks using a local Ollama model."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        batch_size: int = 32,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.batch_size = batch_size

    def embed_chunks(self, chunks: List[Chunk]) -> List[Tuple[str, List[float]]]:
        """
        Generate embeddings for a list of chunks.

        Returns:
            List of (chunk_id, embedding_vector) pairs, in the same order
            as the input chunks (failed embeddings are skipped, not padded).
        """
        results = []
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i : i + self.batch_size]
            texts = [c.content for c in batch]
            vectors = self._embed_batch(texts)
            for chunk, vector in zip(batch, vectors):
                if vector is not None:
                    results.append((chunk.chunk_id, vector))
        return results

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        vectors = self._embed_batch([text])
        if not vectors or vectors[0] is None:
            raise RuntimeError("Failed to generate query embedding")
        return vectors[0]

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Call Ollama's embedding endpoint for each text.

        Note: Ollama's /api/embeddings endpoint takes one prompt at a time,
        so "batching" here just groups them for bookkeeping/print purposes —
        we still issue one request per text.
        """
        vectors = []
        for text in texts:
            try:
                response = requests.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
                vectors.append(data.get("embedding"))
            except requests.RequestException as e:
                print(f"Warning: embedding failed for a chunk: {e}")
                vectors.append(None)
        return vectors