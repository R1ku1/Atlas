from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class Chunk:
    """A single chunk of code ready for embedding."""
    chunk_id: str                           # unique ID (e.g., "file:class.method")
    content: str                            # the actual source code of this chunk
    start_line: int
    end_line: int
    element_type: str                       # "class", "function", "method", etc.
    name: str                               # element name
    file_path: str                          # relative file path
    language: str                           # programming language
    metadata: Dict[str, Any] = field(default_factory=dict)  # e.g., parent class, signature, etc.