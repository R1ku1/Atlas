from app.services.repository_scanner import RepositoryScanner
from app.services.file_reader import FileReader
from app.services.code_parser import CodeParser
from app.services.chunker import CodeChunker
from app.services.chunk_enricher import ChunkEnricher
from app.services.python_code_splitter import PythonCodeSplitter
from app.services.tokenizer_adapter import EmbeddingTokenizer
from app.services.embedding_generator import EmbeddingGenerator
from app.services.vector_store import VectorStore
from typing import List
from models.chunk import Chunk
from models.code_elements import ParsedFile
from app.models.source_file import SourceFile


class AtlasPipeline:
    def __init__(
        self,
        max_chunk_tokens: int = 512,
        persist_path: str = "./chroma",
        embedding_model: str = "nomic-embed-text",
    ):
        self.scanner = RepositoryScanner()
        self.reader = FileReader()
        self.parser = CodeParser()
        self.chunker = CodeChunker(include_class_context=True)
        self.tokenizer = EmbeddingTokenizer()
        self.splitter = PythonCodeSplitter(self.tokenizer, max_tokens=max_chunk_tokens)
        self.enricher = ChunkEnricher()
        self.embedder = EmbeddingGenerator(model=embedding_model)
        self.vector_store = VectorStore(persist_path=persist_path)

    def run(self, repo_path: str, lazy: bool = True) -> List[Chunk]:
        """Process a repo: scan -> parse -> split -> chunk -> enrich."""
        print(f"Scanning {repo_path}...")
        files_meta = self.scanner.scan(repo_path)

        print(f"Creating lazy file references ({len(files_meta)} files)...")
        source_files = [SourceFile.from_reader(self.reader, meta, repo_path) for meta in files_meta]

        all_chunks = []
        for sf in source_files:
            content = sf.get_content()
            parsed = self.parser.parse_file(content, sf.path)
            if not parsed:
                continue

            self._split_oversized_elements(parsed)
            chunks = self.chunker.chunk_file(parsed)
            enriched_chunks = [self.enricher.enrich(c, parsed) for c in chunks]
            all_chunks.extend(enriched_chunks)

        print(f"Created {len(all_chunks)} chunks.")
        return all_chunks

    def index(self, repo_path: str) -> int:
        """Run the full pipeline and persist embeddings to the vector store."""
        chunks = self.run(repo_path)

        print(f"Embedding {len(chunks)} chunks...")
        embeddings = self.embedder.embed_chunks(chunks)
        print(f"Generated {len(embeddings)} embeddings ({len(chunks) - len(embeddings)} failed).")

        print("Writing to vector store...")
        self.vector_store.add(chunks, embeddings)

        total = self.vector_store.count()
        print(f"Indexing complete. Vector store now has {total} chunks.")
        return total

    def _split_oversized_elements(self, parsed: ParsedFile) -> None:
        if parsed.language != "python":
            return
        parsed.functions = [seg for f in parsed.functions for seg in self.splitter.split(f)]
        parsed.methods = [seg for m in parsed.methods for seg in self.splitter.split(m)]