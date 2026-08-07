from fastapi import APIRouter, HTTPException
from app.services.respository_scanner import RepositoryScanner
from app.services.file_reader import FileReader
from app.services.code_parser import CodeParser

router = APIRouter(prefix="/api/v1")

@router.post("/analyze")
async def analyze_repository(repo_path: str):
    try:
        scanner = RepositoryScanner()
        reader = FileReader()
        parser = CodeParser()

        # Step 1 – Scan
        files_meta = scanner.scan(repo_path)
        # Step 2 – Read
        source_files = reader.read_from_metadata(files_meta, repo_path)
        # Step 3 – Parse
        parsed_files = parser.parse_batch({
            sf.path: sf.content for sf in source_files
        })

        # Return structured data (e.g. list of ParsedFile dicts)
        return {
            "status": "success",
            "files_analyzed": len(parsed_files),
            "results": [pf.to_summary() for pf in parsed_files]  # implement to_summary in ParsedFile
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))