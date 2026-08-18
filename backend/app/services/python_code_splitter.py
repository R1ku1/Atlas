from typing import List, Optional, Tuple
from app.models.code_elements import CodeElement
from app.services.tokenizer_adapter import EmbeddingTokenizer
from app.services.code_splitter import CodeSplitter

class PythonCodeSplitter(CodeSplitter):
    def __init__(self, tokenizer: EmbeddingTokenizer, max_tokens: int = 512, 
                 overlap_lines: int = 0, add_class_context: bool = False):
        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.overlap_lines = overlap_lines
        self.add_class_context = add_class_context
        self.class_context_cache = {}  # we'll set this externally

    def split(self, element: CodeElement) -> List[CodeElement]:
        # Only split functions/methods that exceed the limit
        if element.type not in ("function", "method"):
            return [element]

        full_text = element.content
        if self.tokenizer.count_tokens(full_text) <= self.max_tokens:
            return [element]

        # Extract signature lines (decorators + def line + optional docstring)
        signature_lines, body_lines = self._split_signature_and_body(element)
        signature_text = "\n".join(signature_lines)
        sig_token_count = self.tokenizer.count_tokens(signature_text)

        if sig_token_count >= self.max_tokens:
            # Signature itself is too long – fallback to raw splitting
            return self._fallback_split(element)

        # Build body segments
        segments = self._build_segments(body_lines, sig_token_count)
        
        # Create a new CodeElement for each segment
        new_elements = []
        for start_idx, end_idx in segments:
            seg_body_lines = body_lines[start_idx:end_idx]
            seg_text = signature_text + "\n" + "\n".join(seg_body_lines)
            new_elem = self._create_element_copy(element, seg_text, 
                                                start_line=element.start_line + start_idx,
                                                end_line=element.start_line + end_idx - 1)
            new_elements.append(new_elem)
        
        return new_elements

    def _split_signature_and_body(self, element: CodeElement) -> Tuple[List[str], List[str]]:
        """Heuristically split the element content into signature and body lines."""
        lines = element.content.splitlines()
        # Find the first line that starts with 'def' (should be after decorators)
        def_line_idx = None
        for i, line in enumerate(lines):
            if line.lstrip().startswith('def '):
                def_line_idx = i
                break
        if def_line_idx is None:
            # fallback: treat first line as def
            def_line_idx = 0

        signature_end = def_line_idx + 1
        # Include decorators (lines before the def)
        # Optionally include docstring if it's a single string on the next line
        # For simplicity, we stop at the first line after the def that is not a comment/blank?
        # Actually we'll just take lines up to the colon line – that's the signature.
        # The colon line may span multiple lines if using parentheses – but for simplicity we take until the line containing '):'
        # Better: walk forward until we see a line that ends with ':' (the one that starts the block)
        for i in range(def_line_idx, len(lines)):
            if lines[i].rstrip().endswith(':'):
                signature_end = i + 1
                break
        # Include decorators and maybe a blank line
        signature_lines = lines[:signature_end]
        body_lines = lines[signature_end:]
        return signature_lines, body_lines

    def _build_segments(self, body_lines: List[str], sig_token_count: int):
        """Return list of (start, end) indices for body segments."""
        segments = []
        current_start = 0
        current_tokens = sig_token_count
        for i, line in enumerate(body_lines):
            line_tokens = self.tokenizer.count_tokens(line)
            if current_tokens + line_tokens > self.max_tokens:
                # End current segment
                segments.append((current_start, i))
                # Next segment starts with overlap lines from the end of previous segment
                overlap_start = max(current_start, i - self.overlap_lines)
                current_start = overlap_start
                # Recalculate tokens for the overlap
                current_tokens = sig_token_count + sum(
                    self.tokenizer.count_tokens(body_lines[j]) for j in range(overlap_start, i)
                )
            current_tokens += line_tokens
        # Last segment
        if current_start < len(body_lines):
            segments.append((current_start, len(body_lines)))
        return segments

    def _create_element_copy(self, original: CodeElement, new_content: str,
                            start_line: int, end_line: int) -> CodeElement:
        return CodeElement(
            type=original.type,
            name=original.name,
            start_line=start_line,
            end_line=end_line,
            content=new_content,
            docstring=original.docstring,  # might be incomplete, but okay
            decorators=original.decorators,
            parent_class=original.parent_class,
            parameters=original.parameters,
            return_type=original.return_type
        )

    def _fallback_split(self, element: CodeElement) -> List[CodeElement]:
        """
        Used when even the signature exceeds max_tokens (e.g. huge decorator
        stacks or deeply-typed signatures). Ignores the signature/body split
        entirely and chunks the raw content by line, purely on token budget.
        """
        lines = element.content.splitlines()
        segments = []
        current_start = 0
        current_tokens = 0

        for i, line in enumerate(lines):
            line_tokens = self.tokenizer.count_tokens(line)
            if current_tokens + line_tokens > self.max_tokens and i > current_start:
                segments.append((current_start, i))
                overlap_start = max(current_start, i - self.overlap_lines)
                current_start = overlap_start
                current_tokens = sum(
                    self.tokenizer.count_tokens(lines[j]) for j in range(overlap_start, i)
                )
            current_tokens += line_tokens

        if current_start < len(lines):
            segments.append((current_start, len(lines)))

        if not segments:
            # Single line somehow exceeds max_tokens on its own — nothing more we can do
            return [element]

        new_elements = []
        for start_idx, end_idx in segments:
            seg_text = "\n".join(lines[start_idx:end_idx])
            new_elem = self._create_element_copy(
                element, seg_text,
                start_line=element.start_line + start_idx,
                end_line=element.start_line + end_idx - 1
            )
            new_elements.append(new_elem)

        return new_elements