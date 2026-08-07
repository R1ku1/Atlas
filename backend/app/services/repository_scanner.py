import os
from pathlib import Path
from typing import List, Optional, Set
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FileMetadata:
    """Metadata for a scanned file."""
    path: str
    name: str
    extension: str
    size: int
    last_modified: Optional[float] = None
    
    @property
    def relative_path(self) -> str:
        """Get path relative to the scanned directory."""
        return self.path
    
    def __str__(self) -> str:
        return f"{self.name} ({self.extension}, {self._format_size()})"
    
    def _format_size(self) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.size < 1024.0:
                return f"{self.size:.1f} {unit}"
            self.size /= 1024.0
        return f"{self.size:.1f} TB"


class RepositoryScanner:
    # Directories to ignore
    DEFAULT_IGNORE: Set[str] = {
        ".git",
        "node_modules",
        "__pycache__",
        "venv",
        ".venv",
        "dist",
        "build",
        ".idea",
        ".vscode",
        "coverage",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        "eggs",
        ".eggs",
        "site-packages",
    }
    
    # File extensions to include
    SUPPORTED_EXTENSIONS: Set[str] = {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".hpp",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
        ".cs",
        ".vb",
        ".sql",
        ".sh",
        ".bash",
        ".zsh",
        ".yaml",
        ".yml",
        ".json",
        ".xml",
        ".toml",
        ".ini",
        ".cfg",
        ".md",
        ".rst",
        ".txt",
        ".html",
        ".css",
        ".scss",
        ".sass",
    }
    
    def __init__(
        self,
        ignore_patterns: Optional[Set[str]] = None,
        supported_extensions: Optional[Set[str]] = None,
        max_file_size: Optional[int] = None,  # in bytes
        recursive: bool = True
    ):
        """
        Initialize the scanner with custom configurations.
        
        Args:
            ignore_patterns: Directories/files to ignore (uses DEFAULT_IGNORE if None)
            supported_extensions: File extensions to include (uses SUPPORTED_EXTENSIONS if None)
            max_file_size: Maximum file size in bytes (None for no limit)
            recursive: Whether to scan subdirectories
        """
        self.ignore_patterns = ignore_patterns or self.DEFAULT_IGNORE
        self.supported_extensions = supported_extensions or self.SUPPORTED_EXTENSIONS
        self.max_file_size = max_file_size
        self.recursive = recursive
    
    def scan(self, path: str) -> List[FileMetadata]:
        """
        Scan a repository and return metadata for all matching files.
        
        Args:
            path: Root directory to scan
            
        Returns:
            List of FileMetadata objects
            
        Raises:
            FileNotFoundError: If path doesn't exist
            NotADirectoryError: If path is not a directory
        """
        path = os.path.abspath(path)
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Path does not exist: {path}")
        
        if not os.path.isdir(path):
            raise NotADirectoryError(f"Path is not a directory: {path}")
        
        files = []
        
        if self.recursive:
            files = self._scan_recursive(path)
        else:
            files = self._scan_single_level(path)
        
        # Sort by name for consistent ordering
        files.sort(key=lambda f: f.path)
        
        return files
    
    def _scan_recursive(self, root_path: str) -> List[FileMetadata]:
        """Recursively scan directory tree."""
        files = []
        
        for current_dir, dirs, filenames in os.walk(root_path):
            # Filter out ignored directories in-place
            dirs[:] = [d for d in dirs if d not in self.ignore_patterns]
            
            for filename in filenames:
                file_path = os.path.join(current_dir, filename)
                metadata = self._process_file(file_path, root_path)
                if metadata:
                    files.append(metadata)
        
        return files
    
    def _scan_single_level(self, root_path: str) -> List[FileMetadata]:
        """Scan only the top-level directory."""
        files = []
        
        for entry in os.listdir(root_path):
            full_path = os.path.join(root_path, entry)
            if os.path.isfile(full_path):
                metadata = self._process_file(full_path, root_path)
                if metadata:
                    files.append(metadata)
        
        return files
    
    def _process_file(self, file_path: str, root_path: str) -> Optional[FileMetadata]:
        """
        Process a single file and return metadata if it passes filters.
        
        Args:
            file_path: Absolute path to the file
            root_path: Root directory being scanned
            
        Returns:
            FileMetadata if file passes all filters, None otherwise
        """
        # Check extension
        _, extension = os.path.splitext(file_path)
        if extension.lower() not in self.supported_extensions:
            return None
        
        try:
            # Get file stats
            stat = os.stat(file_path)
            file_size = stat.st_size
            
            # Check file size limit
            if self.max_file_size and file_size > self.max_file_size:
                return None
            
            # Create metadata
            relative_path = os.path.relpath(file_path, root_path)
            
            return FileMetadata(
                path=relative_path,
                name=os.path.basename(file_path),
                extension=extension.lower(),
                size=file_size,
                last_modified=stat.st_mtime
            )
            
        except (OSError, IOError) as e:
            # Skip files we can't access
            print(f"Warning: Could not process {file_path}: {e}")
            return None
    
    def get_file_count_by_extension(self, path: str) -> dict:
        """
        Get count of files grouped by extension.
        
        Args:
            path: Root directory to scan
            
        Returns:
            Dictionary mapping extensions to file counts
        """
        files = self.scan(path)
        extension_counts = {}
        
        for file in files:
            ext = file.extension
            extension_counts[ext] = extension_counts.get(ext, 0) + 1
        
        return dict(sorted(extension_counts.items()))
    
    def get_total_size(self, path: str) -> int:
        """
        Get total size of all matched files in bytes.
        
        Args:
            path: Root directory to scan
            
        Returns:
            Total size in bytes
        """
        files = self.scan(path)
        return sum(file.size for file in files)


# Usage example
if __name__ == "__main__":
    scanner = RepositoryScanner()
    
    try:
        # Scan a repository
        files = scanner.scan("/path/to/your/project")
        
        print(f"Found {len(files)} files:")
        for file in files:
            print(f"  {file}")
        
        # Get statistics
        print("\nFiles by extension:")
        for ext, count in scanner.get_file_count_by_extension("/path/to/your/project").items():
            print(f"  {ext}: {count}")
        
        print(f"\nTotal size: {scanner.get_total_size('/path/to/your/project')} bytes")
        
    except Exception as e:
        print(f"Error: {e}")