from typing import List
from app.models.chunk import Chunk
from app.models.code_elements import ParsedFile


class ChunkEnricher:
    """Adds contextual information to chunks before embedding."""

    def enrich(self, chunk: Chunk, parsed_file: ParsedFile) -> Chunk:
        """Return a new chunk with enriched content."""
        context_parts = []

        # 1. File-level imports (compact)
        if parsed_file.imports:
            imports_summary = self._format_imports(parsed_file.imports)
            context_parts.append(f"# File imports: {imports_summary}")

        # 2. Class context for methods (chunker already prepends class signature
        #    + docstring when include_class_context=True, so only add it here
        #    if it's missing — e.g. class docstring wasn't captured, or the
        #    chunker was configured without class context).
        if chunk.element_type == "method" and chunk.metadata.get("parent_class"):
            parent_class = chunk.metadata["parent_class"]
            cls_element = next(
                (c for c in parsed_file.classes if c.name == parent_class), None
            )
            if (
                cls_element
                and cls_element.docstring
                and cls_element.docstring not in chunk.content
            ):
                context_parts.append(
                    f"# Class {parent_class} docstring: {cls_element.docstring}"
                )

        enriched_content = (
            "\n".join(context_parts + [chunk.content]) if context_parts else chunk.content
        )

        return Chunk(
            chunk_id=chunk.chunk_id,
            content=enriched_content,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            element_type=chunk.element_type,
            name=chunk.name,
            file_path=chunk.file_path,
            language=chunk.language,
            metadata=chunk.metadata,
        )

    def _format_imports(self, imports: List) -> str:
        """Compact list of imports into a single string."""
        names = [imp.name for imp in imports[:5]]
        result = ", ".join(names)
        if len(imports) > 5:
            result += f", ... ({len(imports) - 5} more)"
        return result