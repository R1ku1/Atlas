import requests
from typing import List, Dict, Any, Optional
from app.services.search import SearchService


class ChatService:
    """Answers questions about a codebase using retrieved chunks + Ollama."""

    def __init__(
        self,
        search_service: SearchService = None,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
        top_k: int = 5,
    ):
        self.search_service = search_service or SearchService()
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.top_k = top_k

    def ask(self, question: str, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve relevant chunks and generate an answer grounded in them.

        Args:
            repo_path: scopes retrieval to one repository. Without it,
                context is pulled from every repo ever indexed, which is
                how answers end up citing unrelated projects.

        Returns:
            Dict with "answer" and "sources" (the retrieved chunks used).
        """
        results = self.search_service.search(question, top_k=self.top_k, repo_path=repo_path)

        prompt = self._build_prompt(question, results)
        answer = self._generate(prompt)

        return {"answer": answer, "sources": results}

    def _build_prompt(self, question: str, results: List[Dict[str, Any]]) -> str:
        if not results:
            return (
                "You are a helpful assistant answering questions about a codebase. "
                "No relevant code context was found for this question - say so plainly "
                "instead of guessing.\n\n"
                f"Question: {question}\n"
                "Answer:"
            )

        context_blocks = []
        for r in results:
            meta = r["metadata"]
            location = f"{meta['file_path']} ({meta['element_type']} {meta['name']})"
            context_blocks.append(f"# {location}\n{r['content']}")

        context = "\n\n---\n\n".join(context_blocks)

        return (
            "You are a helpful assistant answering questions about a codebase. "
            "Use only the code context below to answer. If the context doesn't "
            "contain the answer, say so instead of guessing.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )

    def _generate(self, prompt: str) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=120,
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except requests.RequestException as e:
            return f"Error generating answer: {e}"