from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.pipeline import AtlasPipeline
from app.services.search import SearchService
from app.services.chat_service import ChatService
from app.services.folder_dialog import open_folder_dialog

router = APIRouter(prefix="/api/v1")

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


@router.get("/browse-folder")
def browse_folder():
    """
    Opens a native folder-browser dialog on the machine running the
    backend and returns the selected path. Only makes sense for a
    local, single-user setup (this dialog pops up on the server's
    desktop, not the browser's) - which matches how Atlas runs.
    """
    try:
        path = open_folder_dialog()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not open folder dialog: {e}")

    if not path:
        # user closed the dialog without picking anything - not a real error
        raise HTTPException(status_code=400, detail="No folder selected")

    return {"status": "success", "path": path}


@router.post("/index")
async def index_repository(payload: IndexRequest):
    """Scan, parse, chunk, embed, and store a repository."""
    try:
        total = pipeline.index(payload.repo_path)
        return {"status": "success", "total_chunks": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_repository(payload: SearchRequest):
    """Semantic search over indexed chunks."""
    try:
        results = search_service.search(payload.query, top_k=payload.top_k)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat_with_repository(payload: ChatRequest):
    """Ask a question about the indexed codebase."""
    try:
        result = chat_service.ask(payload.question)
        return {"status": "success", "answer": result["answer"], "sources": result["sources"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))