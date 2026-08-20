from typing import Optional, List
from app.models.code_elements import CodeElement, ParsedFile
from app.services.parsers.base_parser import BaseParser

import tree_sitter_typescript as tsts
from tree_sitter import Language, Parser


class TypeScriptParser(BaseParser):
    """Parses TypeScript (.ts) or TSX (.tsx) source using tree-sitter."""

    def __init__(self, tsx: bool = False):
        lang_fn = tsts.language_tsx if tsx else tsts.language_typescript
        self._language = Language(lang_fn())
        self._parser = Parser(self._language)
        self._lang_name = "tsx" if tsx else "typescript"

    def get_language(self) -> str:
        return self._lang_name

    def parse(self, source_code: str, file_path: str) -> ParsedFile:
        parsed = ParsedFile(file_path=file_path, language=self._lang_name)
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
        elif node.type in ("class_declaration", "abstract_class_declaration"):
            self._extract_class(node, source_bytes, parsed)
        elif node.type == "function_declaration":
            self._extract_function(node, source_bytes, parsed, parent_class)
        elif node.type == "lexical_declaration":
            self._extract_arrow_function_maybe(node, source_bytes, parsed)
        elif node.type == "export_statement":
            # unwrap `export function foo() {}`, `export class Foo {}`, `export default ...`
            for child in node.children:
                self._process_node(child, source_bytes, parsed, parent_class)
        elif node.type == "interface_declaration":
            self._extract_interface(node, source_bytes, parsed)

    def _text(self, node, source_bytes) -> str:
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    def _get_docstring(self, node, source_bytes) -> Optional[str]:
        """Look for a JSDoc block comment, skipping past any leading decorators."""
        prev = node.prev_sibling
        while prev and prev.type == "decorator":
            prev = prev.prev_sibling
        if prev and prev.type == "comment":
            text = self._text(prev, source_bytes)
            if text.startswith("/**"):
                return text
        return None

    def _get_decorators(self, node, source_bytes) -> List[str]:
        """
        Decorator placement differs by node type in this grammar:
        class decorators are leading CHILDREN of class_declaration;
        method decorators are preceding SIBLINGS within class_body.
        """
        child_decorators = [
            self._text(c, source_bytes) for c in node.children if c.type == "decorator"
        ]
        if child_decorators:
            return child_decorators

        decorators = []
        prev = node.prev_sibling
        while prev and prev.type == "decorator":
            decorators.append(self._text(prev, source_bytes))
            prev = prev.prev_sibling
        return list(reversed(decorators))

    def _get_return_type(self, node, source_bytes) -> Optional[str]:
        rt = node.child_by_field_name("return_type")
        if rt is None:
            return None
        text = self._text(rt, source_bytes)
        return text[1:].strip() if text.startswith(":") else text

    def _extract_params(self, params_node, source_bytes) -> List[str]:
        if not params_node:
            return []
        return [self._text(c, source_bytes) for c in params_node.children if c.is_named]

    def _extract_import(self, node, source_bytes, parsed):
        source_node = node.child_by_field_name("source")
        name = self._text(source_node, source_bytes).strip("'\"") if source_node else self._text(node, source_bytes)
        parsed.elements.append(CodeElement(
            type="import", name=name,
            start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
            content=self._text(node, source_bytes),
        ))

    def _extract_interface(self, node, source_bytes, parsed):
        """Interfaces have no runtime body to chunk further, so treat as a single class-like element."""
        name_node = node.child_by_field_name("name")
        name = self._text(name_node, source_bytes) if name_node else "<anonymous>"
        parsed.elements.append(CodeElement(
            type="class", name=name,
            start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
            content=self._text(node, source_bytes),
            docstring=self._get_docstring(node, source_bytes),
        ))

    def _extract_class(self, node, source_bytes, parsed):
        name_node = node.child_by_field_name("name")
        name = self._text(name_node, source_bytes) if name_node else "<anonymous>"
        parsed.elements.append(CodeElement(
            type="class", name=name,
            start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
            content=self._text(node, source_bytes),
            docstring=self._get_docstring(node, source_bytes),
            decorators=self._get_decorators(node, source_bytes),
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
            type=func_type, name=name,
            start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
            content=self._text(node, source_bytes),
            docstring=self._get_docstring(node, source_bytes),
            decorators=self._get_decorators(node, source_bytes),
            parent_class=parent_class, parameters=params,
            return_type=self._get_return_type(node, source_bytes),
        ))

    def _extract_arrow_function_maybe(self, node, source_bytes, parsed):
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
                type="function", name=name,
                start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                content=self._text(node, source_bytes),
                docstring=self._get_docstring(node, source_bytes),
                parameters=params,
                return_type=self._get_return_type(value, source_bytes),
            ))