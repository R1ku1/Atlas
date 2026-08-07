from abc import ABC, abstractmethod
from typing import List, Optional
from models.code_elements import CodeElement

class CodeSplitter(ABC):
    @abstractmethod
    def split(self, element: CodeElement) -> List[CodeElement]:
        """Split a code element into multiple elements if it exceeds token limit."""
        pass