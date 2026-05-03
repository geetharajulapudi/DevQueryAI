"""
api.py
FastAPI backend for CodeSage AI.
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

from codesage.repo_ingestion import clone_repo, read_files, cleanup_repo
from codesage.embedding import build_index
from codesage.retriever import search, generate_answer

load_dotenv()

session = {
    "index": None, "chunks": None, "model": None,
    "repo_path": None, "repo_url": None,
    "status": "idle", "error": None,
}


def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")
    return Groq(api_key=api_key)


app = FastAPI(title="CodeSage AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngestRequest(BaseModel):
    repo_url: str

class QueryRequest(BaseModel):
    query: str


@app.get("/status")
def status():
    return {
        "loaded": session["index"] is not None,
        "repo_url": session["repo_url"],
        "status": session["status"],
        "error": session["error"],
    }


def run_ingest(repo_url: str):
    if session["repo_path"]:
        cleanup_repo(session["repo_path"])
        session.update({"index": None, "chunks": None, "model": None, "repo_path": None})
    session["status"] = "loading"
    session["error"] = None
    try:
        repo_path = clone_repo(repo_url)
        files = read_files(repo_path)
        index, chunks, model = build_index(files)
        session.update({
            "index": index, "chunks": chunks, "model": model,
            "repo_path": repo_path, "repo_url": repo_url, "status": "ready",
        })
    except Exception as e:
        session["status"] = "error"
        session["error"] = str(e)


@app.post("/ingest")
def ingest(req: IngestRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_ingest, req.repo_url)
    return {"message": "Ingestion started. Poll /status to check progress."}


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
    session.update({"index": None, "chunks": None, "model": None,
                    "repo_path": None, "repo_url": None, "status": "idle", "error": None})
    return {"message": "Session cleared."}
