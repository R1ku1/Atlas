from backend.app.services.repository_scanner import RepositoryScanner
from services.file_reader import FileReader
from services.code_parser import CodeParser
from services.chunker import CodeChunker
from services.chunk_enricher import ChunkEnricher
from services.python_code_splitter import PythonCodeSplitter
from services.tokenizer_adapter import EmbeddingTokenizer
from typing import List
from models.chunk import Chunk
from models.code_elements import ParsedFile
from services.file_reader import SourceFile


class AtlasPipeline:
    def __init__(self, max_chunk_tokens: int = 512):
        self.scanner = RepositoryScanner()
        self.reader = FileReader()
        self.parser = CodeParser()
        self.chunker = CodeChunker(include_class_context=True)
        self.tokenizer = EmbeddingTokenizer()
        self.splitter = PythonCodeSplitter(self.tokenizer, max_tokens=max_chunk_tokens)
        self.enricher = ChunkEnricher()

    def run(self, repo_path: str, lazy: bool = True) -> List[Chunk]:
        """Process a repo: scan -> parse -> split -> chunk -> enrich."""
        print(f"Scanning {repo_path}...")
        files_meta = self.scanner.scan(repo_path)

        print(f"Creating lazy file references ({len(files_meta)} files)...")
        source_files = []
        for meta in files_meta:
            sf = SourceFile.from_reader(self.reader, meta, repo_path)
            source_files.append(sf)

        all_chunks = []
        for sf in source_files:
            # Lazy-load content only when needed for parsing
            content = sf.get_content()
            parsed = self.parser.parse_file(content, sf.path)
            if not parsed:
                continue

            # Split any oversized functions/methods before chunking, so no
            # single chunk blows past the embedding model's token limit
            self._split_oversized_elements(parsed)

            chunks = self.chunker.chunk_file(parsed)

            # Enrich each chunk with file/class-level context
            enriched_chunks = [self.enricher.enrich(c, parsed) for c in chunks]

            all_chunks.extend(enriched_chunks)

        print(f"Created {len(all_chunks)} chunks.")
        return all_chunks

    def _split_oversized_elements(self, parsed: ParsedFile) -> None:
        """Replace functions/methods exceeding the token limit with split segments."""
        if parsed.language != "python":
            return  # splitter is python-specific for now

        new_functions = []
        for func in parsed.functions:
            new_functions.extend(self.splitter.split(func))
        parsed.functions = new_functions

        new_methods = []
        for method in parsed.methods:
            new_methods.extend(self.splitter.split(method))
        parsed.methods = new_methods