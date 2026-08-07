from backend.app.services.repository_scanner import RepositoryScanner
from services.file_reader import FileReader
from services.code_parser import CodeParser
from services.chunker import CodeChunker
from typing import List
from models.chunk import Chunk
from services.file_reader import SourceFile

class AtlasPipeline:
    def __init__(self):
        self.scanner = RepositoryScanner()
        self.reader = FileReader()
        self.parser = CodeParser()
        self.chunker = CodeChunker(include_class_context=True)

    def run(self, repo_path: str, lazy: bool = True) -> List[Chunk]:
        """Process a repo and return all chunks."""
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
            content = sf.get_content()  # loads file from disk once
            parsed = self.parser.parse_file(content, sf.path)
            if parsed:
                chunks = self.chunker.chunk_file(parsed)
                all_chunks.extend(chunks)
        
        print(f"Created {len(all_chunks)} chunks.")
        return all_chunks