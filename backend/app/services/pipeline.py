import os
from app.services.repository_scanner import RepositoryScanner
from app.services.file_reader import FileReader
from app.services.code_parser import CodeParser
from app.services.chunker import CodeChunker
from app.services.tokenizer_adapter import EmbeddingTokenizer
from app.services.python_code_splitter import PythonCodeSplitter
from app.services.indexer import Indexer
from app.services.embedding_generator import EmbeddingGenerator
from app.services.vector_store import VectorStore
from typing import List
from app.models.chunk import Chunk
from app.models.source_file import SourceFile

class AtlasPipeline:
    def __init__(self, max_tokens: int = 512):
        self.scanner = RepositoryScanner()
        self.reader = FileReader()
        self.parser = CodeParser()
        self.tokenizer = EmbeddingTokenizer()
        self.splitter = PythonCodeSplitter(self.tokenizer, max_tokens=max_tokens, overlap_lines=3)
        self.chunker = CodeChunker(include_class_context=True, splitter=self.splitter)

        self.embedder = EmbeddingGenerator()
        self.vector_store = VectorStore()
        self.indexer = Indexer(embedder=self.embedder, vector_store=self.vector_store)

    def _process_file(self, meta, repo_path: str) -> List[Chunk]:
        """Read, parse, and chunk a single file, scoped to repo_path."""
        sf = SourceFile.from_reader(self.reader, meta, repo_path)
        content = sf.get_content()
        if content is None:
            return []
        parsed = self.parser.parse_file(content, sf.path)
        if not parsed:
            return []
        chunks = self.chunker.chunk_file(parsed, repo_path)
        for chunk in chunks:
            chunk.metadata["last_modified"] = meta.last_modified
        return chunks

    def run(self, repo_path: str, lazy: bool = True) -> List[Chunk]:
        """Scan, parse, and chunk every file. Does not embed or store."""
        repo_path = os.path.abspath(repo_path)
        print(f"Scanning {repo_path}...")
        files_meta = self.scanner.scan(repo_path)

        print(f"Creating lazy file references ({len(files_meta)} files)...")
        all_chunks = []
        for meta in files_meta:
            all_chunks.extend(self._process_file(meta, repo_path))

        print(f"Created {len(all_chunks)} chunks.")
        return all_chunks

    def index(self, repo_path: str) -> int:
        """
        Full pipeline: scan -> skip unchanged files -> parse -> chunk
        -> embed -> store. Only re-processes files that are new or whose
        last_modified time has advanced since the last index.

        repo_path is normalized to an absolute path and used to scope
        every read/write in the vector store, so this run never touches
        chunks belonging to a different repository you've indexed before.
        """
        repo_path = os.path.abspath(repo_path)
        print(f"Scanning {repo_path}...")
        files_meta = self.scanner.scan(repo_path)

        indexed_files = self.vector_store.get_indexed_files(repo_path)
        current_paths = {meta.path for meta in files_meta}

        # Clean up files that were indexed before (under this same repo_path)
        # but no longer exist
        removed_paths = set(indexed_files) - current_paths
        for path in removed_paths:
            self.vector_store.delete_by_file(path, repo_path)
        if removed_paths:
            print(f"Removed {len(removed_paths)} deleted file(s) from index.")

        all_chunks = []
        skipped = 0
        for meta in files_meta:
            prev_modified = indexed_files.get(meta.path)
            if (
                prev_modified is not None
                and meta.last_modified is not None
                and prev_modified >= meta.last_modified
            ):
                skipped += 1
                continue

            chunks = self._process_file(meta, repo_path)
            # Drop old chunks for this file first - handles renamed/removed
            # elements that would otherwise leave stale entries behind
            self.vector_store.delete_by_file(meta.path, repo_path)
            all_chunks.extend(chunks)

        print(f"{len(files_meta) - skipped} file(s) changed or new, {skipped} unchanged (skipped).")
        print(f"Created {len(all_chunks)} chunks.")

        total = self.indexer.index_chunks(all_chunks, repo_path)
        print(f"Indexing complete. This repo now has {total} chunks in the store.")
        return total