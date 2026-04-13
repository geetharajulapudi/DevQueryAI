"""
retriever.py
Searches the FAISS index for relevant code chunks and generates answers via Groq LLM.
"""

import numpy as np
import faiss
from groq import Groq
from sentence_transformers import SentenceTransformer

# Groq model to use — fast and free tier available
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are CodeSage AI, an expert developer assistant.

You are given relevant code snippets retrieved from a GitHub repository.
Your job is to answer the user's question clearly and helpfully based on that code.

When answering:
- If the user asks to explain something, give a clear, structured explanation of how it works in THIS repo.
- If the user asks how to implement a feature, give step-by-step instructions with exact file paths and code examples tailored to this repo's structure.
- If the user asks where something is, point to the exact file and describe what's happening there.
- Always reference the actual file paths from the context (e.g. "In `auth/login.py` line ~45, ...").
- If the context doesn't have enough info, say so honestly and suggest what to look for.
- Keep answers concise but complete. Use markdown formatting (headers, code blocks).
"""


def search(
    query: str,
    index: faiss.Index,
    chunks: list[dict],
    model: SentenceTransformer,
    top_k: int = 6,
) -> list[dict]:
    """
    Embeds the query and retrieves the top_k most relevant code chunks from FAISS.
    """
    query_vec = model.encode([query], convert_to_numpy=True).astype("float32")
    faiss.normalize_L2(query_vec)

    scores, indices = index.search(query_vec, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        chunk = dict(chunks[idx])
        chunk["score"] = float(score)
        results.append(chunk)

    return results


def build_context(results: list[dict]) -> str:
    """Formats retrieved chunks into a readable context block for the LLM prompt."""
    parts = []
    for i, chunk in enumerate(results, 1):
        parts.append(
            f"### Snippet {i} — File: `{chunk['path']}` | Line ~{chunk['start_line']}\n"
            f"```\n{chunk['content']}\n```"
        )
    return "\n\n".join(parts)


def generate_answer(query: str, results: list[dict], groq_client: Groq) -> str:
    """
    Sends the query + retrieved code context to Groq LLM and returns the answer.
    Falls back to a plain snippet dump if Groq call fails.
    """
    if not results:
        return "No relevant code found for your query."

    context = build_context(results)

    user_message = f"""Here are the most relevant code snippets from the repository:

{context}

---

User question: {query}

Please answer based on the code above."""

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,      # low temp = focused, factual answers
            max_tokens=1024,
        )
        return response.choices[0].message.content

    except Exception as e:
        # Graceful fallback — show raw snippets if LLM call fails
        fallback = [f"[!] Groq LLM error: {e}\n", "Falling back to raw snippets:\n"]
        for chunk in results:
            fallback.append(f"File: {chunk['path']} | Line ~{chunk['start_line']}\n{chunk['content']}\n")
        return "\n".join(fallback)
