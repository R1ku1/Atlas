import ast
from typing import List, Optional
from models.code_elements import CodeElement, ParsedFile
from parsers.base_parser import BaseParser

class PythonParser(BaseParser):
    
    def get_language(self) -> str:
        return "python"
    
    def parse(self, source_code: str, file_path: str) -> ParsedFile:
        parsed = ParsedFile(file_path=file_path, language="python")
        try:
            tree = ast.parse(source_code)
            for node in ast.iter_child_nodes(tree):
                self._process_node(node, source_code, parsed, parent_class=None)
            parsed.categorize()
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
        return parsed
    
    def _process_node(self, node, source_code, parsed, parent_class):
        if isinstance(node, ast.Import):
            self._extract_import(node, source_code, parsed)
        elif isinstance(node, ast.ImportFrom):
            self._extract_import_from(node, source_code, parsed)
        elif isinstance(node, ast.ClassDef):
            self._extract_class(node, source_code, parsed)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._extract_function(node, source_code, parsed, parent_class)
        # variables can be added similarly
    
    # --- Imports ---
    def _extract_import(self, node: ast.Import, source_code, parsed):
        for alias in node.names:
            element = CodeElement(
                type="import",
                name=alias.name,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                content=ast.get_source_segment(source_code, node) or ""
            )
            parsed.elements.append(element)
    
    def _extract_import_from(self, node: ast.ImportFrom, source_code, parsed):
        module = node.module or ""
        for alias in node.names:
            full_name = f"{module}.{alias.name}" if module else alias.name
            element = CodeElement(
                type="import",
                name=full_name,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                content=ast.get_source_segment(source_code, node) or ""
            )
            parsed.elements.append(element)
    
    # --- Classes ---
    def _extract_class(self, node: ast.ClassDef, source_code, parsed):
        doc = ast.get_docstring(node)
        decorators = [ast.unparse(d) for d in node.decorator_list]
        bases = [ast.unparse(b) for b in node.bases]
        
        element = CodeElement(
            type="class",
            name=node.name,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            content=ast.get_source_segment(source_code, node) or "",
            docstring=doc,
            decorators=decorators,
            parameters=bases   # we reuse parameters to store base class names
        )
        parsed.elements.append(element)
        
        # Process methods inside the class
        for body_node in node.body:
            if isinstance(body_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._extract_function(body_node, source_code, parsed, parent_class=node.name)
    
    # --- Functions / Methods ---
    def _extract_function(self, node, source_code, parsed, parent_class=None):
        doc = ast.get_docstring(node)
        decorators = [ast.unparse(d) for d in node.decorator_list]
        params = [arg.arg for arg in node.args.args]
        ret = ast.unparse(node.returns) if node.returns else None
        
        func_type = "method" if parent_class else "function"
        
        element = CodeElement(
            type=func_type,
            name=node.name,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            content=ast.get_source_segment(source_code, node) or "",
            docstring=doc,
            decorators=decorators,
            parent_class=parent_class,
            parameters=params,
            return_type=ret
        )
        parsed.elements.append(element)