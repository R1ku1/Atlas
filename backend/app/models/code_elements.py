from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set


@dataclass
class CodeElement:
    """
    Represents a single code element:
    class, function, method, import, variable, etc.
    """
    type: str                  # "class", "function", "method", "import", "variable"
    name: str                  # element name
    start_line: int            # starting line number
    end_line: int              # ending line number
    content: str               # raw source code of the element
    docstring: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    parent_class: Optional[str] = None   # for methods
    parameters: List[str] = field(default_factory=list)   # function/method args
    return_type: Optional[str] = None


@dataclass
class ParsedFile:
    """Represents a fully parsed source file."""
    file_path: str
    language: str
    elements: List[CodeElement] = field(default_factory=list)
    
    # Convenience accessors
    imports: List[CodeElement] = field(default_factory=list)
    classes: List[CodeElement] = field(default_factory=list)
    functions: List[CodeElement] = field(default_factory=list)
    methods: List[CodeElement] = field(default_factory=list)
    
    def categorize(self):
        """Fill the convenience lists after all elements are collected."""
        self.imports = [e for e in self.elements if e.type == "import"]
        self.classes = [e for e in self.elements if e.type == "class"]
        self.functions = [e for e in self.elements if e.type == "function"]
        self.methods = [e for e in self.elements if e.type == "method"]