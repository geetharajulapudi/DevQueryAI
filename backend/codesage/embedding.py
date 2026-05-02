"""
embedding.py
Splits code into chunks, generates embeddings, and builds a FAISS index.
"""

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 60
CHUNK_OVERLAP = 10


def chunk_file(file: dict) -> list[dict]:
    lines = file["content"].splitlines()
    chunks = []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    for i in range(0, max(1, len(lines)), step):
        chunk_text = "\n".join(lines[i: i + CHUNK_SIZE]).strip()
        if chunk_text:
            chunks.append({"path": file["path"], "content": chunk_text, "start_line": i + 1})
    return chunks


def build_index(files: list[dict]) -> tuple[faiss.Index, list[dict], SentenceTransformer]:
    print("[+] Loading embedding model ...")
    model = SentenceTransformer(MODEL_NAME)

    all_chunks = []
    for file in files:
        all_chunks.extend(chunk_file(file))

    if not all_chunks:
        raise ValueError("No chunks generated — repository may be empty.")

    print(f"[+] Embedding {len(all_chunks)} chunks ...")
    embeddings = model.encode([c["content"] for c in all_chunks], show_progress_bar=True, batch_size=64)
    embeddings = np.array(embeddings, dtype="float32")
    faiss.normalize_L2(embeddings)

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    print(f"[+] FAISS index built with {index.ntotal} vectors.")
    return index, all_chunks, model
