from abc import ABC, abstractmethod
from typing import Optional, Dict
from pathlib import Path
from app.models.code_elements import ParsedFile

class BaseParser(ABC):
    """Interface for all language-specific parsers."""
    
    @abstractmethod
    def parse(self, source_code: str, file_path: str) -> ParsedFile:
        """Parse source code into a ParsedFile."""
        pass
    
    @abstractmethod
    def get_language(self) -> str:
        """Return the language this parser handles."""
        pass
    
    @staticmethod
    def detect_language(file_path: str) -> Optional[str]:
        """Map file extension to language key."""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            # ... add more as needed
        }
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext)