import hashlib
from typing import List, Optional
from models.chunk import Chunk
from models.code_elements import ParsedFile
from services.code_splitter import CodeSplitter

class CodeChunker:
    """Converts parsed code elements into semantic chunks."""

    def __init__(self, include_class_context: bool = True, splitter: Optional[CodeSplitter] = None):
        self.include_class_context = include_class_context
        self.splitter = splitter  # optional: splits oversized elements before chunking

    def chunk_file(self, parsed_file: ParsedFile) -> List[Chunk]:
        """Create chunks for a single parsed file."""
        chunks = []
        for cls in parsed_file.classes:
            chunks.extend(self._create_chunks(cls, parsed_file, extra_context=None))

            methods = [m for m in parsed_file.methods if m.parent_class == cls.name]
            for method in methods:
                chunks.extend(self._create_chunks(
                    method, parsed_file,
                    extra_context=cls if self.include_class_context else None
                ))

        for func in parsed_file.functions:
            chunks.extend(self._create_chunks(func, parsed_file, extra_context=None))

        return chunks

    def _create_chunks(self, element, parsed_file: ParsedFile, extra_context=None) -> List[Chunk]:
        """Split an element if needed, then build a chunk per resulting piece."""
        elements = self.splitter.split(element) if self.splitter else [element]
        total = len(elements)

        chunks = []
        for i, sub_element in enumerate(elements):
            chunk = self._create_chunk(
                sub_element, parsed_file, extra_context,
                segment_index=i if total > 1 else None,
                total_segments=total if total > 1 else None,
            )
            if chunk:
                chunks.append(chunk)
        return chunks

    def _create_chunk(self, element, parsed_file: ParsedFile, extra_context=None,
                       segment_index: Optional[int] = None,
                       total_segments: Optional[int] = None) -> Chunk:
        """Build a single chunk from a code element (or one segment of a split element)."""
        raw_id = f"{parsed_file.file_path}:{element.name}:{element.type}"
        if segment_index is not None:
            raw_id += f":seg{segment_index}"
        chunk_id = hashlib.md5(raw_id.encode()).hexdigest()[:12]

        content = ""
        if extra_context:
            context_lines = []
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

        name = element.name
        if total_segments is not None:
            name = f"{element.name} (part {segment_index + 1}/{total_segments})"

        return Chunk(
            chunk_id=chunk_id,
            content=content,
            start_line=element.start_line,
            end_line=element.end_line,
            element_type=element.type,
            name=name,
            file_path=parsed_file.file_path,
            language=parsed_file.language,
            metadata={
                "parent_class": element.parent_class,
                "parameters": element.parameters,
                "return_type": element.return_type,
                "decorators": element.decorators,
                "docstring": element.docstring,
                "split_segment": segment_index,
                "split_total": total_segments,
            }
        )