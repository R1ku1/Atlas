import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.services.pipeline import AtlasPipeline
from app.services.search import SearchService
from app.services.chat_service import ChatService

REPO_PATH = r"C:\Users\aweso\Documents\Rainmeter\Skins\EdgeDock\Icons"# <- point this at a real small-ish repo

def main():
    pipeline = AtlasPipeline()

    print("=== INDEXING ===")
    total = pipeline.index(REPO_PATH)
    print(f"Total chunks in store: {total}\n")

    print("=== SEARCH TEST ===")
    search = SearchService(embedder=pipeline.embedder, vector_store=pipeline.vector_store)
    results = search.search("how are files read from disk", top_k=3)
    for r in results:
        print(f"- {r['metadata']['file_path']} :: {r['metadata']['name']} (dist={r['distance']:.4f})")
        print(r["content"][:200].replace("\n", " "))
        print()

    print("=== CHAT TEST ===")
    chat = ChatService(search_service=search)
    result = chat.ask("What does the file reader do?")
    print("Answer:", result["answer"])
    print("\nSources used:")
    for s in result["sources"]:
        print(f"  - {s['metadata']['file_path']} :: {s['metadata']['name']}")

if __name__ == "__main__":
    main()