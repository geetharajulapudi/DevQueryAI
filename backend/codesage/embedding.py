"""
embedding.py
Splits code into chunks, generates embeddings, and builds a FAISS index.
"""

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 60       # lines per chunk
CHUNK_OVERLAP = 10    # overlapping lines between chunks


def chunk_file(file: dict) -> list[dict]:
    """
    Splits a file's content into overlapping line-based chunks.
    Each chunk carries its source file path for traceability.
    """
    lines = file["content"].splitlines()
    chunks = []
    step = CHUNK_SIZE - CHUNK_OVERLAP

    for i in range(0, max(1, len(lines)), step):
        chunk_lines = lines[i: i + CHUNK_SIZE]
        chunk_text = "\n".join(chunk_lines).strip()
        if chunk_text:
            chunks.append({
                "path": file["path"],
                "content": chunk_text,
                "start_line": i + 1,
            })

    return chunks


def build_index(files: list[dict]) -> tuple[faiss.Index, list[dict], SentenceTransformer]:
    """
    Takes a list of file dicts, chunks them, embeds them, and builds a FAISS index.
    Returns (index, chunks_metadata, model).
    """
    print("[+] Loading embedding model ...")
    model = SentenceTransformer(MODEL_NAME)

    # Chunk all files
    all_chunks = []
    for file in files:
        all_chunks.extend(chunk_file(file))

    if not all_chunks:
        raise ValueError("No chunks generated — repository may be empty.")

    print(f"[+] Embedding {len(all_chunks)} chunks ...")
    texts = [c["content"] for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)
    embeddings = np.array(embeddings, dtype="float32")

    # Normalize for cosine similarity via inner product
    faiss.normalize_L2(embeddings)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)  # Inner Product = cosine after normalization
    index.add(embeddings)

    print(f"[+] FAISS index built with {index.ntotal} vectors (dim={dimension}).")
    return index, all_chunks, model
