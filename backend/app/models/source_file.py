from dataclasses import dataclass, field
from typing import Optional, List
from app.services.repository_scanner import FileMetadata
from services.file_reader import FileReader
import os

@dataclass
class SourceFile:
    """Represents a source file with optional lazy-loaded content."""
    path: str
    name: str
    extension: str
    size: int
    metadata: 'FileMetadata'
    
    # Content-related fields (can be None for lazy loading)
    content: Optional[str] = None
    encoding: Optional[str] = None
    line_count: Optional[int] = None
    
    # Internal fields for lazy loading
    _full_path: Optional[str] = field(default=None, repr=False)
    _reader: Optional['FileReader'] = field(default=None, repr=False)
    _content_loaded: bool = field(default=False, repr=False)
    
    def get_content(self) -> Optional[str]:
        """
        Get file content, loading it lazily if necessary.
        
        Returns:
            File content as string, or None if file couldn't be read
        """
        if self._content_loaded:
            return self.content
        
        if self._reader is None or self._full_path is None:
            raise ValueError("Cannot lazy-load content: no reader or path available")
        
        # Load content on demand
        if self.encoding is None:
            self.encoding = self._reader._detect_encoding(self._full_path)
        
        self.content = self._reader._read_content(self._full_path, self.encoding)
        
        if self.content is not None:
            self.line_count = self.content.count('\n') + (1 if self.content and not self.content.endswith('\n') else 0)
        
        self._content_loaded = True
        return self.content
    
    def get_lines(self) -> List[str]:
        """Return file content as list of lines."""
        content = self.get_content()
        return content.splitlines() if content else []
    
    def get_preview(self, lines: int = 10) -> str:
        """Get a preview of the file content."""
        content = self.get_content()
        if not content:
            return ""
        content_lines = content.splitlines()
        return '\n'.join(content_lines[:lines])
    
    def unload_content(self):
        """
        Free memory by unloading content.
        Useful when processing many files sequentially.
        """
        self.content = None
        self.line_count = None
        self._content_loaded = False
    
    def is_loaded(self) -> bool:
        """Check if content has been loaded."""
        return self._content_loaded and self.content is not None
    
    def __str__(self) -> str:
        status = "loaded" if self.is_loaded() else "lazy"
        if self.line_count:
            return f"{self.name} ({self.line_count} lines, {self.encoding}, {status})"
        return f"{self.name} ({self._format_size(self.size)}, {status})"
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    @classmethod
    def from_reader(cls, reader: 'FileReader', metadata: 'FileMetadata', base_path: str) -> 'SourceFile':
        """Build a lazy-loading SourceFile from scan metadata, without reading content yet."""
        full_path = os.path.join(base_path, metadata.path) if base_path else metadata.path
        return cls(
            path=metadata.path,
            name=metadata.name,
            extension=metadata.extension,
            size=metadata.size,
            metadata=metadata,
            content=None,
            encoding=None,
            line_count=None,
            _full_path=full_path,
            _reader=reader,
            _content_loaded=False,
        )