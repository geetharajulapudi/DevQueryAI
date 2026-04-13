"""
main.py
CodeSage AI – CLI entry point.
Orchestrates: clone → read → embed → index → query loop (powered by Groq LLM).
"""

import os
import sys
from dotenv import load_dotenv
from groq import Groq

from codesage.repo_ingestion import clone_repo, read_files, cleanup_repo
from codesage.embedding import build_index
from codesage.retriever import search, generate_answer


def init_groq() -> Groq:
    """Loads .env and initializes the Groq client. Exits if API key is missing."""
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        print("[Error] GROQ_API_KEY not set. Add it to your .env file.")
        print("Get a free key at: https://console.groq.com")
        sys.exit(1)
    return Groq(api_key=api_key)


def run_pipeline(repo_url: str) -> tuple:
    """Clones repo, reads files, builds FAISS index. Returns (index, chunks, model, repo_path)."""
    repo_path = clone_repo(repo_url)
    try:
        files = read_files(repo_path)
    except ValueError as e:
        cleanup_repo(repo_path)
        raise e

    index, chunks, model = build_index(files)
    return index, chunks, model, repo_path


def query_loop(index, chunks, model, groq_client: Groq) -> None:
    """Interactive query loop powered by Groq LLM."""
    print("\n[CodeSage] Ready! Ask anything about the repository.")
    print("Examples:")
    print("  → Explain this project")
    print("  → How can I add authentication?")
    print("  → Where is error handling implemented?")
    print("  → How do I add a new API endpoint?")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            query = input("Your query: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[CodeSage] Goodbye!")
            break

        if not query:
            continue
        if query.lower() in {"exit", "quit"}:
            print("[CodeSage] Goodbye!")
            break

        print("\n[CodeSage] Searching codebase and generating answer...\n")
        results = search(query, index, chunks, model)
        answer = generate_answer(query, results, groq_client)
        print(answer + "\n")
        print("-" * 60 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <github_repo_url>")
        print("Example: python main.py https://github.com/pallets/flask")
        sys.exit(1)

    repo_url = sys.argv[1]
    groq_client = init_groq()

    try:
        index, chunks, model, repo_path = run_pipeline(repo_url)
    except ValueError as e:
        print(f"[Error] {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"[Error] {e}")
        sys.exit(1)

    try:
        query_loop(index, chunks, model, groq_client)
    finally:
        cleanup_repo(repo_path)


if __name__ == "__main__":
    main()
