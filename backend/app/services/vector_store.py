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

    def query(self, query_embedding: List[float], top_k: int = 5,
              repo_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find the top_k most similar chunks to a query embedding.

        Args:
            repo_path: if given, only search chunks from this repository.
                Without it, the query runs across every repo ever indexed
                into this store, which will surface unrelated results from
                other projects you've previously indexed.

        Returns:
            List of dicts with chunk_id, content, metadata, and distance.
        """
        where = {"repo_path": repo_path} if repo_path else None

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
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

    def delete_by_file(self, file_path: str, repo_path: Optional[str] = None) -> None:
        """
        Delete all chunks belonging to a given file (for re-indexing).

        repo_path scopes the delete to one repository. Without it, ANY
        repo that happens to have a file at this same relative path gets
        wiped too - always pass repo_path when re-indexing a specific repo.
        """
        if repo_path:
            self.collection.delete(where={"$and": [{"file_path": file_path}, {"repo_path": repo_path}]})
        else:
            self.collection.delete(where={"file_path": file_path})

    def delete_by_repo(self, repo_path: str) -> None:
        """Remove every chunk belonging to a given repository entirely."""
        self.collection.delete(where={"repo_path": repo_path})

    def get_indexed_files(self, repo_path: str) -> Dict[str, float]:
        """
        Return {file_path: last_modified} for every file currently
        indexed under a given repository, so the pipeline can skip
        re-indexing files that haven't changed since. Scoped to one
        repo_path - without this scoping, files from unrelated repos
        that happen to share a relative path would be compared as if
        they were the same file.
        """
        data = self.collection.get(where={"repo_path": repo_path}, include=["metadatas"])
        file_times: Dict[str, float] = {}
        for metadata in data.get("metadatas", []):
            file_path = metadata.get("file_path")
            last_modified = metadata.get("last_modified")
            if file_path is None or last_modified is None:
                continue
            if file_path not in file_times or last_modified > file_times[file_path]:
                file_times[file_path] = last_modified
        return file_times

    def count(self, repo_path: Optional[str] = None) -> int:
        if repo_path:
            data = self.collection.get(where={"repo_path": repo_path}, include=[])
            return len(data.get("ids", []))
        return self.collection.count()

    def _build_metadata(self, chunk: Chunk) -> Dict[str, Any]:
        """
        Flatten chunk metadata for Chroma, which requires primitive
        (str/int/float/bool) values only - no nested dicts or lists.
        """
        flat = {
            "file_path": chunk.file_path,
            "element_type": chunk.element_type,
            "name": chunk.name,
            "language": chunk.language,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
        }
        repo_path = chunk.metadata.get("repo_path")
        if repo_path:
            flat["repo_path"] = repo_path
        parent_class = chunk.metadata.get("parent_class")
        if parent_class:
            flat["parent_class"] = parent_class
        last_modified = chunk.metadata.get("last_modified")
        if last_modified is not None:
            flat["last_modified"] = last_modified
        return flat