from dataclasses import dataclass, field
from typing import Optional, List
from services.file_reader import FileReader 
from services.respository_scanner import FileMetadata

@dataclass
class SourceFile:
    """Lightweight reference to a source file. Content is loaded lazily."""
    path: str
    name: str
    extension: str
    size: int
    encoding: str
    metadata: 'FileMetadata'          # from scanner
    _content: Optional[str] = field(default=None, repr=False)
    _reader: Optional['FileReader'] = field(default=None, repr=False)

    def get_content(self) -> str:
        """Lazy-load file content and cache it."""
        if self._content is None:
            if self._reader is None:
                raise ValueError("No FileReader assigned for lazy loading.")
            # Use the reader to read this file
            # We assume the reader has a method to read a specific file path
            self._content = self._reader.read_raw(self.path, self.encoding)
        return self._content

    @classmethod
    def from_reader(cls, reader: 'FileReader', file_metadata: 'FileMetadata',
                    base_path: str) -> 'SourceFile':
        """Create a SourceFile without loading content."""
        full_path = reader._resolve_path(file_metadata.path, base_path)
        return cls(
            path=file_metadata.path,
            name=file_metadata.name,
            extension=file_metadata.extension,
            size=file_metadata.size,
            encoding='utf-8',  # we'll detect later if needed
            metadata=file_metadata,
            _reader=reader
        )