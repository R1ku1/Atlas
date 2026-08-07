from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.app.services.repository_scanner import RepositoryScanner
from app.services.file_reader import FileReader
from app.services.code_parser import CodeParser
from app.services.pipeline import AtlasPipeline
from app.services.search import SearchService
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/v1")

# Services that hold state (Chroma connection, etc.) get instantiated once
# and reused across requests rather than per-request.
pipeline = AtlasPipeline()
search_service = SearchService(embedder=pipeline.embedder, vector_store=pipeline.vector_store)
chat_service = ChatService(search_service=search_service)


class IndexRequest(BaseModel):
    repo_path: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class ChatRequest(BaseModel):
    question: str
    top_k: Optional[int] = None


@router.post("/analyze")
async def analyze_repository(repo_path: str):
    try:
        scanner = RepositoryScanner()
        reader = FileReader()
        parser = CodeParser()

        files_meta = scanner.scan(repo_path)
        source_files = reader.read_from_metadata(files_meta, repo_path)
        parsed_files = parser.parse_batch({
            sf.path: sf.content for sf in source_files
        })

        return {
            "status": "success",
            "files_analyzed": len(parsed_files),
            "results": [pf.to_summary() for pf in parsed_files]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index")
async def index_repository(request: IndexRequest):
    """Run the full pipeline: scan, parse, chunk, enrich, embed, and store."""
    try:
        total_chunks = pipeline.index(request.repo_path)
        return {
            "status": "success",
            "repo_path": request.repo_path,
            "chunks_indexed": total_chunks,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_code(request: SearchRequest):
    """Semantic search over indexed code chunks."""
    try:
        results = search_service.search(request.query, top_k=request.top_k)
        return {
            "status": "success",
            "query": request.query,
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat_with_codebase(request: ChatRequest):
    """Ask a natural-language question, answered using retrieved code context."""
    try:
        if request.top_k:
            chat_service.top_k = request.top_k
        result = chat_service.ask(request.question)
        return {
            "status": "success",
            "question": request.question,
            "answer": result["answer"],
            "sources": result["sources"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))