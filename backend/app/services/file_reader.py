import os
import chardet
from typing import Dict, Optional, List
from dataclasses import dataclass
from app.services.respository_scanner import FileMetadata


@dataclass
class SourceFile:
    """Represents a source file with its content and metadata."""
    path: str
    name: str
    extension: str
    content: str
    size: int
    encoding: str
    line_count: int
    metadata: FileMetadata
    
    def __str__(self) -> str:
        preview = self.content[:100].replace('\n', '\\n')
        return f"{self.name} ({self.line_count} lines, {self.encoding})"
    
    def get_lines(self) -> List[str]:
        """Return file content as list of lines."""
        return self.content.splitlines()
    
    def get_preview(self, lines: int = 10) -> str:
        """Get a preview of the file content."""
        content_lines = self.get_lines()
        return '\n'.join(content_lines[:lines])


class FileReader:
    """
    Reads source files and returns their content with metadata.
    
    Handles:
    - Multiple encodings (UTF-8, UTF-16, Latin-1, etc.)
    - Binary file detection
    - Large file handling
    - Encoding detection with chardet
    """
    
    # Common source code encodings to try
    ENCODINGS = ['utf-8', 'utf-16', 'latin-1', 'cp1252', 'ascii', 'iso-8859-1']
    
    # Maximum file size to read (10MB default)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(
        self,
        max_file_size: Optional[int] = None,
        default_encoding: str = 'utf-8',
        detect_encoding: bool = True,
        ignore_errors: bool = False
    ):
        """
        Initialize the file reader.
        
        Args:
            max_file_size: Maximum file size to read in bytes (None for default)
            default_encoding: Default encoding to try first
            detect_encoding: Whether to use chardet for encoding detection
            ignore_errors: Whether to ignore decoding errors
        """
        self.max_file_size = max_file_size or self.MAX_FILE_SIZE
        self.default_encoding = default_encoding
        self.detect_encoding = detect_encoding
        self.ignore_errors = ignore_errors
    
    def read(self, file_path: str, base_path: Optional[str] = None) -> Optional[SourceFile]:
        """
        Read a source file and return its content with metadata.
        
        Args:
            file_path: Path to the file (can be relative or absolute)
            base_path: Base directory for relative paths
            
        Returns:
            SourceFile object if successful, None otherwise
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is too large or appears to be binary
        """
        # Resolve full path
        full_path = self._resolve_path(file_path, base_path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {full_path}")
        
        if not os.path.isfile(full_path):
            raise ValueError(f"Path is not a file: {full_path}")
        
        # Check file size
        file_size = os.path.getsize(full_path)
        if file_size > self.max_file_size:
            raise ValueError(
                f"File too large: {full_path} ({self._format_size(file_size)})"
            )
        
        # Check if file is binary
        if self._is_binary(full_path):
            raise ValueError(f"File appears to be binary: {full_path}")
        
        # Detect encoding
        encoding = self._detect_encoding(full_path) if self.detect_encoding else self.default_encoding
        
        # Read file content
        content = self._read_content(full_path, encoding)
        
        if content is None:
            return None
        
        # Create metadata
        stat = os.stat(full_path)
        _, extension = os.path.splitext(full_path)
        
        metadata = FileMetadata(
            path=os.path.relpath(full_path, base_path) if base_path else full_path,
            name=os.path.basename(full_path),
            extension=extension.lower(),
            size=file_size,
            last_modified=stat.st_mtime
        )
        
        # Count lines
        line_count = content.count('\n') + (1 if content and not content.endswith('\n') else 0)
        
        return SourceFile(
            path=metadata.path,
            name=metadata.name,
            extension=metadata.extension,
            content=content,
            size=file_size,
            encoding=encoding,
            line_count=line_count,
            metadata=metadata
        )
    
    def read_batch(
        self,
        file_paths: List[str],
        base_path: Optional[str] = None
    ) -> List[SourceFile]:
        """
        Read multiple files.
        
        Args:
            file_paths: List of file paths to read
            base_path: Base directory for relative paths
            
        Returns:
            List of successfully read SourceFile objects
        """
        source_files = []
        errors = []
        
        for file_path in file_paths:
            try:
                source_file = self.read(file_path, base_path)
                if source_file:
                    source_files.append(source_file)
            except Exception as e:
                errors.append((file_path, str(e)))
        
        if errors:
            print(f"Warning: Failed to read {len(errors)} files:")
            for path, error in errors[:5]:  # Show first 5 errors
                print(f"  {path}: {error}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more errors")
        
        return source_files
    
    def read_from_metadata(
        self,
        files_metadata: List[FileMetadata],
        base_path: Optional[str] = None
    ) -> List[SourceFile]:
        """
        Read files from FileMetadata objects (from RepositoryScanner).
        
        Args:
            files_metadata: List of FileMetadata objects
            base_path: Base directory for resolving paths
            
        Returns:
            List of SourceFile objects
        """
        file_paths = [meta.path for meta in files_metadata]
        return self.read_batch(file_paths, base_path)
    
    def _resolve_path(self, file_path: str, base_path: Optional[str] = None) -> str:
        """Resolve file path, handling relative paths."""
        if os.path.isabs(file_path):
            return file_path
        
        if base_path:
            return os.path.join(base_path, file_path)
        
        return os.path.abspath(file_path)
    
    def _detect_encoding(self, file_path: str) -> str:
        """
        Detect file encoding using chardet.
        Falls back to default encoding if detection fails.
        """
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # Read first 10KB for detection
                
            result = chardet.detect(raw_data)
            
            if result['confidence'] > 0.7:
                return result['encoding']
            
        except Exception:
            pass
        
        return self.default_encoding
    
    def _read_content(self, file_path: str, encoding: str) -> Optional[str]:
        """
        Read file content with the specified encoding.
        Tries multiple encodings if the first one fails.
        """
        # Try the detected/specified encoding first
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            if not self.ignore_errors:
                # Try other encodings
                for enc in self.ENCODINGS:
                    if enc != encoding:
                        try:
                            with open(file_path, 'r', encoding=enc) as f:
                                return f.read()
                        except UnicodeDecodeError:
                            continue
                
                # Last resort: read with error handling
                if self.ignore_errors:
                    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                        return f.read()
        
        return None
    
    def _is_binary(self, file_path: str) -> bool:
        """
        Check if a file is binary by looking for null bytes.
        """
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\x00' in chunk
        except Exception:
            return True
    
    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


# Example usage and integration with RepositoryScanner
if __name__ == "__main__":
    from app.services.respository_scanner import RepositoryScanner
    
    # Initialize both services
    scanner = RepositoryScanner()
    reader = FileReader()
    
    # Scan repository
    repo_path = "/path/to/your/project"
    try:
        print(f"Scanning repository: {repo_path}")
        files_metadata = scanner.scan(repo_path)
        print(f"Found {len(files_metadata)} files")
        
        # Read all source files
        print("\nReading source files...")
        source_files = reader.read_from_metadata(files_metadata, repo_path)
        
        print(f"Successfully read {len(source_files)} files\n")
        
        # Display statistics
        total_lines = sum(f.line_count for f in source_files)
        total_size = sum(f.size for f in source_files)
        
        print(f"Statistics:")
        print(f"  Total files: {len(source_files)}")
        print(f"  Total lines: {total_lines:,}")
        print(f"  Total size: {reader._format_size(total_size)}")
        
        # Show first few files
        print(f"\nFirst 5 files:")
        for sf in source_files[:5]:
            print(f"  {sf}")
            print(f"    Preview: {sf.get_preview(3)}")
            print()
        
    except Exception as e:
        print(f"Error: {e}")