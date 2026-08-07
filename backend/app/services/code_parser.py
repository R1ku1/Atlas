from typing import List, Optional, Dict
from app.models.code_elements import ParsedFile
from app.services.parsers.base_parser import BaseParser
from app.services.parsers.python_parser import PythonParser

class CodeParser:
    def __init__(self):
        self.parsers: Dict[str, BaseParser] = {
            'python': PythonParser(),
            # future: 'java': JavaParser(), 'cpp': CppParser()
        }
    
    def parse_file(self, source_code: str, file_path: str) -> Optional[ParsedFile]:
        lang = BaseParser.detect_language(file_path)
        if not lang or lang not in self.parsers:
            return None
        return self.parsers[lang].parse(source_code, file_path)
    
    def parse_batch(self, file_dict: Dict[str, str]) -> List[ParsedFile]:
        """file_dict: {file_path: source_code}"""
        results = []
        for path, code in file_dict.items():
            parsed = self.parse_file(code, path)
            if parsed:
                results.append(parsed)
        return results