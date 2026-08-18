from typing import Optional, List
from app.models.code_elements import CodeElement, ParsedFile
from app.services.parsers.base_parser import BaseParser

import tree_sitter_javascript as tsjs
from tree_sitter import Language, Parser


class JavaScriptParser(BaseParser):
    """Parses JavaScript source files using tree-sitter."""

    def __init__(self):
        self._language = Language(tsjs.language())
        self._parser = Parser(self._language)

    def get_language(self) -> str:
        return "javascript"

    def parse(self, source_code: str, file_path: str) -> ParsedFile:
        parsed = ParsedFile(file_path=file_path, language="javascript")
        source_bytes = source_code.encode("utf-8")
        tree = self._parser.parse(source_bytes)
        root = tree.root_node

        for node in root.children:
            self._process_node(node, source_bytes, parsed, parent_class=None)

        parsed.categorize()
        return parsed

    def _process_node(self, node, source_bytes, parsed, parent_class):
        if node.type == "import_statement":
            self._extract_import(node, source_bytes, parsed)
        elif node.type == "class_declaration":
            self._extract_class(node, source_bytes, parsed)
        elif node.type == "function_declaration":
            self._extract_function(node, source_bytes, parsed, parent_class)
        elif node.type == "lexical_declaration":
            self._extract_arrow_function_maybe(node, source_bytes, parsed)
        elif node.type == "export_statement":
            # unwrap `export function foo() {}`, `export class Foo {}`, etc.
            for child in node.children:
                self._process_node(child, source_bytes, parsed, parent_class)

    def _text(self, node, source_bytes) -> str:
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    def _get_docstring(self, node, source_bytes) -> Optional[str]:
        """Look for a JSDoc block comment (/** ... */) immediately preceding this node."""
        prev = node.prev_sibling
        if prev and prev.type == "comment":
            text = self._text(prev, source_bytes)
            if text.startswith("/**"):
                return text
        return None

    def _extract_params(self, params_node, source_bytes) -> List[str]:
        if not params_node:
            return []
        return [self._text(c, source_bytes) for c in params_node.children if c.is_named]

    def _extract_import(self, node, source_bytes, parsed):
        source_node = node.child_by_field_name("source")
        name = self._text(source_node, source_bytes).strip("'\"") if source_node else self._text(node, source_bytes)
        parsed.elements.append(CodeElement(
            type="import",
            name=name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            content=self._text(node, source_bytes),
        ))

    def _extract_class(self, node, source_bytes, parsed):
        name_node = node.child_by_field_name("name")
        name = self._text(name_node, source_bytes) if name_node else "<anonymous>"
        parsed.elements.append(CodeElement(
            type="class",
            name=name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            content=self._text(node, source_bytes),
            docstring=self._get_docstring(node, source_bytes),
        ))

        body = node.child_by_field_name("body")
        if body:
            for child in body.children:
                if child.type == "method_definition":
                    self._extract_function(child, source_bytes, parsed, parent_class=name)

    def _extract_function(self, node, source_bytes, parsed, parent_class=None):
        name_node = node.child_by_field_name("name")
        name = self._text(name_node, source_bytes) if name_node else "<anonymous>"
        params = self._extract_params(node.child_by_field_name("parameters"), source_bytes)
        func_type = "method" if parent_class else "function"

        parsed.elements.append(CodeElement(
            type=func_type,
            name=name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            content=self._text(node, source_bytes),
            docstring=self._get_docstring(node, source_bytes),
            parent_class=parent_class,
            parameters=params,
        ))

    def _extract_arrow_function_maybe(self, node, source_bytes, parsed):
        """Handle `const foo = () => {...}` / `const foo = function() {...}` at module scope."""
        for declarator in node.children:
            if declarator.type != "variable_declarator":
                continue
            value = declarator.child_by_field_name("value")
            if value is None or value.type not in ("arrow_function", "function"):
                continue
            name_node = declarator.child_by_field_name("name")
            name = self._text(name_node, source_bytes) if name_node else "<anonymous>"
            params = self._extract_params(value.child_by_field_name("parameters"), source_bytes)

            parsed.elements.append(CodeElement(
                type="function",
                name=name,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                content=self._text(node, source_bytes),
                docstring=self._get_docstring(node, source_bytes),
                parameters=params,
            ))