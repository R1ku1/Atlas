import hashlib
from typing import List
from models.chunk import Chunk
from models.code_elements import ParsedFile

class CodeChunker:
    """Converts parsed code elements into semantic chunks."""
    
    def __init__(self, include_class_context: bool = True):
        self.include_class_context = include_class_context

    def chunk_file(self, parsed_file: ParsedFile) -> List[Chunk]:
        """Create chunks for a single parsed file."""
        chunks = []
        # First, handle classes (each class becomes a chunk)
        for cls in parsed_file.classes:
            # Create a chunk for the class itself (signature + docstring)
            class_chunk = self._create_chunk(
                element=cls,
                parsed_file=parsed_file,
                extra_context=None
            )
            if class_chunk:
                chunks.append(class_chunk)
            
            # Now chunk each method inside this class
            methods = [m for m in parsed_file.methods if m.parent_class == cls.name]
            for method in methods:
                method_chunk = self._create_chunk(
                    element=method,
                    parsed_file=parsed_file,
                    extra_context=cls if self.include_class_context else None
                )
                if method_chunk:
                    chunks.append(method_chunk)
        
        # Top-level functions
        for func in parsed_file.functions:
            func_chunk = self._create_chunk(
                element=func,
                parsed_file=parsed_file,
                extra_context=None
            )
            if func_chunk:
                chunks.append(func_chunk)
        
        return chunks

    def _create_chunk(self, element, parsed_file: ParsedFile,
                      extra_context=None) -> Chunk:
        """Build a single chunk from a code element."""
        # Generate unique ID
        raw_id = f"{parsed_file.file_path}:{element.name}:{element.type}"
        chunk_id = hashlib.md5(raw_id.encode()).hexdigest()[:12]
        
        # Build chunk content: optionally prepend class context
        content = ""
        if extra_context:
            # Add class signature and docstring as context
            context_lines = []
            # Add a simplified class signature (name, bases)
            class_sig = f"class {extra_context.name}"
            if extra_context.parameters:
                class_sig += f"({', '.join(extra_context.parameters)})"
            class_sig += ":"
            context_lines.append(class_sig)
            if extra_context.docstring:
                context_lines.append(f'    """{extra_context.docstring}"""')
            context = "\n".join(context_lines)
            content = f"# In class {extra_context.name}\n{context}\n\n{element.content}"
        else:
            content = element.content
        
        return Chunk(
            chunk_id=chunk_id,
            content=content,
            start_line=element.start_line,
            end_line=element.end_line,
            element_type=element.type,
            name=element.name,
            file_path=parsed_file.file_path,
            language=parsed_file.language,
            metadata={
                "parent_class": element.parent_class,
                "parameters": element.parameters,
                "return_type": element.return_type,
                "decorators": element.decorators,
                "docstring": element.docstring,
            }
        )