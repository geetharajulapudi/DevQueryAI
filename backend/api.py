"""
api.py
FastAPI backend for CodeSage AI.
Endpoints:
  POST /ingest  — clone repo, build FAISS index
  POST /query   — search + Groq LLM answer
  GET  /status  — check if repo is loaded
  POST /reset   — clear current session
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

from codesage.repo_ingestion import clone_repo, read_files, cleanup_repo
from codesage.embedding import build_index
from codesage.retriever import search, generate_answer

load_dotenv()

# ── Global session state ──────────────────────────────────────────────────────
session = {
    "index": None,
    "chunks": None,
    "model": None,
    "repo_path": None,
    "repo_url": None,
}


def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured in .env")
    return Groq(api_key=api_key)


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="CodeSage AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────
class IngestRequest(BaseModel):
    repo_url: str

class QueryRequest(BaseModel):
    query: str


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/status")
def status():
    return {
        "loaded": session["index"] is not None,
        "repo_url": session["repo_url"],
    }


@app.post("/ingest")
def ingest(req: IngestRequest):
    # Clean up previous session if any
    if session["repo_path"]:
        cleanup_repo(session["repo_path"])
        session.update({"index": None, "chunks": None, "model": None, "repo_path": None})

    try:
        repo_path = clone_repo(req.repo_url)
        files = read_files(repo_path)
        index, chunks, model = build_index(files)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    session.update({
        "index": index,
        "chunks": chunks,
        "model": model,
        "repo_path": repo_path,
        "repo_url": req.repo_url,
    })

    return {"message": f"Ingested {len(chunks)} chunks from {req.repo_url}", "repo_url": session["repo_url"]}


@app.post("/query")
def query(req: QueryRequest):
    if session["index"] is None:
        raise HTTPException(status_code=400, detail="No repository loaded. Call /ingest first.")

    groq_client = get_groq_client()
    results = search(req.query, session["index"], session["chunks"], session["model"])
    answer = generate_answer(req.query, results, groq_client)

    return {
        "answer": answer,
        "sources": [
            {"path": r["path"], "start_line": r["start_line"], "score": round(r["score"], 3)}
            for r in results
        ],
    }


@app.post("/reset")
def reset():
    if session["repo_path"]:
        cleanup_repo(session["repo_path"])
    session.update({"index": None, "chunks": None, "model": None, "repo_path": None, "repo_url": None})
    return {"message": "Session cleared."}
