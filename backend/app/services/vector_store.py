import chromadb
from typing import List, Tuple, Dict, Any, Optional
from app.models.chunk import Chunk


class VectorStore:
    """Wrapper around ChromaDB for storing and querying chunk embeddings."""

    def __init__(self, persist_path: str = "./chroma", collection_name: str = "atlas_chunks"):
        self.client = chromadb.PersistentClient(path=persist_path)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add(self, chunks: List[Chunk], embeddings: List[Tuple[str, List[float]]]) -> None:
        """
        Store chunks and their embeddings.

        Args:
            chunks: Original chunk objects (for metadata + content)
            embeddings: (chunk_id, vector) pairs from EmbeddingGenerator
        """
        chunk_by_id = {c.chunk_id: c for c in chunks}

        ids, vectors, documents, metadatas = [], [], [], []
        for chunk_id, vector in embeddings:
            chunk = chunk_by_id.get(chunk_id)
            if chunk is None:
                continue
            ids.append(chunk_id)
            vectors.append(vector)
            documents.append(chunk.content)
            metadatas.append(self._build_metadata(chunk))

        if not ids:
            return

        self.collection.upsert(
            ids=ids,
            embeddings=vectors,
            documents=documents,
            metadatas=metadatas,
        )

    def query(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find the top_k most similar chunks to a query embedding.

        Returns:
            List of dicts with chunk_id, content, metadata, and distance.
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        hits = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for chunk_id, content, metadata, distance in zip(ids, documents, metadatas, distances):
            hits.append({
                "chunk_id": chunk_id,
                "content": content,
                "metadata": metadata,
                "distance": distance,
            })
        return hits

    def delete_by_file(self, file_path: str) -> None:
        """Delete all chunks belonging to a given file (for re-indexing)."""
        self.collection.delete(where={"file_path": file_path})

    def count(self) -> int:
        return self.collection.count()

    def _build_metadata(self, chunk: Chunk) -> Dict[str, Any]:
        """
        Flatten chunk metadata for Chroma, which requires primitive
        (str/int/float/bool) values only — no nested dicts or lists.
        """
        flat = {
            "file_path": chunk.file_path,
            "element_type": chunk.element_type,
            "name": chunk.name,
            "language": chunk.language,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
        }
        parent_class = chunk.metadata.get("parent_class")
        if parent_class:
            flat["parent_class"] = parent_class
        return flat